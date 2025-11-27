
#schemas.py
from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field

from app.models import ScanStatus, ToolExecutionStatus


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
    tool_version: Optional[str]
    input_seed: Optional[str]
    coverage: Optional[dict]
    assertions: Optional[dict]
    raw: Optional[dict]

    class Config:
        from_attributes = True


class ToolExecutionRead(BaseModel):
    id: str
    scan_id: str
    tool: str
    status: ToolExecutionStatus
    attempt: int
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    duration_seconds: Optional[float]
    command: Optional[list[str]]
    exit_code: Optional[int]
    stdout_path: Optional[str]
    stderr_path: Optional[str]
    environment: Optional[dict]
    artifacts_path: Optional[str]
    error: Optional[str]
    parsing_error: Optional[str]
    failure_reason: Optional[str]
    findings_count: int
    tool_version: Optional[str]
    input_seed: Optional[str]
    coverage: Optional[dict]
    assertions: Optional[dict]

    class Config:
        from_attributes = True


class ScanDetail(ScanRead):
    findings: List[FindingRead]
    tool_executions: List[ToolExecutionRead] = Field(default_factory=list)


class QuickScanResponse(BaseModel):
    project_id: str
    scan_id: str