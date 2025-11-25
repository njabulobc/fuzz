from __future__ import annotations

import json
from typing import List, Tuple

import requests
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app import models


def _finding_to_sarif_result(finding: models.Finding) -> dict:
    try:
        start_line = int(finding.line_number)
    except (TypeError, ValueError):
        start_line = 1

    return {
        "ruleId": finding.category or finding.title,
        "level": finding.severity.lower(),
        "message": {"text": finding.description},
        "locations": [
            {
                "physicalLocation": {
                    "artifactLocation": {"uri": finding.file_path or "unknown"},
                    "region": {"startLine": start_line},
                }
            }
        ],
    }


def generate_sarif(scan: models.Scan) -> dict:
    return {
        "$schema": "https://schemastore.azurewebsites.net/schemas/json/sarif-2.1.0.json",
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "fuzz-orchestrator",
                        "informationUri": "https://example.com/docs",
                        "rules": [],
                    }
                },
                "results": [_finding_to_sarif_result(f) for f in scan.findings],
                "properties": {
                    "tool_results": scan.tool_results or [],
                    "telemetry": scan.telemetry or {},
                    "campaigns": [
                        {"id": c.id, "status": str(c.status), "coverage": c.coverage_metrics}
                        for c in scan.campaigns
                    ],
                },
            }
        ],
    }


def generate_json_report(scan: models.Scan) -> dict:
    return {
        "scan": {
            "id": scan.id,
            "status": scan.status,
            "target": scan.target,
            "tools": scan.tools,
            "tool_results": scan.tool_results,
            "telemetry": scan.telemetry,
            "artifacts": scan.artifacts,
            "findings": [
                {
                    "id": f.id,
                    "tool": f.tool,
                    "severity": f.severity,
                    "title": f.title,
                    "description": f.description,
                    "file_path": f.file_path,
                    "line_number": f.line_number,
                }
                for f in scan.findings
            ],
            "crashes": [
                {
                    "id": c.id,
                    "signature": c.signature,
                    "status": str(c.reproduction_status),
                    "log": c.log,
                }
                for c in scan.crash_reports
            ],
        }
    }


def dispatch_webhook(url: str, payload: dict) -> Tuple[int, str]:
    try:
        response = requests.post(url, json=payload, timeout=10)
        return response.status_code, response.text
    except requests.RequestException as exc:  # pragma: no cover
        raise HTTPException(status_code=502, detail=str(exc))


def export_sarif_bytes(scan: models.Scan) -> bytes:
    sarif_doc = generate_sarif(scan)
    return json.dumps(sarif_doc, default=str, indent=2).encode()


def export_json_bytes(scan: models.Scan) -> bytes:
    return json.dumps(generate_json_report(scan), default=str, indent=2).encode()

