from __future__ import annotations

import json
import re
from typing import List

from app.adapters.base import run_command, ToolResult
from app.normalization.findings import NormalizedFinding
from app.config import get_settings

settings = get_settings()


def run_manticore(target: str, timeout: int | None = None) -> tuple[ToolResult, List[NormalizedFinding]]:
    cmd = [settings.manticore_path, target]
    result = run_command(cmd, timeout=timeout or settings.default_timeout_seconds)
    findings: List[NormalizedFinding] = []

    if result.output:
        # prefer structured JSON output when available
        try:
            data = json.loads(result.output)
            issues = data.get("issues") or data.get("bugs") or []
            coverage = data.get("coverage")
            if isinstance(coverage, (int, float)):
                result.coverage = float(coverage)

            if isinstance(data.get("budget"), (int, float)):
                result.budget_seconds = float(data["budget"])

            for entry in issues:
                title = entry.get("title") or entry.get("description") or "Manticore finding"
                prop = entry.get("property") or entry.get("function")
                if prop:
                    result.properties = (result.properties or []) + [prop]
                findings.append(
                    NormalizedFinding(
                        tool="manticore",
                        title=title,
                        description=entry.get("message") or entry.get("description", ""),
                        severity=entry.get("severity", "MEDIUM"),
                        category=entry.get("category", "assertion"),
                        file_path=entry.get("file"),
                        line_number=str(entry.get("line", "")),
                        function=prop,
                        raw=entry,
                    )
                )

            if result.properties:
                result.properties = sorted(set(result.properties))
            return result, findings
        except json.JSONDecodeError:
            pass

        bug_matches = re.findall(r"bug\s*(\d+)?[:\-]\s*(.+)", result.output, re.IGNORECASE)
        for _, message in bug_matches:
            findings.append(
                NormalizedFinding(
                    tool="manticore",
                    title="Manticore bug discovered",
                    description=message.strip(),
                    severity="HIGH",
                    category="property-violation",
                )
            )

        coverage_match = re.search(r"coverage[^\d]*(\d+(?:\.\d+)?)", result.output, re.IGNORECASE)
        if coverage_match:
            result.coverage = float(coverage_match.group(1))

        budget_match = re.search(r"(budget|time)[^\d]*(\d+(?:\.\d+)?)(?:s|seconds)?", result.output, re.IGNORECASE)
        if budget_match:
            result.budget_seconds = float(budget_match.group(2))

    # Manticore default output not easily machine-readable; capture generic entry on failure
    if not result.success and not findings:
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
