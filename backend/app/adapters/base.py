from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from app.workers.tool_runner import ToolExecutionTelemetry, run_in_isolated_worker


@dataclass
class ToolResult:
    success: bool
    output: str
    error: str | None = None
    attempts: int = 1
    duration_seconds: float | None = None
    exit_code: int | None = None
    artifacts: list[str] = field(default_factory=list)
    telemetry: Optional[ToolExecutionTelemetry] = None


def run_command(
    cmd: List[str],
    timeout: int = 600,
    max_retries: int = 1,
    worker_image: str | None = None,
    resource_limits: dict | None = None,
) -> ToolResult:
    """
    Execute a tool command inside an isolated worker with retries, resource limits,
    and rich telemetry. While the underlying implementation still uses subprocess
    for portability in the dev environment, all calls funnel through
    ``run_in_isolated_worker`` to centralize retry, timeout, and monitoring logic.
    """

    telemetry, proc = run_in_isolated_worker(
        cmd,
        timeout_seconds=timeout,
        max_retries=max_retries,
        resource_limits=resource_limits or {},
        container_image=worker_image,
    )

    success = proc.returncode == 0
    return ToolResult(
        success=success,
        output=proc.stdout,
        error=proc.stderr,
        attempts=telemetry.attempts,
        duration_seconds=telemetry.duration_seconds,
        exit_code=proc.returncode,
        artifacts=telemetry.artifacts,
        telemetry=telemetry,
    )