from pathlib import Path

from app.adapters import slither
from app.config import ToolSettings
from app.normalization.findings import NormalizedFinding


def test_slither_parse_handles_bad_json(monkeypatch, tmp_path):
    def fake_run_command(cmd, timeout=10, env=None, workdir=None, log_dir=None, max_runtime=None):  # noqa: ARG001
        class Res:
            success = True
            output = "not-json"
            error = None
            return_code = 0
            command = cmd
            stdout_path = str(tmp_path / "stdout.log")
            stderr_path = str(tmp_path / "stderr.log")
            environment = env
            started_at = None
            finished_at = None
            duration_seconds = None
            parsing_error = None
            failure_reason = None
            artifacts_path = str(tmp_path)
            tool_version = "1.0.0"

        return Res()

    monkeypatch.setattr(slither, "run_command", fake_run_command)
    result, findings = slither.run_slither(
        "/tmp/file.sol",
        config=ToolSettings(),
        workdir=tmp_path,
        log_dir=tmp_path,
        env={},
    )
    assert result.success is True
    assert result.parsing_error is not None
    assert findings == []
