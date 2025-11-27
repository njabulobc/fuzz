from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class NormalizedFinding:
    tool: str
    title: str
    description: str
    severity: str
    category: Optional[str] = None
    file_path: Optional[str] = None
    line_number: Optional[str] = None
    function: Optional[str] = None
    tool_version: Optional[str] = None
    input_seed: Optional[str] = None
    coverage: Optional[dict[str, Any]] = None
    assertions: Optional[dict[str, Any]] = None
    raw: Optional[dict] = None