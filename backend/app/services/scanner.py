from __future__ import annotations

import asyncio
import json
import os
import shutil
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List

from sqlalchemy.orm import Session

from app import models
from app.adapters import echidna, foundry, manticore, mythril, slither
from app.config import ToolSettings, get_settings
from app.db.session import SessionLocal
from app.normalization.findings import NormalizedFinding

settings = get_settings()

TOOL_MAP = {
    "slither": slither.run_slither,
    "mythril": mythril.run_mythril,
    "echidna": echidna.run_echidna,
    "manticore": manticore.run_manticore,
    "foundry": foundry.run_foundry,
}

DEFAULT_FAKE_FINDINGS = [
    {
        "title": "Simulated critical vulnerability",
        "description": "This is a simulated positive finding to demonstrate reporting.",
        "severity": "HIGH",
        "category": "demo",
        "raw": {"simulated": True, "type": "positive"},
    },
    {
        "title": "Simulated clean analysis",
        "description": "This is a simulated negative finding showing no critical issues.",
        "severity": "INFO",
        "category": "demo",
        "raw": {"simulated": True, "type": "negative"},
    },
]


def _iso(dt: datetime | None) -> str | None:
    return dt.isoformat() if dt else None


@dataclass
class ToolExecutionLog:
    tool: str
    status: str
    attempts: int = 0
    success: bool = False
    started_at: datetime | None = None
    finished_at: datetime | None = None
    errors: list[str] = field(default_factory=list)
    findings_count: int = 0
    last_output: str | None = None
    stdout_path: str | None = None
    stderr_path: str | None = None

    def as_dict(self) -> dict:
        return {
            **asdict(self),
            "started_at": _iso(self.started_at),
            "finished_at": _iso(self.finished_at),
        }


def _prepare_workspace(scan: models.Scan) -> tuple[Path, Path]:
    base_dir = Path(settings.storage_path) / "scans" / scan.id
    base_dir.mkdir(parents=True, exist_ok=True)

    target_path = Path(scan.target)
    if not target_path.is_absolute() and scan.project:
        target_path = Path(scan.project.path) / scan.target

    if not target_path.exists():
        raise FileNotFoundError(f"Target {target_path} not found")

    isolated_target = base_dir / target_path.name
    if target_path.is_dir():
        shutil.copytree(target_path, isolated_target, dirs_exist_ok=True)
    else:
        isolated_target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(target_path, isolated_target)

    return base_dir, isolated_target


def _create_tool_records(db: Session, scan: models.Scan, workspace: Path) -> None:
    for tool in scan.tools:
        existing = (
            db.query(models.ToolExecution)
            .filter(models.ToolExecution.scan_id == scan.id, models.ToolExecution.tool == tool)
            .first()
        )
        if existing:
            continue
        db.add(
            models.ToolExecution(
                scan_id=scan.id,
                tool=tool,
                status=models.ToolExecutionStatus.PENDING,
                artifacts_path=str(workspace / tool),
            )
        )
    db.commit()


def _store_findings(db: Session, scan_id: str, findings: List[NormalizedFinding]) -> None:
    for f in findings:
        db.add(
            models.Finding(
                scan_id=scan_id,
                tool=f.tool,
                title=f.title,
                description=f.description,
                severity=f.severity,
                category=f.category,
                file_path=f.file_path,
                line_number=f.line_number,
                function=f.function,
                raw=f.raw,
                tool_version=f.tool_version,
                input_seed=f.input_seed,
                coverage=f.coverage,
                assertions=f.assertions,
            )
        )
    db.commit()


def _update_tool_record(
    tool_exec: models.ToolExecution, result, findings: List[NormalizedFinding], status
) -> None:
    tool_exec.status = status
    tool_exec.finished_at = result.finished_at or datetime.utcnow()
    tool_exec.duration_seconds = result.duration_seconds
    tool_exec.command = result.command
    tool_exec.exit_code = result.return_code
    tool_exec.stdout_path = result.stdout_path
    tool_exec.stderr_path = result.stderr_path
    tool_exec.environment = result.environment
    tool_exec.artifacts_path = result.artifacts_path or tool_exec.artifacts_path
    tool_exec.error = result.error
    tool_exec.parsing_error = result.parsing_error
    tool_exec.failure_reason = result.failure_reason
    tool_exec.findings_count = len(findings)
    tool_exec.tool_version = result.tool_version
    if findings:
        tool_exec.tool_version = tool_exec.tool_version or findings[0].tool_version
        tool_exec.input_seed = findings[0].input_seed
        tool_exec.coverage = findings[0].coverage
        tool_exec.assertions = findings[0].assertions


def _build_env(config: ToolSettings) -> dict[str, str]:
    env = {"PATH": os.environ.get("PATH", "")}
    env.update(config.env)
    return env


def _execute_tool(scan_id: str, tool_name: str, target_path: Path, workspace: Path) -> None:
    db: Session = SessionLocal()
    try:
        tool_fn = TOOL_MAP.get(tool_name)
        tool_exec = (
            db.query(models.ToolExecution)
            .filter(models.ToolExecution.scan_id == scan_id, models.ToolExecution.tool == tool_name)
            .first()
        )
        if not tool_fn:
            if tool_exec:
                tool_exec.status = models.ToolExecutionStatus.FAILED
                tool_exec.error = f"Tool {tool_name} not recognized"
                tool_exec.finished_at = datetime.utcnow()
                db.commit()
            return

        config = settings.get_tool_config(tool_name)
        attempts = max(1, config.retries + 1)
        all_findings: List[NormalizedFinding] = []
        for attempt in range(attempts):
            tool_exec.attempt += 1
            tool_exec.status = models.ToolExecutionStatus.RUNNING
            tool_exec.started_at = datetime.utcnow()
            db.commit()

            attempt_dir = Path(tool_exec.artifacts_path or workspace / tool_name)
            attempt_dir.mkdir(parents=True, exist_ok=True)
            env = _build_env(config)

            result, findings = tool_fn(
                str(target_path),
                config=config,
                workdir=attempt_dir,
                log_dir=attempt_dir,
                env=env,
            )
            all_findings.extend(findings)

            status = (
                models.ToolExecutionStatus.SUCCEEDED
                if result.success
                else (
                    models.ToolExecutionStatus.RETRYING
                    if attempt < attempts - 1
                    else models.ToolExecutionStatus.FAILED
                )
            )
            is_final_attempt = status != models.ToolExecutionStatus.RETRYING
            if is_final_attempt:
                _store_findings(db, scan_id, all_findings)

            attempt_findings = all_findings if is_final_attempt else findings
            _update_tool_record(tool_exec, result, attempt_findings, status)
            db.commit()

            if result.success:
                break
            time.sleep(config.backoff_seconds)
    finally:
        db.close()


async def _execute_tool_async(scan_id: str, tool: str, target_path: Path, workspace: Path) -> None:
    await asyncio.to_thread(_execute_tool, scan_id, tool, target_path, workspace)


def _build_fake_findings(scan: models.Scan) -> list[dict]:
    if scan.fake_findings:
        return scan.fake_findings

    tool_name = scan.tools[0] if scan.tools else "simulator"
    default_findings: list[dict] = []
    for finding in DEFAULT_FAKE_FINDINGS:
        default_findings.append({"tool": tool_name, **finding})
    return default_findings


def _apply_fake_findings(db: Session, scan: models.Scan) -> None:
    fake_findings = _build_fake_findings(scan)
    default_tool = scan.tools[0] if scan.tools else "simulator"

    db.query(models.Finding).filter(models.Finding.scan_id == scan.id).delete()
    db.commit()

    tool_counts: dict[str, int] = {}
    for finding in fake_findings:
        tool_name = finding.get("tool") or default_tool
        tool_counts[tool_name] = tool_counts.get(tool_name, 0) + 1
        db.add(
            models.Finding(
                scan_id=scan.id,
                tool=tool_name,
                title=finding.get("title", "Simulated finding"),
                description=finding.get(
                    "description", "This finding was generated in fake-results mode."
                ),
                severity=finding.get("severity", "INFO"),
                category=finding.get("category"),
                file_path=finding.get("file_path"),
                line_number=finding.get("line_number"),
                function=finding.get("function"),
                raw=finding.get("raw")
                or {"simulated": True, "note": "fake_results enabled"},
                tool_version=finding.get("tool_version"),
                input_seed=finding.get("input_seed"),
                coverage=finding.get("coverage"),
                assertions=finding.get("assertions"),
            )
        )

    db.commit()

    tool_executions = (
        db.query(models.ToolExecution)
        .filter(models.ToolExecution.scan_id == scan.id)
        .all()
    )
    for exec_record in tool_executions:
        exec_record.findings_count = tool_counts.get(exec_record.tool, exec_record.findings_count)
    db.commit()


def _build_logs_snapshot(db: Session, scan_id: str) -> str:
    entries = (
        db.query(models.ToolExecution)
        .filter(models.ToolExecution.scan_id == scan_id)
        .order_by(models.ToolExecution.tool)
        .all()
    )
    logs = []
    for entry in entries:
        logs.append(
            {
                "tool": entry.tool,
                "status": entry.status.value if entry.status else None,
                "attempts": entry.attempt,
                "success": entry.status == models.ToolExecutionStatus.SUCCEEDED,
                "started_at": _iso(entry.started_at),
                "finished_at": _iso(entry.finished_at),
                "duration_seconds": entry.duration_seconds,
                "errors": [entry.error] if entry.error else [],
                "parsing_error": entry.parsing_error,
                "stdout_path": entry.stdout_path,
                "stderr_path": entry.stderr_path,
                "findings_count": entry.findings_count,
                "command": entry.command,
                "exit_code": entry.exit_code,
                "environment": entry.environment,
            }
        )
    return json.dumps(logs)


def execute_scan(db: Session, scan: models.Scan) -> None:
    if scan.status in {models.ScanStatus.SUCCESS, models.ScanStatus.RUNNING}:
        return

    scan.status = models.ScanStatus.RUNNING
    scan.started_at = datetime.utcnow()
    db.commit()
    db.refresh(scan)

    workspace, isolated_target = _prepare_workspace(scan)
    _create_tool_records(db, scan, workspace)

    async def runner() -> None:
        await asyncio.gather(
            *[
                _execute_tool_async(scan.id, tool, isolated_target, workspace)
                for tool in scan.tools
            ]
        )

    asyncio.run(runner())

    db.refresh(scan)
    if scan.fake_results:
        _apply_fake_findings(db, scan)

    success_count = (
        db.query(models.ToolExecution)
        .filter(
            models.ToolExecution.scan_id == scan.id,
            models.ToolExecution.status == models.ToolExecutionStatus.SUCCEEDED,
        )
        .count()
    )
    scan.finished_at = datetime.utcnow()
    scan.status = models.ScanStatus.SUCCESS if success_count > 0 else models.ScanStatus.FAILED
    scan.logs = _build_logs_snapshot(db, scan.id)
    db.commit()
    db.refresh(scan)
