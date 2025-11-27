from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, List

from app.adapters.base import ToolResult, detect_tool_version, run_command
from app.config import ToolSettings, get_settings
from app.normalization.findings import NormalizedFinding

settings = get_settings()


_FAILURE_STATUSES = {"fail", "failed", "failure", "error", "panic"}


def _iter_dicts(obj: object) -> Iterable[dict]:
    if isinstance(obj, dict):
        yield obj
        for value in obj.values():
            yield from _iter_dicts(value)
    elif isinstance(obj, list):
        for item in obj:
            yield from _iter_dicts(item)


def _extract_findings(payload: object, tool_version: str | None) -> List[NormalizedFinding]:
    findings: List[NormalizedFinding] = []
    for entry in _iter_dicts(payload):
        status = str(entry.get("status", "")).lower() if isinstance(entry.get("status"), str) else ""
        success = entry.get("success")
        is_failure = status in _FAILURE_STATUSES or success is False
        if not is_failure:
            continue

        name = entry.get("name") or entry.get("test") or "Foundry test failure"
        description = (
            entry.get("reason")
            or entry.get("error_message")
            or entry.get("stdout")
            or "Foundry reported a failing test"
        )
        findings.append(
            NormalizedFinding(
                tool="foundry",
                title=str(name),
                description=str(description),
                severity="HIGH",
                category=str(entry.get("kind") or "test_failure"),
                file_path=entry.get("file") or entry.get("source") or entry.get("path"),
                line_number=str(entry.get("line")) if entry.get("line") else None,
                function=entry.get("contract") or entry.get("test_contract") or entry.get("function"),
                raw=entry,
                tool_version=tool_version,
            )
        )
    return findings


def _parse_foundry_output(output: str, tool_version: str | None) -> List[NormalizedFinding]:
    findings: List[NormalizedFinding] = []
    for line in output.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        findings.extend(_extract_findings(payload, tool_version))
    return findings


def run_foundry(
    target: str,
    *,
    config: ToolSettings,
    workdir: Path,
    log_dir: Path,
    env: dict[str, str],
) -> tuple[ToolResult, List[NormalizedFinding]]:
    target_path = Path(target)
    project_root = target_path.parent

    cmd = [
        settings.foundry_path,
        "test",
        "--json",
        "--root",
        str(project_root),
    ]

    if target_path.is_file():
        cmd.extend(["--match-path", str(target_path)])

    result = run_command(
        cmd,
        timeout=config.timeout_seconds,
        env=env,
        workdir=workdir,
        log_dir=log_dir,
        max_runtime=config.max_runtime_seconds,
    )

    result.tool_version = detect_tool_version(settings.foundry_path)
    findings = _parse_foundry_output(result.output or "", result.tool_version)

    if not findings and not result.success:
        result.failure_reason = result.failure_reason or "command-failed"

    return result, findings
