from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


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
    raw: Optional[dict] = None