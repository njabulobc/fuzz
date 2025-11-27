from __future__ import annotations

import json

from app.adapters import echidna, manticore
from app.adapters.base import ToolResult


def test_echidna_parses_metrics_and_properties(monkeypatch):
    sample_output = json.dumps(
        {
            "coverage": {"overall": 72.5},
            "testBudget": 30,
            "errors": [
                {
                    "test": "test_property_fails",
                    "message": "invariant broken",
                    "property": "invariant",
                    "contract": "Foo.sol",
                    "line": 12,
                }
            ],
        }
    )

    def fake_run_command(cmd, timeout=600):  # noqa: ARG001 - test stub
        return ToolResult(success=True, output=sample_output)

    monkeypatch.setattr(echidna, "run_command", fake_run_command)
    result, findings = echidna.run_echidna("Foo.sol")

    assert result.coverage == 72.5
    assert result.budget_seconds == 30
    assert result.properties == ["invariant"]
    assert findings[0].function == "invariant"


def test_manticore_parses_json_findings(monkeypatch):
    output = json.dumps(
        {
            "issues": [
                {
                    "title": "Overflow detected",
                    "message": "unchecked math",
                    "severity": "HIGH",
                    "line": 8,
                    "file": "Bar.sol",
                    "property": "unchecked_add",
                }
            ],
            "coverage": 81.2,
            "budget": 15,
        }
    )

    def fake_run_command(cmd, timeout=600):  # noqa: ARG001 - test stub
        return ToolResult(success=True, output=output)

    monkeypatch.setattr(manticore, "run_command", fake_run_command)
    result, findings = manticore.run_manticore("Bar.sol")

    assert result.coverage == 81.2
    assert result.budget_seconds == 15
    assert result.properties == ["unchecked_add"]
    assert findings[0].title == "Overflow detected"
