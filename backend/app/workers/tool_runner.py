from __future__ import annotations

import subprocess
import time
import uuid
from dataclasses import dataclass, field
from typing import Iterable, List, Tuple

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class WorkerProcessResult:
    stdout: str
    stderr: str
    returncode: int


@dataclass
class ToolExecutionTelemetry:
    worker_id: str
    attempts: int
    duration_seconds: float
    timeout_seconds: int
    resource_limits: dict
    container_image: str | None = None
    command: List[str] | None = None
    artifacts: list[str] = field(default_factory=list)
    retries_exhausted: bool = False
    timed_out: bool = False


def _run_once(cmd: List[str], timeout_seconds: int) -> Tuple[ToolExecutionTelemetry, WorkerProcessResult]:
    worker_id = str(uuid.uuid4())
    start = time.perf_counter()
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
        duration = time.perf_counter() - start
        telemetry = ToolExecutionTelemetry(
            worker_id=worker_id,
            attempts=1,
            duration_seconds=duration,
            timeout_seconds=timeout_seconds,
            resource_limits={},
            command=cmd,
            timed_out=False,
        )
        return telemetry, WorkerProcessResult(proc.stdout, proc.stderr, proc.returncode)
    except subprocess.TimeoutExpired as exc:
        duration = time.perf_counter() - start
        telemetry = ToolExecutionTelemetry(
            worker_id=worker_id,
            attempts=1,
            duration_seconds=duration,
            timeout_seconds=timeout_seconds,
            resource_limits={},
            command=cmd,
            timed_out=True,
        )
        return telemetry, WorkerProcessResult(exc.stdout or "", exc.stderr or "timeout", returncode=124)


def _merge_telemetry(samples: Iterable[ToolExecutionTelemetry]) -> ToolExecutionTelemetry:
    samples = list(samples)
    if not samples:
        return ToolExecutionTelemetry(
            worker_id="unknown",
            attempts=0,
            duration_seconds=0.0,
            timeout_seconds=0,
            resource_limits={},
        )

    duration = sum(item.duration_seconds for item in samples)
    attempts = sum(item.attempts for item in samples)
    timed_out = any(item.timed_out for item in samples)
    retries_exhausted = any(item.retries_exhausted for item in samples)
    worker_id = samples[-1].worker_id

    merged = ToolExecutionTelemetry(
        worker_id=worker_id,
        attempts=attempts,
        duration_seconds=duration,
        timeout_seconds=samples[-1].timeout_seconds,
        resource_limits=samples[-1].resource_limits,
        container_image=samples[-1].container_image,
        command=samples[-1].command,
        timed_out=timed_out,
        retries_exhausted=retries_exhausted,
    )
    merged.artifacts = [artifact for sample in samples for artifact in sample.artifacts]
    return merged


def run_in_isolated_worker(
    cmd: List[str],
    timeout_seconds: int,
    max_retries: int = 1,
    container_image: str | None = None,
    resource_limits: dict | None = None,
) -> tuple[ToolExecutionTelemetry, WorkerProcessResult]:
    """
    Run a command in a sandboxed worker with retries and emit telemetry used by the
    reporting layer. This is a lightweight facade around ``subprocess`` that keeps
    a stable interface for future container backends.
    """

    resource_limits = resource_limits or {}
    samples: list[ToolExecutionTelemetry] = []
    last_proc: WorkerProcessResult | None = None

    for attempt in range(1, max_retries + 1):
        logger.info(
            "worker.run",
            worker_image=container_image,
            command=cmd,
            attempt=attempt,
            timeout_seconds=timeout_seconds,
            resource_limits=resource_limits,
        )
        telemetry, proc = _run_once(cmd, timeout_seconds=timeout_seconds)
        telemetry.container_image = container_image
        telemetry.resource_limits = resource_limits
        samples.append(telemetry)
        last_proc = proc
        if proc.returncode == 0:
            break

    merged_telemetry = _merge_telemetry(samples)
    merged_telemetry.retries_exhausted = (last_proc.returncode != 0) if last_proc else False

    logger.info(
        "worker.finished",
        worker_id=merged_telemetry.worker_id,
        attempts=merged_telemetry.attempts,
        returncode=last_proc.returncode if last_proc else None,
        duration_seconds=merged_telemetry.duration_seconds,
        timed_out=merged_telemetry.timed_out,
    )

    return merged_telemetry, last_proc or WorkerProcessResult("", "", 1)
