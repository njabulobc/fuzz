from __future__ import annotations

import time
from pathlib import Path
from typing import Dict, List, Optional

import requests
import typer

API_URL = "http://localhost:8000/api"
DEFAULT_TOOLS = ["slither", "mythril", "echidna"]

app = typer.Typer(help="Smart contract scanner CLI")


def parse_tools_option(tools: Optional[str]) -> List[str]:
    if not tools:
        return DEFAULT_TOOLS
    parsed = [tool.strip() for tool in tools.split(",") if tool.strip()]
    return parsed or DEFAULT_TOOLS


def validate_response(resp: requests.Response, expected_status: int = 200):
    try:
        data = resp.json()
    except ValueError:
        typer.echo(f"Unexpected response (status {resp.status_code}): {resp.text}")
        raise typer.Exit(code=1)

    if resp.status_code != expected_status:
        detail = data.get("detail") if isinstance(data, dict) else data
        typer.echo(f"Request failed with status {resp.status_code}: {detail}")
        raise typer.Exit(code=1)
    return data


def get_or_create_project(name: str, path: str) -> Dict:
    projects = validate_response(requests.get(f"{API_URL}/projects"))
    for project in projects:
        if project.get("name") == name:
            return project

    payload = {"name": name, "path": path}
    return validate_response(requests.post(f"{API_URL}/projects", json=payload), 200)


def start_scan(project_id: str, target: str, tools: List[str]) -> Dict:
    payload = {"project_id": project_id, "target": target, "tools": tools}
    return validate_response(requests.post(f"{API_URL}/scans", json=payload), 200)


def wait_for_scan(scan_id: str, poll_interval: float = 2.0) -> Dict:
    while True:
        scan = validate_response(requests.get(f"{API_URL}/scans/{scan_id}"))
        status = scan.get("status")
        if status in {"SUCCESS", "FAILED"}:
            return scan
        time.sleep(poll_interval)


def summarize_findings(scan_id: str) -> str:
    findings = validate_response(
        requests.get(f"{API_URL}/findings", params={"scan_id": scan_id})
    )
    if not findings:
        return "No findings reported."

    counts: Dict[str, int] = {}
    for finding in findings:
        severity = finding.get("severity", "unknown").upper()
        counts[severity] = counts.get(severity, 0) + 1

    summary_lines = ["Findings summary:"]
    for severity, count in sorted(counts.items(), key=lambda item: item[0]):
        summary_lines.append(f"- {severity}: {count}")

    first_titles = [f["title"] for f in findings[:3] if f.get("title")]
    if first_titles:
        summary_lines.append("Sample findings: " + "; ".join(first_titles))

    return "\n".join(summary_lines)


def generate_contract(path: Path, contract_name: str) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    contract_path = path / f"{contract_name}.sol"
    contract_source = f"""// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract {contract_name} {{
    address public owner;
    mapping(address => uint256) private balances;

    constructor() {{
        owner = msg.sender;
        balances[msg.sender] = 1 ether;
    }}

    function withdraw(uint256 amount) public {{
        require(balances[msg.sender] >= amount, "insufficient funds");
        balances[msg.sender] -= amount;
        (bool ok, ) = msg.sender.call{value: amount}("");
        require(ok, "transfer failed");
    }}

    function deposit() public payable {{
        balances[msg.sender] += msg.value;
    }}
}}
"""
    contract_path.write_text(contract_source)
    return contract_path


@app.command()
def create_project(name: str, path: str):
    resp = requests.post(f"{API_URL}/projects", json={"name": name, "path": path})
    typer.echo(validate_response(resp))


@app.command()
def list_projects():
    resp = requests.get(f"{API_URL}/projects")
    typer.echo(validate_response(resp))


@app.command()
def run_scan(project_id: str, target: str, tools: Optional[str] = typer.Option(None)):
    tools_list = parse_tools_option(tools)
    resp = requests.post(
        f"{API_URL}/scans",
        json={"project_id": project_id, "target": target, "tools": tools_list},
    )
    typer.echo(validate_response(resp))


@app.command()
def scans():
    resp = requests.get(f"{API_URL}/scans")
    typer.echo(validate_response(resp))


@app.command()
def findings(scan_id: Optional[str] = None):
    params = {"scan_id": scan_id} if scan_id else {}
    resp = requests.get(f"{API_URL}/findings", params=params)
    typer.echo(validate_response(resp))


@app.command()
def automate_contract(
    project_name: str = typer.Argument(..., help="Project name to create or reuse"),
    output_dir: Path = typer.Option(
        Path("./generated-contracts"), "--output-dir", "-o", help="Where to write the contract"
    ),
    contract_name: str = typer.Option(
        "AutoContract", "--contract-name", "-c", help="Generated Solidity contract name"
    ),
    tools: Optional[str] = typer.Option(
        None, help="Comma-separated tools list (defaults to slither,mythril,echidna)"
    ),
    wait: bool = typer.Option(
        False, help="Wait for scan completion and show a summarized set of findings"
    ),
    poll_interval: float = typer.Option(2.0, help="Seconds between status checks when waiting"),
):
    contract_path = generate_contract(output_dir, contract_name)
    project = get_or_create_project(project_name, str(output_dir))
    scan = start_scan(project["id"], str(contract_path), parse_tools_option(tools))
    typer.echo(
        f"Started scan {scan['id']} for project {project_name} targeting {contract_path}"
    )

    if not wait:
        return

    typer.echo("Waiting for scan to finish...")
    completed_scan = wait_for_scan(scan["id"], poll_interval)
    typer.echo(f"Scan completed with status {completed_scan['status']}")
    typer.echo(summarize_findings(scan["id"]))


if __name__ == "__main__":
    app()
