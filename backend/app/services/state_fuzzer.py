from __future__ import annotations

import ast
import hashlib
import json
import random
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from app.adapters.base import ToolResult
from app.normalization.findings import NormalizedFinding

StateDict = Dict[str, Any]


@dataclass
class ContractState:
    """Minimal representation of an on-chain contract state."""

    storage: StateDict = field(default_factory=dict)
    balances: StateDict = field(default_factory=dict)
    metadata: StateDict = field(default_factory=dict)

    def clone(self) -> "ContractState":
        return ContractState(
            storage=dict(self.storage),
            balances=dict(self.balances),
            metadata=dict(self.metadata),
        )


@dataclass
class ActionResult:
    name: str
    parameters: StateDict
    resulting_state: ContractState
    note: Optional[str] = None


@dataclass
class StateFinding:
    invariant: str
    description: str
    trace: List[ActionResult]
    state_snapshot: ContractState
    severity: str = "HIGH"

    def to_normalized(self) -> NormalizedFinding:
        return NormalizedFinding(
            tool="state-fuzzer",
            title=f"Invariant violated: {self.invariant}",
            description=self.description,
            severity=self.severity,
            category="state-invariant",
            raw={
                "trace": [
                    {
                        "action": step.name,
                        "parameters": step.parameters,
                        "note": step.note,
                        "state": step.resulting_state.storage,
                    }
                    for step in self.trace
                ],
                "snapshot": self.state_snapshot.storage,
            },
        )


@dataclass
class StateInvariant:
    name: str
    check: Callable[[ContractState], bool]
    description: str
    severity: str = "HIGH"


@dataclass
class StateAction:
    name: str
    executor: Callable[[ContractState, StateDict], Tuple[ContractState, Optional[str]]]
    parameter_strategy: Callable[[ContractState], StateDict] = lambda state: {}
    precondition: Callable[[ContractState], bool] = lambda state: True

    def run(self, state: ContractState) -> Optional[ActionResult]:
        if not self.precondition(state):
            return None
        params = self.parameter_strategy(state)
        new_state, note = self.executor(state.clone(), params)
        return ActionResult(
            name=self.name,
            parameters=params,
            resulting_state=new_state,
            note=note,
        )


@dataclass
class StateModel:
    initial_state: ContractState
    actions: Sequence[StateAction]

    def available_actions(self, state: ContractState) -> List[StateAction]:
        return [action for action in self.actions if action.precondition(state)]


@dataclass
class FuzzResult:
    findings: List[StateFinding]
    explored_traces: int
    unique_states: int
    coverage: List[str]


class StateAwareFuzzer:
    def __init__(
        self,
        model: StateModel,
        invariants: Sequence[StateInvariant],
        max_depth: int = 4,
        max_branches_per_state: int = 6,
    ) -> None:
        self.model = model
        self.invariants = list(invariants)
        self.max_depth = max_depth
        self.max_branches_per_state = max_branches_per_state
        self.visited_signatures: set[str] = set()
        self.findings: List[StateFinding] = []
        self.coverage: List[str] = []
        self.explored_traces = 0

    def fuzz(self) -> FuzzResult:
        stack: List[Tuple[int, ContractState, List[ActionResult]]] = [
            (0, self.model.initial_state.clone(), []),
        ]
        while stack:
            depth, state, trace = stack.pop()
            signature = self._state_signature(state)
            if signature not in self.visited_signatures:
                self.visited_signatures.add(signature)
                self.coverage.append(signature)

            violation = self._check_invariants(state, trace)
            if violation:
                self.findings.append(violation)
                continue

            if depth >= self.max_depth:
                continue

            actions = self.model.available_actions(state)
            random.shuffle(actions)
            for action in actions[: self.max_branches_per_state]:
                result = action.run(state)
                if not result:
                    continue
                next_trace = trace + [result]
                stack.append((depth + 1, result.resulting_state, next_trace))
                self.explored_traces += 1

        return FuzzResult(
            findings=self.findings,
            explored_traces=self.explored_traces,
            unique_states=len(self.visited_signatures),
            coverage=self.coverage,
        )

    def _check_invariants(
        self, state: ContractState, trace: List[ActionResult]
    ) -> Optional[StateFinding]:
        for invariant in self.invariants:
            if not invariant.check(state):
                return StateFinding(
                    invariant=invariant.name,
                    description=invariant.description,
                    trace=trace,
                    state_snapshot=state.clone(),
                    severity=invariant.severity,
                )
        return None

    @staticmethod
    def _state_signature(state: ContractState) -> str:
        serializable = json.dumps(
            {"storage": state.storage, "balances": state.balances},
            sort_keys=True,
        )
        return hashlib.sha1(serializable.encode("utf-8")).hexdigest()


def _safe_eval(expression: str, variables: Dict[str, Any]) -> bool:
    node = ast.parse(expression, mode="eval").body
    return _eval_ast(node, variables)


def _eval_ast(node: ast.AST, variables: Dict[str, Any]) -> Any:
    if isinstance(node, ast.Name):
        return variables.get(node.id)
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub)):
        left = _eval_ast(node.left, variables)
        right = _eval_ast(node.right, variables)
        return left + right if isinstance(node.op, ast.Add) else left - right
    if isinstance(node, ast.BoolOp):
        values = [_eval_ast(v, variables) for v in node.values]
        if isinstance(node.op, ast.And):
            return all(values)
        if isinstance(node.op, ast.Or):
            return any(values)
    if isinstance(node, ast.Compare):
        left = _eval_ast(node.left, variables)
        for op_node, comparator in zip(node.ops, node.comparators):
            right = _eval_ast(comparator, variables)
            if isinstance(op_node, ast.Gt) and not left > right:
                return False
            if isinstance(op_node, ast.Lt) and not left < right:
                return False
            if isinstance(op_node, ast.GtE) and not left >= right:
                return False
            if isinstance(op_node, ast.LtE) and not left <= right:
                return False
            if isinstance(op_node, ast.Eq) and not left == right:
                return False
            if isinstance(op_node, ast.NotEq) and not left != right:
                return False
            left = right
        return True
    raise ValueError("Unsupported expression for invariant evaluation")


def load_model_from_file(path: str) -> Optional[tuple[StateModel, List[StateInvariant]]]:
    try:
        with open(path, "r", encoding="utf-8") as fp:
            data = json.load(fp)
    except FileNotFoundError:
        return None

    initial_state = ContractState(
        storage=data.get("initial_storage", {}),
        balances=data.get("initial_balances", {}),
        metadata={"source": path},
    )

    actions: List[StateAction] = []
    for action_def in data.get("actions", []):
        updates = action_def.get("state_updates", [])
        inputs = action_def.get("inputs", {})
        precondition_expr = action_def.get("precondition")

        def strategy(state: ContractState, template=inputs) -> StateDict:
            params: StateDict = {}
            for key, spec in template.items():
                if isinstance(spec, list) and len(spec) == 2 and all(
                    isinstance(v, (int, float)) for v in spec
                ):
                    params[key] = random.randint(int(spec[0]), int(spec[1]))
                else:
                    params[key] = spec
            return params

        def executor(
            state: ContractState, params: StateDict, updates=updates
        ) -> Tuple[ContractState, Optional[str]]:
            new_state = state.clone()
            notes: List[str] = []
            for update in updates:
                target = update.get("target")
                op = update.get("op", "set")
                condition_expr = update.get("condition")
                if condition_expr:
                    variables = {**new_state.storage, **params}
                    if not _safe_eval(condition_expr, variables):
                        continue
                value = update.get("value")
                if "value_from" in update:
                    value = params.get(update["value_from"])
                current_value = new_state.storage.get(target, 0)
                if op == "add":
                    new_state.storage[target] = current_value + value
                elif op == "sub":
                    new_state.storage[target] = current_value - value
                else:
                    new_state.storage[target] = value
                notes.append(f"{target}={new_state.storage[target]}")
            return new_state, ", ".join(notes) if notes else None

        def precondition(state: ContractState, expr=precondition_expr) -> bool:
            if not expr:
                return True
            variables = {**state.storage, **state.balances}
            return bool(_safe_eval(expr, variables))

        actions.append(
            StateAction(
                name=action_def.get("name", "action"),
                executor=executor,
                parameter_strategy=strategy,
                precondition=precondition,
            )
        )

    invariants: List[StateInvariant] = []
    for invariant_def in data.get("invariants", []):
        expr = invariant_def.get("expression")
        description = invariant_def.get("description", expr or "Invariant failed")
        severity = invariant_def.get("severity", "HIGH").upper()

        def checker(state: ContractState, expression=expr) -> bool:
            variables = {**state.storage, **state.balances}
            return bool(_safe_eval(expression, variables))

        invariants.append(
            StateInvariant(
                name=invariant_def.get("name", "invariant"),
                check=checker,
                description=description,
                severity=severity,
            )
        )

    return StateModel(initial_state=initial_state, actions=actions), invariants


def run_state_fuzzer(
    target: str,
    *,
    model: Optional[StateModel] = None,
    invariants: Optional[Sequence[StateInvariant]] = None,
    max_depth: int | None = None,
) -> tuple[ToolResult, List[NormalizedFinding]]:
    if model is None or invariants is None:
        loaded = load_model_from_file(target)
        if loaded is None:
            return ToolResult(
                success=False, output="", error=f"state model not found at {target}"
            ), []
        model, invariants = loaded

    fuzzer = StateAwareFuzzer(
        model=model, invariants=list(invariants), max_depth=max_depth or 4
    )
    result = fuzzer.fuzz()

    normalized = [finding.to_normalized() for finding in result.findings]
    output = {
        "explored_traces": result.explored_traces,
        "unique_states": result.unique_states,
        "coverage": result.coverage,
        "findings": len(normalized),
    }
    return ToolResult(success=True, output=json.dumps(output), error=None), normalized
