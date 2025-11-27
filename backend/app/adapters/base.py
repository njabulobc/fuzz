from __future__ import annotations

import subprocess
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class ToolResult:
    success: bool
    output: str
    error: str | None = None
    coverage: Optional[float] = None
    budget_seconds: Optional[float] = None
    properties: List[str] | None = None


def run_command(cmd: List[str], timeout: int = 600) -> ToolResult:
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout, check=False
        )
        return ToolResult(success=proc.returncode == 0, output=proc.stdout, error=proc.stderr)
    except subprocess.TimeoutExpired:
        return ToolResult(success=False, output="", error="timeout")
