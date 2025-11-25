from __future__ import annotations

from datetime import datetime
from typing import List
from sqlalchemy.orm import Session

from app import models
from app.adapters import echidna, manticore, mythril, slither, state_fuzzer
from app.normalization.findings import NormalizedFinding
from app.config import get_settings

settings = get_settings()

TOOL_MAP = {
    "slither": slither.run_slither,
    "mythril": mythril.run_mythril,
    "echidna": echidna.run_echidna,
    "manticore": manticore.run_manticore,
    "state-fuzzer": state_fuzzer.run_state_fuzzer,
}


def execute_scan(db: Session, scan: models.Scan) -> None:
    scan.status = models.ScanStatus.RUNNING
    scan.started_at = datetime.utcnow()
    db.commit()
    db.refresh(scan)

    logs: list[str] = []
    all_findings: List[NormalizedFinding] = []

    for tool_name in scan.tools:
        tool = TOOL_MAP.get(tool_name)
        if not tool:
            logs.append(f"Tool {tool_name} not recognized")
            continue
        result, findings = tool(scan.target)
        logs.append(f"[{tool_name}] success={result.success}\n{result.output}\n{result.error or ''}")
        all_findings.extend(findings)

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
    scan.status = models.ScanStatus.SUCCESS
    scan.logs = "\n".join(logs)
    db.commit()
    db.refresh(scan)