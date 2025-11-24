from __future__ import annotations

import typer
import requests
from typing import Optional

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
