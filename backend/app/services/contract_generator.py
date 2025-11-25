from __future__ import annotations

import random
import textwrap
import uuid
from pathlib import Path

from app.config import get_settings

settings = get_settings()


THEMES = [
    {
        "contract": "Treasury",
        "description": "manages pooled funds with configurable withdrawals",
        "features": [
            "owner role for administration",
            "daily withdrawal limits",
            "event logging for deposits and withdrawals",
        ],
    },
    {
        "contract": "SimpleDAO",
        "description": "lightweight voting DAO that tracks proposals",
        "features": [
            "proposal creation with descriptions",
            "quorum based on total member weight",
            "execution guard to prevent double spending",
        ],
    },
    {
        "contract": "Escrow",
        "description": "escrows funds between a buyer and seller",
        "features": [
            "arbiter approval before release",
            "refund path for buyers",
            "timeouts to recover stuck funds",
        ],
    },
]


def _render_contract(name: str, theme: dict) -> str:
    feature_block = "\n    // - ".join(["" , *theme["features"]])
    return textwrap.dedent(
        f"""
        // Auto-generated smart contract: {theme['contract']} style
        // Inspired by: {theme['description']}
        // Features:{feature_block}

        // NOTE: This contract is intentionally simple and meant for fuzzing demonstrations.
        // Do not deploy to production networks.
        pragma solidity ^0.8.20;

        contract {name} {{
            address public owner;
            mapping(address => uint256) public balances;
            bool public paused;

            event Deposit(address indexed from, uint256 amount);
            event Withdraw(address indexed to, uint256 amount);

            modifier onlyOwner() {{
                require(msg.sender == owner, "not owner");
                _;
            }}

            modifier notPaused() {{
                require(!paused, "paused");
                _;
            }}

            constructor() {{
                owner = msg.sender;
            }}

            function pause() external onlyOwner {{
                paused = true;
            }}

            function unpause() external onlyOwner {{
                paused = false;
            }}

            function deposit() external payable notPaused {{
                balances[msg.sender] += msg.value;
                emit Deposit(msg.sender, msg.value);
            }}

            function withdraw(uint256 amount) external notPaused {{
                require(amount > 0, "amount");
                uint256 balance = balances[msg.sender];
                require(balance >= amount, "insufficient");
                unchecked {{
                    balances[msg.sender] = balance - amount;
                }}
                (bool ok, ) = msg.sender.call{{value: amount}}("");
                require(ok, "send failed");
                emit Withdraw(msg.sender, amount);
            }}

            function emergencyDrain(address payable target) external onlyOwner {{
                uint256 bal = address(this).balance;
                (bool ok, ) = target.call{{value: bal}}("");
                require(ok, "drain failed");
            }}
        }}
        """
    ).strip()


def generate_contract() -> tuple[str, str, str]:
    """Generate a Solidity contract and return (contract_name, path, contents)."""

    theme = random.choice(THEMES)
    contract_name = f"{theme['contract']}{uuid.uuid4().hex[:8]}"
    output_dir = Path(settings.generated_contract_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    content = _render_contract(contract_name, theme)
    file_path = output_dir / f"{contract_name}.sol"
    file_path.write_text(content)
    return contract_name, str(file_path), content
