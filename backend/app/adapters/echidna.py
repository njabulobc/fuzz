from __future__ import annotations

import json
from typing import List

from app.adapters.base import run_command, ToolResult
from app.normalization.findings import NormalizedFinding
from app.config import get_settings


settings = get_settings()


def run_echidna(target: str, timeout: int | None = None) -> tuple[ToolResult, List[NormalizedFinding]]:
    cmd = [settings.echidna_path, target, "--format", "json"]
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
                    )
                )
        except json.JSONDecodeError:
            pass
    return result, findings