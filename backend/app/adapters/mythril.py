from __future__ import annotations

import json
from pathlib import Path
from typing import List

from app.adapters.base import ToolResult, detect_tool_version, run_command
from app.config import ToolSettings, get_settings
from app.normalization.findings import NormalizedFinding


settings = get_settings()


def run_mythril(
    target: str,
    *,
    config: ToolSettings,
    workdir: Path,
    log_dir: Path,
    env: dict[str, str],
) -> tuple[ToolResult, List[NormalizedFinding]]:
    cmd = [settings.mythril_path, "analyze", target, "-o", "json"]
    result = run_command(
        cmd,
        timeout=config.timeout_seconds,
        env=env,
        workdir=workdir,
        log_dir=log_dir,
        max_runtime=config.max_runtime_seconds,
    )
    result.tool_version = detect_tool_version(settings.mythril_path)
    findings: List[NormalizedFinding] = []
    if result.success and result.output:
        try:
            data = json.loads(result.output)
            for issue in data.get("issues", []):
                findings.append(
                    NormalizedFinding(
                        tool="mythril",
                        title=issue.get("title", "mythril finding"),
                        description=issue.get("description", ""),
                        severity=issue.get("severity", "INFO").upper(),
                        category=issue.get("swcID"),
                        file_path=issue.get("filename"),
                        line_number=str(issue.get("lineno", "?")),
                        function=issue.get("function"),
                        raw=issue,
                        tool_version=result.tool_version,
                    )
                )
        except json.JSONDecodeError as exc:
            result.parsing_error = str(exc)
            result.failure_reason = result.failure_reason or "parse-error"
    return result, findings