from __future__ import annotations

from typing import List

from app.adapters.base import run_command, ToolResult
from app.normalization.findings import NormalizedFinding
from app.config import get_settings

settings = get_settings()


def run_manticore(target: str, timeout: int | None = None) -> tuple[ToolResult, List[NormalizedFinding]]:
    cmd = [settings.manticore_path, target]
    result = run_command(cmd, timeout=timeout or settings.default_timeout_seconds)
    findings: List[NormalizedFinding] = []
    # Manticore default output not easily machine-readable; capture generic entry on failure
    if not result.success:
        findings.append(
            NormalizedFinding(
                tool="manticore",
                title="Manticore execution issue",
                description=result.error or "Manticore failed",
                severity="MEDIUM",
                category="execution",
                raw={"stderr": result.error},
            )
        )
    return result, findings