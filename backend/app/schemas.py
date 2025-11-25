from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field

from app.models import (
    CrashReproductionStatus,
    FuzzCampaignStatus,
    ScanStatus,
)


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


class ContractGenerationResponse(BaseModel):
    contract_name: str
    contract_path: str
    contract_source: str
    project: ProjectRead
    scan: ScanRead


class ToolOutcome(BaseModel):
    tool: str
    success: bool
    output: str
    error: Optional[str]
    attempts: int
    duration_seconds: Optional[float]
    artifacts: List[str] = Field(default_factory=list)
    telemetry: Optional[dict]
    findings: int = 0


class ScanRead(BaseModel):
    id: str
    project_id: str
    status: ScanStatus
    tools: List[str]
    target: str
    started_at: datetime
    finished_at: Optional[datetime]
    logs: Optional[str]
    tool_results: Optional[List[ToolOutcome]] = Field(default_factory=list)
    telemetry: Optional[dict]
    artifacts: Optional[dict]

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
    crash_reports: List["CrashReportRead"] = Field(default_factory=list)
    campaigns: List["FuzzCampaignRead"] = Field(default_factory=list)


class FuzzCampaignRead(BaseModel):
    id: str
    scan_id: str
    name: str
    strategy: str
    status: FuzzCampaignStatus
    coverage_metrics: Optional[dict]
    seed_pool: Optional[list]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class FuzzCampaignDetail(FuzzCampaignRead):
    seeds: List["CorpusSeedRead"] = Field(default_factory=list)
    crash_reports: List["CrashReportRead"] = Field(default_factory=list)


class CorpusSeedRead(BaseModel):
    id: str
    campaign_id: str
    value: str
    origin: Optional[str]
    coverage: Optional[dict]
    metadata: Optional[dict]
    created_at: datetime

    class Config:
        from_attributes = True


class CrashReportRead(BaseModel):
    id: str
    campaign_id: Optional[str]
    scan_id: Optional[str]
    seed_id: Optional[str]
    signature: str
    description: str
    reproduction_status: CrashReproductionStatus
    dedup_hash: Optional[str]
    log: Optional[str]
    trace: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


ScanDetail.model_rebuild()
FuzzCampaignDetail.model_rebuild()