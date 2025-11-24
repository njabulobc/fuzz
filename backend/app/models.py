from __future__ import annotations

import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Enum, ForeignKey, JSON, Text, Integer
from sqlalchemy.orm import relationship
import enum

from app.db.session import Base


class ScanStatus(str, enum.Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class ToolRunStatus(str, enum.Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    RETRIED = "RETRIED"


class FuzzCampaignStatus(str, enum.Enum):
    PLANNED = "PLANNED"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"


class CrashStatus(str, enum.Enum):
    NEW = "NEW"
    DUPLICATE = "DUPLICATE"
    CONFIRMED = "CONFIRMED"
    IGNORED = "IGNORED"


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
    artifacts = Column(JSON, nullable=True)
    telemetry = Column(JSON, nullable=True)
    webhook_url = Column(String, nullable=True)

    project = relationship("Project", back_populates="scans")
    findings = relationship("Finding", back_populates="scan", cascade="all, delete")
    tool_runs = relationship("ToolRun", back_populates="scan", cascade="all, delete")


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


class ToolRun(Base):
    __tablename__ = "tool_runs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    scan_id = Column(String, ForeignKey("scans.id"), nullable=False)
    tool = Column(String, nullable=False)
    status = Column(Enum(ToolRunStatus), default=ToolRunStatus.PENDING)
    attempts = Column(Integer, default=0)
    exit_code = Column(Integer, nullable=True)
    started_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)
    output = Column(Text, nullable=True)
    error = Column(Text, nullable=True)
    artifacts = Column(JSON, nullable=True)
    metrics = Column(JSON, nullable=True)

    scan = relationship("Scan", back_populates="tool_runs")


class FuzzCampaign(Base):
    __tablename__ = "fuzz_campaigns"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    target = Column(String, nullable=False)
    strategy = Column(String, nullable=True)
    status = Column(Enum(FuzzCampaignStatus), default=FuzzCampaignStatus.PLANNED)
    meta = Column(JSON, nullable=True)
    coverage = Column(JSON, nullable=True)
    metrics = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    seeds = relationship("FuzzSeed", back_populates="campaign", cascade="all, delete")
    crashes = relationship("CrashReport", back_populates="campaign", cascade="all, delete")
    signals = relationship("CoverageSignal", back_populates="campaign", cascade="all, delete")


class FuzzSeed(Base):
    __tablename__ = "fuzz_seeds"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    campaign_id = Column(String, ForeignKey("fuzz_campaigns.id"), nullable=False)
    source = Column(String, nullable=False)
    corpus_path = Column(String, nullable=True)
    dedupe_key = Column(String, nullable=True)
    reproducible = Column(Enum(CrashStatus), default=CrashStatus.NEW)
    coverage = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    campaign = relationship("FuzzCampaign", back_populates="seeds")


class CrashReport(Base):
    __tablename__ = "crash_reports"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    campaign_id = Column(String, ForeignKey("fuzz_campaigns.id"), nullable=False)
    scan_id = Column(String, ForeignKey("scans.id"), nullable=True)
    signature = Column(String, nullable=False)
    dedupe_key = Column(String, nullable=True)
    status = Column(Enum(CrashStatus), default=CrashStatus.NEW)
    input_reference = Column(String, nullable=True)
    stacktrace = Column(Text, nullable=True)
    reproducer = Column(Text, nullable=True)
    meta = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    campaign = relationship("FuzzCampaign", back_populates="crashes")


class CoverageSignal(Base):
    __tablename__ = "coverage_signals"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    campaign_id = Column(String, ForeignKey("fuzz_campaigns.id"), nullable=False)
    run_identifier = Column(String, nullable=True)
    covered_edges = Column(Integer, default=0)
    functions = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    campaign = relationship("FuzzCampaign", back_populates="signals")