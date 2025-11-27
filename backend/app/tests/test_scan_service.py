from app import models
from app.services import scanner


class DummyResult:
    def __init__(self, success=True):
        self.success = success
        self.output = "ok"
        self.error = None


def test_execute_scan_collects_findings(monkeypatch, tmp_path):
    project = models.Project(id="p1", name="proj", path=str(tmp_path))
    scan = models.Scan(id="s1", project_id="p1", target="/tmp/file.sol", tools=["slither"])

    def fake_tool(target, timeout=None):  # noqa: ARG001 - test helper
        return DummyResult(True), [
            scanner.NormalizedFinding(
                tool="slither",
                title="issue",
                description="desc",
                severity="HIGH",
                category="reentrancy",
                file_path="file.sol",
                line_number="1",
                function="f",
                raw={"a": 1},
            )
        ]

    monkeypatch.setattr(scanner, "TOOL_MAP", {"slither": fake_tool})

    class DummyDB:
        def __init__(self):
            self.added = []
            self.commits = 0

        def commit(self):
            self.commits += 1

        def refresh(self, obj):
            pass

        def add(self, obj):
            self.added.append(obj)

    db = DummyDB()
    scanner.execute_scan(db, scan)
    assert scan.status == models.ScanStatus.SUCCESS
    assert db.added, "findings should be added"


def test_execute_scan_handles_unknown_tool(monkeypatch, tmp_path):
    project = models.Project(id="p1", name="proj", path=str(tmp_path))
    scan = models.Scan(
        id="s1", project_id="p1", target="/tmp/file.sol", tools=["missing-tool"]
    )

    class DummyDB:
        def __init__(self):
            self.added = []

        def commit(self):
            pass

        def refresh(self, obj):
            pass

        def add(self, obj):
            self.added.append(obj)

    db = DummyDB()
    scanner.execute_scan(db, scan)

    assert scan.status == models.ScanStatus.FAILED
    logs = scanner.json.loads(scan.logs)
    assert logs[0]["status"] == "unknown-tool"


def test_execute_scan_is_idempotent(monkeypatch, tmp_path):
    project = models.Project(id="p1", name="proj", path=str(tmp_path))
    scan = models.Scan(
        id="s1",
        project_id="p1",
        target="/tmp/file.sol",
        tools=["slither"],
        status=models.ScanStatus.SUCCESS,
    )

    class DummyDB:
        def __init__(self):
            self.calls = 0

        def commit(self):
            self.calls += 1

        def refresh(self, obj):
            pass

        def add(self, obj):
            pass

    db = DummyDB()
    scanner.execute_scan(db, scan)

    assert db.calls == 0, "should not mutate already completed scans"
