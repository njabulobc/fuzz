
#schemas.py
from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field

from app.models import ScanStatus


class ProjectCreate(BaseModel):
    name: str
    path: str
    meta: Optional[dict] = None


class ProjectRead(ProjectCreate):
    id: str
    created_at: datetime

    class Config:
        from_attributes = True


class ScanRequest(BaseModel):
    project_id: str
    target: str
    tools: List[str] = Field(default_factory=lambda: ["slither", "mythril", "echidna"])


class QuickScanProject(BaseModel):
    name: str
    path: str
    meta: Optional[dict] = None


class QuickScanRequest(BaseModel):
    project: QuickScanProject
    target: str
    tools: List[str] = Field(default_factory=lambda: ["slither", "mythril", "echidna"])


class ScanRead(BaseModel):
    id: str
    project_id: str
    status: ScanStatus
    tools: List[str]
    target: str
    started_at: datetime
    finished_at: Optional[datetime]
    logs: Optional[str]

    class Config:
        from_attributes = True


class FindingRead(BaseModel):
    id: str
    scan_id: str
    tool: str
    title: str
    description: str
    severity: str
    category: Optional[str]
    file_path: Optional[str]
    line_number: Optional[str]
    function: Optional[str]
    raw: Optional[dict]

    class Config:
        from_attributes = True


class ScanDetail(ScanRead):
    findings: List[FindingRead]


class QuickScanResponse(BaseModel):
    project_id: str
    scan_id: str