from __future__ import annotations

import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Enum, ForeignKey, JSON, Text, Integer, Float
from sqlalchemy.orm import relationship
import enum

from app.db.session import Base


class ScanStatus(str, enum.Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class ToolExecutionStatus(str, enum.Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    RETRYING = "RETRYING"
    SUCCEEDED = "SUCCEEDED"
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

    project = relationship("Project", back_populates="scans")
    findings = relationship("Finding", back_populates="scan", cascade="all, delete")
    tool_executions = relationship(
        "ToolExecution", back_populates="scan", cascade="all, delete"
    )


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
    tool_version = Column(String, nullable=True)
    input_seed = Column(String, nullable=True)
    coverage = Column(JSON, nullable=True)
    assertions = Column(JSON, nullable=True)
    raw = Column(JSON, nullable=True)

    scan = relationship("Scan", back_populates="findings")


class ToolExecution(Base):
    __tablename__ = "tool_executions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    scan_id = Column(String, ForeignKey("scans.id"), nullable=False)
    tool = Column(String, nullable=False)
    status = Column(Enum(ToolExecutionStatus), default=ToolExecutionStatus.PENDING)
    attempt = Column(Integer, default=0)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Float, nullable=True)
    command = Column(JSON, nullable=True)
    exit_code = Column(Integer, nullable=True)
    stdout_path = Column(String, nullable=True)
    stderr_path = Column(String, nullable=True)
    environment = Column(JSON, nullable=True)
    artifacts_path = Column(String, nullable=True)
    error = Column(Text, nullable=True)
    parsing_error = Column(Text, nullable=True)
    failure_reason = Column(String, nullable=True)
    findings_count = Column(Integer, default=0)
    tool_version = Column(String, nullable=True)
    input_seed = Column(String, nullable=True)
    coverage = Column(JSON, nullable=True)
    assertions = Column(JSON, nullable=True)

    scan = relationship("Scan", back_populates="tool_executions")