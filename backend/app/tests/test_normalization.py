from app.adapters import slither
from app.normalization.findings import NormalizedFinding


def test_slither_parse_handles_bad_json(monkeypatch):
    def fake_run_command(cmd, timeout=10):
        class Res:
            success = True
            output = "not-json"
            error = None

        return Res()

    monkeypatch.setattr(slither, "run_command", fake_run_command)
    result, findings = slither.run_slither("/tmp/file.sol")
    assert result.success is True
    assert findings == []