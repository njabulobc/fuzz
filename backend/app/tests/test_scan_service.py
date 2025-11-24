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

    def fake_tool(target):
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