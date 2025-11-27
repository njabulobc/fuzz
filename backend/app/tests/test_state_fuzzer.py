import json

from app.services.state_fuzzer import (
    ContractState,
    StateAction,
    StateAwareFuzzer,
    StateInvariant,
    StateModel,
    load_model_from_file,
    run_state_fuzzer,
)


def test_state_fuzzer_finds_state_dependent_underflow():
    initial_state = ContractState(storage={"balance": 0, "unlocked": False})

    def deposit_executor(state: ContractState, params):
        amount = params["amount"]
        state.storage["balance"] = state.storage.get("balance", 0) + amount
        if amount > 10:
            state.storage["unlocked"] = True
        return state, f"balance={state.storage['balance']}"

    deposit = StateAction(
        name="deposit",
        executor=deposit_executor,
        parameter_strategy=lambda _: {"amount": 12},
    )

    def bonus_withdraw_executor(state: ContractState, params):
        amount = params["amount"]
        state.storage["balance"] = state.storage.get("balance", 0) - amount
        # missing lock reset intentionally
        return state, f"balance={state.storage['balance']}"

    bonus_withdraw = StateAction(
        name="bonus-withdraw",
        executor=bonus_withdraw_executor,
        parameter_strategy=lambda _: {"amount": 12},
        precondition=lambda st: st.storage.get("unlocked", False),
    )

    invariant = StateInvariant(
        name="no-negative-balances",
        description="Balances should not underflow when unlocked twice",
        severity="CRITICAL",
        check=lambda state: state.storage.get("balance", 0) >= 0,
    )

    model = StateModel(initial_state=initial_state, actions=[deposit, bonus_withdraw])
    fuzzer = StateAwareFuzzer(model, [invariant], max_depth=3, max_branches_per_state=3)
    result = fuzzer.fuzz()

    assert result.findings, "Fuzzer should detect the underflow after repeated bonus withdrawals"
    finding = result.findings[0]
    assert finding.state_snapshot.storage["balance"] < 0
    assert [step.name for step in finding.trace] == ["deposit", "bonus-withdraw", "bonus-withdraw"]


def test_state_fuzzer_loads_json_scenario(tmp_path):
    scenario = {
        "initial_storage": {"balance": 5, "gate": True},
        "actions": [
            {
                "name": "drain",
                "precondition": "gate == True",
                "inputs": {"amount": [10, 10]},
                "state_updates": [
                    {"target": "balance", "op": "sub", "value_from": "amount"},
                ],
            },
            {
                "name": "close-gate",
                "state_updates": [
                    {"target": "gate", "op": "set", "value": False},
                ],
            },
        ],
        "invariants": [
            {
                "name": "balance-not-negative",
                "expression": "balance >= 0",
                "description": "Balance must stay non-negative",
                "severity": "HIGH",
            }
        ],
    }

    scenario_file = tmp_path / "state-model.json"
    scenario_file.write_text(json.dumps(scenario), encoding="utf-8")

    loaded = load_model_from_file(str(scenario_file))
    assert loaded is not None, "Scenario file should be parsed"
    model, invariants = loaded

    tool_result, findings = run_state_fuzzer(
        target=str(scenario_file), model=model, invariants=invariants, max_depth=2
    )

    assert tool_result.success is True
    assert findings, "Invariant violation should be reported for over-draw"
    assert findings[0].raw["snapshot"]["balance"] < 0
