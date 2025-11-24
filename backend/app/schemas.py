from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field

from app.models import ScanStatus, ToolRunStatus, FuzzCampaignStatus, CrashStatus


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
    webhook_url: Optional[str] = None


class ScanRead(BaseModel):
    id: str
    project_id: str
    status: ScanStatus
    tools: List[str]
    target: str
    started_at: datetime
    finished_at: Optional[datetime]
    logs: Optional[str]
    artifacts: Optional[list[dict]]
    telemetry: Optional[dict]
    webhook_url: Optional[str]

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


class ToolRunRead(BaseModel):
    id: str
    scan_id: str
    tool: str
    status: ToolRunStatus
    attempts: int
    exit_code: Optional[int]
    started_at: datetime
    finished_at: Optional[datetime]
    output: Optional[str]
    error: Optional[str]
    artifacts: Optional[list[dict]]
    metrics: Optional[dict]

    class Config:
        from_attributes = True


class ScanDetail(ScanRead):
    findings: List[FindingRead]
    tool_runs: List[ToolRunRead]


class FuzzCampaignCreate(BaseModel):
    name: str
    target: str
    strategy: Optional[str] = None
    meta: Optional[dict] = None


class FuzzCampaignRead(FuzzCampaignCreate):
    id: str
    status: FuzzCampaignStatus
    coverage: Optional[dict]
    metrics: Optional[dict]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class FuzzCampaignDetail(FuzzCampaignRead):
    seeds: List[FuzzSeedRead]
    crashes: List[CrashReportRead]
    signals: List[CoverageSignalRead]


class FuzzSeedCreate(BaseModel):
    source: str
    corpus_path: Optional[str] = None
    dedupe_key: Optional[str] = None
    coverage: Optional[dict] = None


class FuzzSeedRead(FuzzSeedCreate):
    id: str
    reproducible: CrashStatus
    created_at: datetime

    class Config:
        from_attributes = True


class CoverageSignalCreate(BaseModel):
    run_identifier: Optional[str] = None
    covered_edges: int
    functions: Optional[dict] = None


class CoverageSignalRead(CoverageSignalCreate):
    id: str
    created_at: datetime

    class Config:
        from_attributes = True


class CrashReportCreate(BaseModel):
    signature: str
    dedupe_key: Optional[str] = None
    input_reference: Optional[str] = None
    stacktrace: Optional[str] = None
    reproducer: Optional[str] = None
    meta: Optional[dict] = None
    scan_id: Optional[str] = None


class CrashReportRead(CrashReportCreate):
    id: str
    status: CrashStatus
    created_at: datetime

    class Config:
        from_attributes = True