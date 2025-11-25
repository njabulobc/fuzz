from __future__ import annotations

import json
from typing import List

from app.adapters.base import run_command, ToolResult
from app.normalization.findings import NormalizedFinding
from app.config import get_settings


settings = get_settings()


def run_mythril(target: str, timeout: int | None = None) -> tuple[ToolResult, List[NormalizedFinding]]:
    cmd = [settings.mythril_path, "analyze", target, "-o", "json"]
    result = run_command(
        cmd,
        timeout=timeout or settings.default_timeout_seconds,
        max_retries=settings.default_max_retries,
        worker_image=settings.worker_container_image,
        resource_limits=settings.worker_resource_limits,
    )
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
                    )
                )
        except json.JSONDecodeError:
            pass
    return result, findings