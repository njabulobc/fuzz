from __future__ import annotations

from datetime import datetime
from typing import Dict, List
from sqlalchemy.orm import Session

from app import models
from app.adapters import slither, mythril, echidna, manticore
from app.normalization.findings import NormalizedFinding
from app.config import get_settings
from app.services.orchestrator import FuzzOrchestrator

settings = get_settings()

TOOL_MAP = {
    "slither": slither.run_slither,
    "mythril": mythril.run_mythril,
    "echidna": echidna.run_echidna,
    "manticore": manticore.run_manticore,
}


def _capture_tool_outcome(tool_name: str, result, findings: List[NormalizedFinding]) -> dict:
    return {
        "tool": tool_name,
        "success": result.success,
        "attempts": result.attempts,
        "duration_seconds": result.duration_seconds,
        "artifacts": result.artifacts,
        "output": result.output,
        "error": result.error,
        "telemetry": result.telemetry.__dict__ if result.telemetry else {},
        "findings": len(findings),
    }


def execute_scan(db: Session, scan: models.Scan) -> None:
    scan.status = models.ScanStatus.RUNNING
    scan.started_at = datetime.utcnow()
    db.commit()
    db.refresh(scan)

    logs: list[str] = []
    all_findings: List[NormalizedFinding] = []
    tool_outcomes: list[dict] = []
    artifacts: Dict[str, str] = {}
    orchestrator = FuzzOrchestrator(db)
    campaign = orchestrator.create_or_resume_campaign(scan)

    for tool_name in scan.tools:
        tool = TOOL_MAP.get(tool_name)
        if not tool:
            logs.append(f"Tool {tool_name} not recognized")
            continue

        result, findings = tool(scan.target)
        tool_outcomes.append(_capture_tool_outcome(tool_name, result, findings))
        logs.append(
            f"[{tool_name}] success={result.success} attempts={result.attempts}\n{result.output}\n{result.error or ''}"
        )
        all_findings.extend(findings)

        if not result.success:
            crash = orchestrator.record_crash(
                campaign,
                scan,
                seed=None,
                signature=f"{tool_name}:{scan.target}",
                description=f"{tool_name} failed against {scan.target}",
                log=result.error or "failure",
            )
            orchestrator.attempt_reproduction(crash)
        else:
            orchestrator.record_coverage(campaign, {"edges": 1})

        artifacts[tool_name] = {"stdout": result.output, "stderr": result.error}

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
    scan.tool_results = tool_outcomes
    scan.artifacts = artifacts
    scan.telemetry = {"tool_runs": tool_outcomes, "campaign": orchestrator.serialize_campaign(campaign)}
    scan.logs = "\n".join(logs)
    scan.status = models.ScanStatus.SUCCESS

    if any(not outcome.get("success") for outcome in tool_outcomes):
        scan.status = models.ScanStatus.FAILED
        orchestrator.finalize_campaign(campaign, models.FuzzCampaignStatus.FAILED)
    else:
        orchestrator.finalize_campaign(campaign, models.FuzzCampaignStatus.COMPLETED)

    db.commit()
    db.refresh(scan)
