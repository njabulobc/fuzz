from __future__ import annotations

from typing import List, Sequence

from app.normalization.findings import NormalizedFinding
from app.services.state_fuzzer import (
    StateInvariant,
    StateModel,
    run_state_fuzzer as run_state_fuzzer_service,
)
from app.adapters.base import ToolResult


def run_state_fuzzer(
    target: str,
    *,
    model: StateModel | None = None,
    invariants: Sequence[StateInvariant] | None = None,
) -> tuple[ToolResult, List[NormalizedFinding]]:
    """Bridge function to execute the in-process state-aware fuzzer.

    The adapter mirrors the signature of external tool runners so the scanner
    orchestration layer can schedule the fuzzer just like other tools.
    """

    return run_state_fuzzer_service(target, model=model, invariants=invariants)
