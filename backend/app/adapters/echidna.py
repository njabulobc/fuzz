from __future__ import annotations

import json
from pathlib import Path
from typing import List

from app.adapters.base import ToolResult, detect_tool_version, run_command
from app.config import ToolSettings, get_settings
from app.normalization.findings import NormalizedFinding


settings = get_settings()


def run_echidna(
    target: str,
    *,
    config: ToolSettings,
    workdir: Path,
    log_dir: Path,
    env: dict[str, str],
) -> tuple[ToolResult, List[NormalizedFinding]]:
    cmd = [settings.echidna_path, target, "--format", "json"]
    if config.fuzz_duration_seconds:
        cmd.extend(["--test-duration", str(config.fuzz_duration_seconds)])
    result = run_command(
        cmd,
        timeout=config.timeout_seconds,
        env=env,
        workdir=workdir,
        log_dir=log_dir,
        max_runtime=config.max_runtime_seconds or config.fuzz_duration_seconds,
    )
    result.tool_version = detect_tool_version(settings.echidna_path)
    findings: List[NormalizedFinding] = []
    if result.success and result.output:
        try:
            data = json.loads(result.output)
            for issue in data.get("errors", []):
                findings.append(
                    NormalizedFinding(
                        tool="echidna",
                        title=issue.get("test", "echidna failure"),
                        description=issue.get("message", ""),
                        severity="HIGH",
                        category="property-violation",
                        file_path=issue.get("contract"),
                        line_number=str(issue.get("line", "?")),
                        function=issue.get("property"),
                        raw=issue,
                        tool_version=result.tool_version,
                        input_seed=issue.get("seed"),
                        assertions=issue.get("property"),
                    )
                )
        except json.JSONDecodeError as exc:
            result.parsing_error = str(exc)
            result.failure_reason = result.failure_reason or "parse-error"
    return result, findings