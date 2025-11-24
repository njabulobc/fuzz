from app import models
from app.services import scanner
from app.adapters.base import ToolResult


def test_execute_scan_collects_findings(monkeypatch, tmp_path):
    project = models.Project(id="p1", name="proj", path=str(tmp_path))
    scan = models.Scan(id="s1", project_id="p1", target="/tmp/file.sol", tools=["slither"])

    def fake_tool(target, timeout=None):
        return ToolResult(success=True, output="ok", error=None, exit_code=0, runtime_seconds=0.1), [
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

        def flush(self):
            pass

    db = DummyDB()
    scanner.execute_scan(db, scan)
    assert scan.status == models.ScanStatus.SUCCESS
    assert db.added, "findings should be added"