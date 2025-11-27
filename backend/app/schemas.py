
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel, Field, model_validator

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
    project_id: str | None = None
    project_name: str | None = None
    project_path: str | None = None
    target: str | None = None
    tools: List[str] = Field(default_factory=lambda: ["slither", "mythril", "echidna"])
    scan_name: str | None = None
    log_file: str | None = None
    chain: str | None = None
    meta: Optional[dict] = None

    @model_validator(mode="after")
    def ensure_project_and_target(self):
        if not self.project_id and not (self.project_name or self.scan_name):
            raise ValueError("Provide either project_id or project_name/scan_name")

        if not self.project_name:
            self.project_name = self.scan_name

        if not self.target:
            self.target = self.log_file

        if not self.target:
            raise ValueError("Provide a target or log_file to scan")

        if not self.project_id and not self.project_path:
            if self.log_file:
                self.project_path = str(Path(self.log_file).parent or ".")
            else:
                raise ValueError("Provide project_path when creating a project")

        return self


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