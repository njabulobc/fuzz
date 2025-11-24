from __future__ import annotations

from typing import Any, Dict, List

from app import models


def _tool_driver(tool_run: models.ToolRun) -> Dict[str, Any]:
    return {
        "name": tool_run.tool,
        "status": str(tool_run.status),
        "attempts": tool_run.attempts,
        "metrics": tool_run.metrics or {},
    }


def build_scan_report(scan: models.Scan, include_findings: bool = True) -> Dict[str, Any]:
    return {
        "id": scan.id,
        "project_id": scan.project_id,
        "target": scan.target,
        "status": str(scan.status),
        "tools": [_tool_driver(tr) for tr in scan.tool_runs],
        "findings": [
            {
                "id": f.id,
                "tool": f.tool,
                "title": f.title,
                "severity": f.severity,
                "category": f.category,
                "file_path": f.file_path,
                "line_number": f.line_number,
            }
            for f in scan.findings
        ]
        if include_findings
        else [],
        "artifacts": scan.artifacts or [],
        "telemetry": scan.telemetry or {},
    }


def build_sarif(scan: models.Scan) -> Dict[str, Any]:
    results: List[Dict[str, Any]] = []
    for finding in scan.findings:
        results.append(
            {
                "ruleId": finding.category or finding.title,
                "level": finding.severity.lower(),
                "message": {"text": finding.description},
                "locations": [
                    {
                        "physicalLocation": {
                            "artifactLocation": {"uri": finding.file_path or scan.target},
                            "region": {
                                "startLine": int(finding.line_number)
                                if finding.line_number and finding.line_number.isdigit()
                                else 0
                            },
                        }
                    }
                ],
                "properties": {"tool": finding.tool, "function": finding.function},
            }
        )

    return {
        "version": "2.1.0",
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "scan-platform",
                        "informationUri": "https://example.com",
                        "rules": [
                            {
                                "id": tr.tool,
                                "properties": tr.metrics or {},
                            }
                            for tr in scan.tool_runs
                        ],
                    }
                },
                "invocations": [
                    {
                        "executionSuccessful": scan.status == models.ScanStatus.SUCCESS,
                        "stdout": scan.logs,
                        "properties": {"artifacts": scan.artifacts or []},
                    }
                ],
                "results": results,
            }
        ],
    }
