from __future__ import annotations

import json
from typing import List

from app.adapters.base import run_command, ToolResult
from app.normalization.findings import NormalizedFinding
from app.config import get_settings


settings = get_settings()


def run_echidna(target: str, timeout: int | None = None) -> tuple[ToolResult, List[NormalizedFinding]]:
    cmd = [settings.echidna_path, target, "--format", "json"]

    if settings.echidna_config_path:
        cmd.extend(["--config", settings.echidna_config_path])
    if settings.echidna_seed_corpus:
        cmd.extend(["--seed-corpus", settings.echidna_seed_corpus])
    if settings.echidna_test_limit:
        cmd.extend(["--test-limit", str(settings.echidna_test_limit)])
    for prop in settings.echidna_property_filters:
        cmd.extend(["--property", prop])
    if settings.fuzz_budget_seconds:
        cmd.extend(["--test-duration", str(settings.fuzz_budget_seconds)])
    cmd.extend(settings.echidna_extra_args)

    result = run_command(cmd, timeout=timeout or settings.default_timeout_seconds)
    findings: List[NormalizedFinding] = []

    if result.success and result.output:
        try:
            data = json.loads(result.output)
            coverage_data = data.get("coverage")
            if isinstance(coverage_data, (int, float)):
                result.coverage = float(coverage_data)
            elif isinstance(coverage_data, dict):
                overall = coverage_data.get("overall") or coverage_data.get("total")
                if isinstance(overall, (int, float)):
                    result.coverage = float(overall)

            budget = data.get("testBudget") or data.get("duration")
            if isinstance(budget, (int, float)):
                result.budget_seconds = float(budget)

            for issue in data.get("errors", []):
                property_name = issue.get("property")
                if property_name:
                    result.properties = (result.properties or []) + [property_name]
                findings.append(
                    NormalizedFinding(
                        tool="echidna",
                        title=issue.get("test", "echidna failure"),
                        description=issue.get("message", ""),
                        severity="HIGH",
                        category="property-violation",
                        file_path=issue.get("contract"),
                        line_number=str(issue.get("line", "?")),
                        function=property_name,
                        raw=issue,
                    )
                )

            if result.properties:
                result.properties = sorted(set(result.properties))
        except json.JSONDecodeError:
            pass
    return result, findings
