from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, List, Dict, Any

from sqlalchemy.orm import Session

from app import models
from app.adapters import slither, mythril, echidna, manticore
from app.adapters.base import ToolResult
from app.normalization.findings import NormalizedFinding
from app.config import get_settings
from app.services.webhooks import dispatch_scan_webhook
from app.services.reporting import build_scan_report

settings = get_settings()

TOOL_MAP: dict[str, Callable[[str, int | None], tuple[ToolResult, List[NormalizedFinding]]]] = {
    "slither": slither.run_slither,
    "mythril": mythril.run_mythril,
    "echidna": echidna.run_echidna,
    "manticore": manticore.run_manticore,
}


@dataclass
class ToolExecutionOutcome:
    tool: str
    result: ToolResult
    findings: List[NormalizedFinding]
    attempts: int
    artifacts: list[dict] = field(default_factory=list)
    telemetry: Dict[str, Any] = field(default_factory=dict)
    status: models.ToolRunStatus = models.ToolRunStatus.PENDING


class SandboxedToolRunner:
    """Runs tools in an isolated worker context with retries and telemetry."""

    def __init__(
        self,
        timeout_seconds: int = settings.default_timeout_seconds,
        max_retries: int = 1,
        memory_limit_mb: int | None = None,
    ) -> None:
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.memory_limit_mb = memory_limit_mb

    def run(self, tool_name: str, tool_func: Callable[[str, int | None], tuple[ToolResult, List[NormalizedFinding]]], target: str) -> ToolExecutionOutcome:
        attempts = 0
        artifacts: list[dict] = []
        findings: List[NormalizedFinding] = []
        latest_result: ToolResult | None = None
        status = models.ToolRunStatus.PENDING

        while attempts <= self.max_retries:
            attempts += 1
            status = models.ToolRunStatus.RUNNING
            result, findings = tool_func(target, timeout=self.timeout_seconds)
            latest_result = result
            artifacts.append(
                {
                    "attempt": attempts,
                    "stdout": result.output,
                    "stderr": result.error,
                    "exit_code": result.exit_code,
                }
            )
            if result.success:
                status = models.ToolRunStatus.SUCCESS
                break
            status = models.ToolRunStatus.RETRIED if attempts <= self.max_retries else models.ToolRunStatus.FAILED

        telemetry = {
            "attempts": attempts,
            "timeout_seconds": self.timeout_seconds,
            "memory_limit_mb": self.memory_limit_mb,
            "runtime_seconds": latest_result.runtime_seconds if latest_result else None,
        }

        return ToolExecutionOutcome(
            tool=tool_name,
            result=latest_result or ToolResult(success=False, output="", error="no result"),
            findings=findings,
            attempts=attempts,
            artifacts=artifacts,
            telemetry=telemetry,
            status=status,
        )


def execute_scan(db: Session, scan: models.Scan) -> None:
    scan.status = models.ScanStatus.RUNNING
    scan.started_at = datetime.utcnow()
    scan.logs = None
    scan.telemetry = {"tools": []}
    scan.artifacts = []
    db.commit()
    db.refresh(scan)

    logs: list[str] = []
    all_findings: List[NormalizedFinding] = []
    sandbox = SandboxedToolRunner()
    overall_success = True

    for tool_name in scan.tools:
        tool = TOOL_MAP.get(tool_name)
        tool_run = models.ToolRun(
            scan_id=scan.id,
            tool=tool_name,
            status=models.ToolRunStatus.PENDING,
            started_at=datetime.utcnow(),
        )
        db.add(tool_run)
        db.commit()
        db.refresh(tool_run)

        if not tool:
            tool_run.status = models.ToolRunStatus.FAILED
            tool_run.error = f"Tool {tool_name} not recognized"
            db.commit()
            overall_success = False
            logs.append(tool_run.error)
            continue

        outcome = sandbox.run(tool_name, tool, scan.target)
        tool_run.status = outcome.status
        tool_run.attempts = outcome.attempts
        tool_run.exit_code = outcome.result.exit_code
        tool_run.output = outcome.result.output
        tool_run.error = outcome.result.error
        tool_run.artifacts = outcome.artifacts
        tool_run.metrics = outcome.telemetry
        tool_run.finished_at = datetime.utcnow()
        db.commit()
        db.refresh(tool_run)

        all_findings.extend(outcome.findings)
        logs.append(
            f"[{tool_name}] status={outcome.status} attempts={outcome.attempts} success={outcome.result.success}\n{outcome.result.output}\n{outcome.result.error or ''}"
        )
        scan.telemetry.setdefault("tools", []).append({
            "tool": tool_name,
            "status": outcome.status,
            "metrics": outcome.telemetry,
        })
        scan.artifacts.extend(outcome.artifacts)
        if not outcome.result.success:
            overall_success = False

    for f in all_findings:
        db_finding = models.Finding(
            scan_id=scan.id,
            tool=f.tool,
            title=f.title,
            description=f.description,
            severity=f.severity,
            category=f.category,
            file_path=f.file_path,
            line_number=f.line_number,
            function=f.function,
            raw=f.raw,
        )
        db.add(db_finding)

    scan.finished_at = datetime.utcnow()
    scan.status = models.ScanStatus.SUCCESS if overall_success else models.ScanStatus.FAILED
    scan.logs = "\n".join(logs)
    db.flush()
    scan.telemetry["summary"] = build_scan_report(scan, include_findings=False)
    db.commit()
    db.refresh(scan)

    if scan.webhook_url:
        dispatch_scan_webhook(scan)
