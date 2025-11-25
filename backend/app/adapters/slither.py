from __future__ import annotations

import json
from typing import List

from app.adapters.base import run_command, ToolResult
from app.normalization.findings import NormalizedFinding
from app.config import get_settings


settings = get_settings()


def run_slither(target: str, timeout: int | None = None) -> tuple[ToolResult, List[NormalizedFinding]]:
    cmd = [settings.slither_path, target, "--json", "-"]
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
            for issue in data.get("results", {}).get("detectors", []):
                findings.append(
                    NormalizedFinding(
                        tool="slither",
                        title=issue.get("check", "slither finding"),
                        description=issue.get("description", ""),
                        severity=issue.get("impact", "INFO").upper(),
                        category=issue.get("check"),
                        file_path=issue.get("elements", [{}])[0].get("source_mapping", {}).get("filename_relative"),
                        line_number=str(issue.get("elements", [{}])[0].get("source_mapping", {}).get("lines", ["?"])[0]),
                        function=issue.get("elements", [{}])[0].get("type"),
                        raw=issue,
                    )
                )
        except json.JSONDecodeError:
            pass
    return result, findings