from __future__ import annotations

import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Enum, ForeignKey, JSON, Text
from sqlalchemy.orm import relationship
import enum

from app.db.session import Base


class ScanStatus(str, enum.Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class Project(Base):
    __tablename__ = "projects"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, unique=True, nullable=False)
    path = Column(String, nullable=False)
    meta = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    scans = relationship("Scan", back_populates="project", cascade="all, delete")


class Scan(Base):
    __tablename__ = "scans"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    status = Column(Enum(ScanStatus), default=ScanStatus.PENDING)
    tools = Column(JSON, nullable=False)
    target = Column(String, nullable=False)
    started_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)
    logs = Column(Text, nullable=True)
    tool_results = Column(JSON, nullable=True)
    artifacts = Column(JSON, nullable=True)
    telemetry = Column(JSON, nullable=True)

    project = relationship("Project", back_populates="scans")
    findings = relationship("Finding", back_populates="scan", cascade="all, delete")
    crash_reports = relationship("CrashReport", back_populates="scan", cascade="all, delete")
    campaigns = relationship("FuzzCampaign", back_populates="scan", cascade="all, delete")


class Finding(Base):
    __tablename__ = "findings"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    scan_id = Column(String, ForeignKey("scans.id"), nullable=False)
    tool = Column(String, nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    severity = Column(String, nullable=False)
    category = Column(String, nullable=True)
    file_path = Column(String, nullable=True)
    line_number = Column(String, nullable=True)
    function = Column(String, nullable=True)
    raw = Column(JSON, nullable=True)

    scan = relationship("Scan", back_populates="findings")


class FuzzCampaignStatus(str, enum.Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class FuzzCampaign(Base):
    __tablename__ = "fuzz_campaigns"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    scan_id = Column(String, ForeignKey("scans.id"), nullable=False)
    name = Column(String, nullable=False)
    strategy = Column(String, nullable=False, default="coverage-guided")
    status = Column(Enum(FuzzCampaignStatus), default=FuzzCampaignStatus.PENDING)
    coverage_metrics = Column(JSON, nullable=True)
    seed_pool = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

    scan = relationship("Scan", back_populates="campaigns")
    seeds = relationship("CorpusSeed", back_populates="campaign", cascade="all, delete")
    crash_reports = relationship("CrashReport", back_populates="campaign", cascade="all, delete")


class CorpusSeed(Base):
    __tablename__ = "corpus_seeds"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    campaign_id = Column(String, ForeignKey("fuzz_campaigns.id"), nullable=False)
    value = Column(Text, nullable=False)
    origin = Column(String, nullable=True)
    coverage = Column(JSON, nullable=True)
    metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    campaign = relationship("FuzzCampaign", back_populates="seeds")


class CrashReproductionStatus(str, enum.Enum):
    NEW = "NEW"
    DEDUPED = "DEDUPED"
    REPRODUCIBLE = "REPRODUCIBLE"
    FLAKY = "FLAKY"
    INVALID = "INVALID"


class CrashReport(Base):
    __tablename__ = "crash_reports"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    campaign_id = Column(String, ForeignKey("fuzz_campaigns.id"), nullable=True)
    scan_id = Column(String, ForeignKey("scans.id"), nullable=True)
    seed_id = Column(String, ForeignKey("corpus_seeds.id"), nullable=True)
    signature = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    reproduction_status = Column(Enum(CrashReproductionStatus), default=CrashReproductionStatus.NEW)
    dedup_hash = Column(String, nullable=True)
    log = Column(Text, nullable=True)
    trace = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    campaign = relationship("FuzzCampaign", back_populates="crash_reports")
    scan = relationship("Scan", back_populates="crash_reports")
    seed = relationship("CorpusSeed")
