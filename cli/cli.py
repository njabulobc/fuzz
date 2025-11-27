from __future__ import annotations

import json
from typing import Optional

import requests
import typer

API_URL = "http://localhost:8000/api"

app = typer.Typer(help="Smart contract scanner CLI")


@app.command()
def create_project(name: str, path: str):
    resp = requests.post(f"{API_URL}/projects", json={"name": name, "path": path})
    typer.echo(resp.json())


@app.command()
def list_projects():
    resp = requests.get(f"{API_URL}/projects")
    typer.echo(resp.json())


@app.command()
def run_scan(project_id: str, target: str, tools: Optional[str] = typer.Option(None)):
    tools_list = tools.split(",") if tools else ["slither", "mythril", "echidna"]
    resp = requests.post(
        f"{API_URL}/scans",
        json={"project_id": project_id, "target": target, "tools": tools_list},
    )
    typer.echo(resp.json())


@app.command()
def quick_scan(
    name: str,
    path: str,
    target: str,
    meta: Optional[str] = typer.Option(None, help="Optional JSON metadata for the project"),
    tools: Optional[str] = typer.Option(None, help="Comma-separated list of tools to run"),
):
    tools_list = tools.split(",") if tools else ["slither", "mythril", "echidna"]
    meta_payload = None

    if meta:
        try:
            meta_payload = json.loads(meta)
        except json.JSONDecodeError as exc:
            typer.echo(f"Invalid meta JSON: {exc}")
            raise typer.Exit(code=1)

    payload = {
        "project": {"name": name, "path": path, "meta": meta_payload},
        "target": target,
        "tools": tools_list,
    }
    resp = requests.post(f"{API_URL}/scans/quick", json=payload)
    typer.echo(resp.json())


@app.command()
def scans():
    resp = requests.get(f"{API_URL}/scans")
    typer.echo(resp.json())


@app.command()
def findings(scan_id: Optional[str] = None):
    params = {"scan_id": scan_id} if scan_id else {}
    resp = requests.get(f"{API_URL}/findings", params=params)
    typer.echo(resp.json())


if __name__ == "__main__":
    app()
