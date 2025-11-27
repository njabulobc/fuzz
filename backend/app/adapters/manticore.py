from __future__ import annotations

from pathlib import Path
from typing import List

from app.adapters.base import ToolResult, detect_tool_version, run_command
from app.config import ToolSettings, get_settings
from app.normalization.findings import NormalizedFinding

settings = get_settings()


def run_manticore(
    target: str,
    *,
    config: ToolSettings,
    workdir: Path,
    log_dir: Path,
    env: dict[str, str],
) -> tuple[ToolResult, List[NormalizedFinding]]:
    cmd = [settings.manticore_path, target]
    result = run_command(
        cmd,
        timeout=config.timeout_seconds,
        env=env,
        workdir=workdir,
        log_dir=log_dir,
        max_runtime=config.max_runtime_seconds,
    )
    result.tool_version = detect_tool_version(settings.manticore_path)
    findings: List[NormalizedFinding] = []
    if not result.success:
        failure_description = result.error or "Manticore failed"
        severity = "MEDIUM"
        if result.failure_reason == "timeout":
            failure_description = "Manticore timed out"
            severity = "LOW"
        findings.append(
            NormalizedFinding(
                tool="manticore",
                title="Manticore execution issue",
                description=failure_description,
                severity=severity,
                category="execution",
                raw={"stderr": result.error, "failure_reason": result.failure_reason},
                tool_version=result.tool_version,
            )
        )
    return result, findings