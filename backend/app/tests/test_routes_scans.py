from __future__ import annotations

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

TEST_DATABASE_URL = "sqlite:///./test_routes_scans.db"

Path("test_routes_scans.db").unlink(missing_ok=True)

os.environ["DATABASE_URL"] = TEST_DATABASE_URL

from app import config as app_config

app_config.get_settings.cache_clear()

from app.main import app
from app import models
from app.db.session import Base
from app.routes import scans


engine = create_engine(
    TEST_DATABASE_URL, connect_args={"check_same_thread": False}, future=True
)
TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def setup_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    app.dependency_overrides[scans.get_db] = override_get_db
    yield
    app.dependency_overrides.pop(scans.get_db, None)
    Path("test_routes_scans.db").unlink(missing_ok=True)


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setattr(scans.run_scan_task, "delay", lambda scan_id: None)
    return TestClient(app)


def test_start_scan_accepts_log_file(monkeypatch, tmp_path: Path, client: TestClient):
    workspace = tmp_path / "contracts"
    workspace.mkdir()
    log_file = workspace / "Sample.sol"
    log_file.write_text("contract Sample {}")

    payload = {
        "scan_name": "DemoProject",
        "log_file": str(log_file),
        "chain": "sepolia",
        "tools": ["slither"],
    }

    response = client.post("/api/scans", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["target"] == str(log_file)

    with TestingSessionLocal() as db:
        project = db.query(models.Project).filter_by(id=data["project_id"]).first()
        assert project is not None
        assert project.name == "DemoProject"
        assert project.path == str(workspace)
        assert project.meta.get("chain") == "sepolia"

