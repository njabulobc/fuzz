from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class ToolResult:
    success: bool
    output: str
    error: str | None = None
    exit_code: Optional[int] = None
    runtime_seconds: Optional[float] = None


def run_command(cmd: List[str], timeout: int = 600) -> ToolResult:
    start = time.monotonic()
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout, check=False
        )
        return ToolResult(
            success=proc.returncode == 0,
            output=proc.stdout,
            error=proc.stderr,
            exit_code=proc.returncode,
            runtime_seconds=round(time.monotonic() - start, 3),
        )
    except subprocess.TimeoutExpired:
        return ToolResult(
            success=False,
            output="",
            error="timeout",
            exit_code=None,
            runtime_seconds=round(time.monotonic() - start, 3),
        )