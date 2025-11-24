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

    project = relationship("Project", back_populates="scans")
    findings = relationship("Finding", back_populates="scan", cascade="all, delete")


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