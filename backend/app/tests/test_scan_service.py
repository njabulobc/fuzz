from datetime import datetime
import json
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import models
from app.adapters.base import ToolResult
from app.db.session import Base
from app.services import scanner
from app.normalization.findings import NormalizedFinding
from app.config import ToolSettings


def setup_sqlite(tmp_path: Path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'test.db'}", connect_args={"check_same_thread": False}, future=True
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def make_result(tmp_path: Path, success: bool = True) -> ToolResult:
    now = datetime.utcnow()
    return ToolResult(
        success=success,
        output="ok" if success else "",
        error=None if success else "error",
        return_code=0 if success else 1,
        command=["tool"],
        stdout_path=str(tmp_path / "stdout.log"),
        stderr_path=str(tmp_path / "stderr.log"),
        environment={},
        started_at=now,
        finished_at=now,
        duration_seconds=0.1,
        parsing_error=None,
        failure_reason=None if success else "non-zero-exit",
        artifacts_path=str(tmp_path),
        tool_version="1.0.0",
    )


def test_execute_scan_collects_findings(monkeypatch, tmp_path):
    SessionLocal = setup_sqlite(tmp_path)
    monkeypatch.setattr(scanner, "SessionLocal", SessionLocal)
    scanner.settings.storage_path = str(tmp_path)
    scanner.settings.fake_results_probability = 0
    monkeypatch.setattr(scanner.settings, "tool_settings", {"default": ToolSettings(retries=0)})

    db = SessionLocal()
    project = models.Project(id="p1", name="proj", path=str(tmp_path))
    db.add(project)
    db.commit()

    target = tmp_path / "file.sol"
    target.write_text("contract Test {}")

    scan = models.Scan(id="s1", project_id=project.id, target=str(target), tools=["slither"])
    db.add(scan)
    db.commit()
    db.refresh(scan)

    def fake_tool(target, config=None, workdir=None, log_dir=None, env=None):  # noqa: ARG001
        return make_result(tmp_path), [
            NormalizedFinding(
                tool="slither",
                title="issue",
                description="desc",
                severity="HIGH",
                category="reentrancy",
                file_path="file.sol",
                line_number="1",
                function="f",
                raw={"a": 1},
                tool_version="1.0.0",
            )
        ]

    monkeypatch.setattr(scanner, "TOOL_MAP", {"slither": fake_tool})

    scanner.execute_scan(db, scan)
    db.refresh(scan)

    assert scan.status == models.ScanStatus.SUCCESS
    findings = db.query(models.Finding).filter(models.Finding.scan_id == scan.id).all()
    assert findings, "findings should be added"
    tool_runs = db.query(models.ToolExecution).filter_by(scan_id=scan.id).all()
    assert tool_runs[0].stdout_path


def test_execute_scan_handles_unknown_tool(monkeypatch, tmp_path):
    SessionLocal = setup_sqlite(tmp_path)
    monkeypatch.setattr(scanner, "SessionLocal", SessionLocal)
    scanner.settings.storage_path = str(tmp_path)
    scanner.settings.fake_results_probability = 0
    monkeypatch.setattr(scanner.settings, "tool_settings", {"default": ToolSettings(retries=0)})

    db = SessionLocal()
    project = models.Project(id="p1", name="proj", path=str(tmp_path))
    db.add(project)
    db.commit()

    target = tmp_path / "file.sol"
    target.write_text("contract Test {}")

    scan = models.Scan(id="s1", project_id=project.id, target=str(target), tools=["missing-tool"])
    db.add(scan)
    db.commit()
    db.refresh(scan)

    monkeypatch.setattr(scanner, "TOOL_MAP", {})

    scanner.execute_scan(db, scan)
    db.refresh(scan)

    assert scan.status == models.ScanStatus.FAILED
    logs = json.loads(scan.logs)
    assert logs[0]["status"] == models.ToolExecutionStatus.FAILED.value


def test_execute_scan_persists_failure_findings(monkeypatch, tmp_path):
    SessionLocal = setup_sqlite(tmp_path)
    monkeypatch.setattr(scanner, "SessionLocal", SessionLocal)
    scanner.settings.storage_path = str(tmp_path)
    scanner.settings.fake_results_probability = 0
    monkeypatch.setattr(scanner.settings, "tool_settings", {"default": ToolSettings(retries=0)})

    db = SessionLocal()
    project = models.Project(id="p1", name="proj", path=str(tmp_path))
    db.add(project)
    db.commit()

    target = tmp_path / "file.sol"
    target.write_text("contract Test {}")

    scan = models.Scan(id="s1", project_id=project.id, target=str(target), tools=["manticore"])
    db.add(scan)
    db.commit()
    db.refresh(scan)

    def failing_tool(target, config=None, workdir=None, log_dir=None, env=None):  # noqa: ARG001
        finding = NormalizedFinding(
            tool="manticore",
            title="Execution failed",
            description="timed out",
            severity="LOW",
            category="execution",
            raw={"stderr": "timeout", "failure_reason": "timeout"},
            tool_version="1.0.0",
        )
        return make_result(tmp_path, success=False), [finding]

    monkeypatch.setattr(scanner, "TOOL_MAP", {"manticore": failing_tool})

    scanner.execute_scan(db, scan)
    db.refresh(scan)

    assert scan.status == models.ScanStatus.FAILED
    findings = db.query(models.Finding).filter(models.Finding.scan_id == scan.id).all()
    assert findings, "failure findings should be stored"
    assert findings[0].tool == "manticore"


def test_execute_scan_is_idempotent(monkeypatch, tmp_path):
    SessionLocal = setup_sqlite(tmp_path)
    monkeypatch.setattr(scanner, "SessionLocal", SessionLocal)
    scanner.settings.storage_path = str(tmp_path)
    scanner.settings.fake_results_probability = 0

    db = SessionLocal()
    project = models.Project(id="p1", name="proj", path=str(tmp_path))
    db.add(project)
    db.commit()

    scan = models.Scan(
        id="s1",
        project_id="p1",
        target=str(tmp_path / "file.sol"),
        tools=["slither"],
        status=models.ScanStatus.SUCCESS,
    )
    db.add(scan)
    db.commit()

    scanner.execute_scan(db, scan)
    db.refresh(scan)

    assert scan.status == models.ScanStatus.SUCCESS


def test_fake_findings_can_be_injected(monkeypatch, tmp_path):
    SessionLocal = setup_sqlite(tmp_path)
    monkeypatch.setattr(scanner, "SessionLocal", SessionLocal)
    scanner.settings.storage_path = str(tmp_path)
    scanner.settings.fake_results_probability = 1.0
    monkeypatch.setattr(scanner.settings, "tool_settings", {"default": ToolSettings(retries=0)})

    db = SessionLocal()
    project = models.Project(id="p1", name="proj", path=str(tmp_path))
    db.add(project)
    db.commit()

    target = tmp_path / "file.sol"
    target.write_text("contract Test {}")

    scan = models.Scan(id="s1", project_id=project.id, target=str(target), tools=["slither"])
    db.add(scan)
    db.commit()
    db.refresh(scan)

    def failing_tool(target, config=None, workdir=None, log_dir=None, env=None):  # noqa: ARG001
        return make_result(tmp_path, success=False), []

    monkeypatch.setattr(scanner, "TOOL_MAP", {"slither": failing_tool})

    scanner.execute_scan(db, scan)
    db.refresh(scan)

    tool_runs = db.query(models.ToolExecution).filter_by(scan_id=scan.id).all()
    findings = db.query(models.Finding).filter(models.Finding.scan_id == scan.id).all()

    assert scan.status == models.ScanStatus.SUCCESS
    assert tool_runs[0].status == models.ToolExecutionStatus.SUCCEEDED
    assert findings, "synthetic findings should be stored when injected"
