from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import List


@dataclass
class ToolResult:
    success: bool
    output: str
    error: str | None = None
    return_code: int | None = None
    command: list[str] | None = None
    stdout_path: str | None = None
    stderr_path: str | None = None
    environment: dict[str, str] | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    duration_seconds: float | None = None
    parsing_error: str | None = None
    failure_reason: str | None = None
    artifacts_path: str | None = None
    tool_version: str | None = None


def _safe_read(path: Path) -> str:
    try:
        return path.read_text()
    except OSError:
        return ""


def run_command(
    cmd: List[str],
    timeout: int = 600,
    env: dict[str, str] | None = None,
    workdir: str | Path | None = None,
    log_dir: str | Path | None = None,
    max_runtime: int | None = None,
) -> ToolResult:
    log_dir_path = Path(log_dir or Path.cwd() / "logs")
    log_dir_path.mkdir(parents=True, exist_ok=True)
    stdout_path = log_dir_path / "stdout.log"
    stderr_path = log_dir_path / "stderr.log"

    environment = os.environ.copy()
    environment.update(env or {})

    started_at = datetime.utcnow()
    try:
        with stdout_path.open("w") as stdout, stderr_path.open("w") as stderr:
            proc = subprocess.run(
                cmd,
                stdout=stdout,
                stderr=stderr,
                text=True,
                timeout=max_runtime or timeout,
                check=False,
                cwd=workdir,
                env=environment,
            )
        finished_at = datetime.utcnow()
        output = _safe_read(stdout_path)
        error_output = _safe_read(stderr_path)
        return ToolResult(
            success=proc.returncode == 0,
            output=output,
            error=error_output or None,
            return_code=proc.returncode,
            command=cmd,
            stdout_path=str(stdout_path),
            stderr_path=str(stderr_path),
            environment=environment,
            started_at=started_at,
            finished_at=finished_at,
            duration_seconds=(finished_at - started_at).total_seconds(),
            artifacts_path=str(log_dir_path),
            failure_reason=None if proc.returncode == 0 else "non-zero-exit",
        )
    except subprocess.TimeoutExpired:
        finished_at = datetime.utcnow()
        return ToolResult(
            success=False,
            output=_safe_read(stdout_path),
            error="timeout",
            return_code=None,
            command=cmd,
            stdout_path=str(stdout_path),
            stderr_path=str(stderr_path),
            environment=environment,
            started_at=started_at,
            finished_at=finished_at,
            duration_seconds=(finished_at - started_at).total_seconds(),
            artifacts_path=str(log_dir_path),
            failure_reason="timeout",
        )
    except OSError as exc:
        finished_at = datetime.utcnow()
        return ToolResult(
            success=False,
            output=_safe_read(stdout_path),
            error=str(exc),
            return_code=None,
            command=cmd,
            stdout_path=str(stdout_path),
            stderr_path=str(stderr_path),
            environment=environment,
            started_at=started_at,
            finished_at=finished_at,
            duration_seconds=(finished_at - started_at).total_seconds(),
            artifacts_path=str(log_dir_path),
            failure_reason="crash",
        )


@lru_cache(maxsize=32)
def detect_tool_version(binary: str) -> str | None:
    try:
        proc = subprocess.run(
            [binary, "--version"], capture_output=True, text=True, timeout=10, check=False
        )
        output = (proc.stdout or proc.stderr or "").strip()
        return output.splitlines()[0] if output else None
    except OSError:
        return None
