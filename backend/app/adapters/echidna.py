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
    """
    Execute Echidna using the official trailofbits/echidna Docker image.

    We no longer call echidna-test installed on the host since the worker
    container does NOT include Echidna. Instead we call:

        docker run --rm -v <target>:<target> trailofbits/echidna echidna-test ...

    The output is still JSON, so the existing parsing logic continues to work.
    """

    abs_target = str(Path(target).resolve())

    # Build docker command
    cmd = [
        "docker", "run", "--rm",
        "-v", f"{abs_target}:{abs_target}",
        "trailofbits/echidna",
        "echidna-test", abs_target,
        "--format", "json",
    ]

    # Add fuzz duration if configured
    if config.fuzz_duration_seconds:
        cmd.extend(["--test-duration", str(config.fuzz_duration_seconds)])

    # Execute via existing run_command utility (keeps logs, timeouts, etc.)
    result = run_command(
        cmd,
        timeout=config.timeout_seconds,
        env=env,
        workdir=workdir,
        log_dir=log_dir,
        max_runtime=config.max_runtime_seconds or config.fuzz_duration_seconds,
    )

    # Dockers don’t provide versions — so we mark it explicitly
    result.tool_version = "docker:trailofbits/echidna"

    findings: List[NormalizedFinding] = []
    if result.success and result.output:
        try:
            data = json.loads(result.output)

            # Standard Echidna JSON structure: {"errors": [ ... ]}
            for issue in data.get("errors", []):
                findings.append(
                    NormalizedFinding(
                        tool="echidna",
                        title=issue.get("test", "Echidna issue"),
                        description=issue.get("message", ""),
                        severity="HIGH",  # Echidna does not label severity
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
