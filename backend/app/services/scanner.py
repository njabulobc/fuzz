from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import List
from sqlalchemy.orm import Session

from app import models
from app.adapters import slither, mythril, echidna, manticore
from app.normalization.findings import NormalizedFinding
from app.config import get_settings

settings = get_settings()

TOOL_MAP = {
    "slither": slither.run_slither,
    "mythril": mythril.run_mythril,
    "echidna": echidna.run_echidna,
    "manticore": manticore.run_manticore,
}


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

    def as_dict(self) -> dict:
        return {
            **asdict(self),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
        }


def execute_scan(db: Session, scan: models.Scan) -> None:
    if scan.status in {models.ScanStatus.SUCCESS, models.ScanStatus.RUNNING}:
        return

    scan.status = models.ScanStatus.RUNNING
    scan.started_at = datetime.utcnow()
    db.commit()
    db.refresh(scan)


    logs: list[ToolExecutionLog] = []
    all_findings: List[NormalizedFinding] = []
    successful_tools = 0

    for tool_name in scan.tools:
        log = ToolExecutionLog(tool=tool_name, status="pending", started_at=datetime.utcnow())
        tool = TOOL_MAP.get(tool_name)

        if not tool:
            log.status = "unknown-tool"
            log.finished_at = datetime.utcnow()
            log.errors.append(f"Tool {tool_name} not recognized")
            logs.append(log)
            continue

        for attempt in range(settings.tool_attempts):
            log.attempts += 1
            try:
                result, findings = tool(scan.target, timeout=settings.default_timeout_seconds)
                log.last_output = (result.output or "")[:5000]
                if result.error:
                    log.errors.append(result.error)

                if result.success:
                    log.status = "completed"
                    log.success = True
                    log.findings_count = len(findings)
                    all_findings.extend(findings)
                    successful_tools += 1
                    break
                else:
                    log.status = "retrying" if attempt < settings.tool_attempts - 1 else "failed"
            except Exception as exc:  # pragma: no cover - defensive
                log.errors.append(str(exc))
                log.status = "retrying" if attempt < settings.tool_attempts - 1 else "failed"

        log.finished_at = datetime.utcnow()
        logs.append(log)

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
    scan.status = (
        models.ScanStatus.SUCCESS if successful_tools > 0 else models.ScanStatus.FAILED
    )
    scan.logs = json.dumps([log.as_dict() for log in logs])
    db.commit()
    db.refresh(scan)