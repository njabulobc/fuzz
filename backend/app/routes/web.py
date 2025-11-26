from __future__ import annotations

import json
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import models
from app.db.session import SessionLocal
from app.workers.tasks import run_scan_task

router = APIRouter(tags=["web"])

templates = Jinja2Templates(directory="app/templates")

TOOLBOX = ["slither", "mythril", "echidna"]
SAMPLE_CONTRACT = """// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract SampleToken {
    string public name = "SampleToken";
    string public symbol = "SMP";
    uint8 public decimals = 18;
    uint256 public totalSupply = 1_000_000 * 10 ** uint256(decimals);

    mapping(address => uint256) public balanceOf;
    mapping(address => mapping(address => uint256)) public allowance;

    event Transfer(address indexed from, address indexed to, uint256 value);
    event Approval(address indexed owner, address indexed spender, uint256 value);

    constructor() {
        balanceOf[msg.sender] = totalSupply;
    }

    function transfer(address to, uint256 value) public returns (bool) {
        require(balanceOf[msg.sender] >= value, "Insufficient balance");
        _transfer(msg.sender, to, value);
        return true;
    }

    function approve(address spender, uint256 value) public returns (bool) {
        allowance[msg.sender][spender] = value;
        emit Approval(msg.sender, spender, value);
        return true;
    }

    function transferFrom(address from, address to, uint256 value) public returns (bool) {
        require(balanceOf[from] >= value, "Insufficient balance");
        require(allowance[from][msg.sender] >= value, "Allowance too low");
        allowance[from][msg.sender] -= value;
        _transfer(from, to, value);
        return true;
    }

    function _transfer(address from, address to, uint256 value) internal {
        require(to != address(0), "Cannot transfer to zero address");
        balanceOf[from] -= value;
        balanceOf[to] += value;
        emit Transfer(from, to, value);
    }
}
"""


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _redirect_with_message(request: Request, message: str | None = None, tone: str = "info", selected_scan_id: str | None = None):
    base_url = request.url_for("dashboard")
    params: dict[str, str] = {}
    if message:
        params["alert"] = message
        params["tone"] = tone
    if selected_scan_id:
        params["selected_scan_id"] = selected_scan_id
    query = f"?{urlencode(params)}" if params else ""
    return RedirectResponse(f"{base_url}{query}", status_code=303)


@router.get("/", response_class=HTMLResponse, name="dashboard")
def dashboard(
    request: Request,
    selected_scan_id: str | None = None,
    severity: str | None = None,
    tool: str | None = None,
    db: Session = Depends(get_db),
):
    projects = db.query(models.Project).order_by(models.Project.created_at.desc()).all()
    scans = db.query(models.Scan).order_by(models.Scan.started_at.desc()).all()

    selected_scan = None
    findings: list[models.Finding] = []

    if not selected_scan_id and scans:
        selected_scan_id = scans[0].id

    if selected_scan_id:
        selected_scan = db.query(models.Scan).filter(models.Scan.id == selected_scan_id).first()
        if selected_scan:
            query = db.query(models.Finding).filter(models.Finding.scan_id == selected_scan_id)
            if severity:
                query = query.filter(models.Finding.severity == severity)
            if tool:
                query = query.filter(models.Finding.tool == tool)
            findings = query.order_by(models.Finding.severity.desc()).all()

    context = {
        "request": request,
        "projects": projects,
        "scans": scans,
        "selected_scan": selected_scan,
        "selected_scan_id": selected_scan_id,
        "findings": findings,
        "severity_filter": severity or "",
        "tool_filter": tool or "",
        "toolbox": TOOLBOX,
        "sample_contract": SAMPLE_CONTRACT,
        "alert_message": request.query_params.get("alert"),
        "alert_tone": request.query_params.get("tone", "info"),
        "default_target": "contracts/SampleToken.sol",
    }
    return templates.TemplateResponse("dashboard.html", context)


@router.post("/projects", response_class=HTMLResponse, name="create_project_web")
def create_project(
    request: Request,
    name: str = Form(...),
    path: str = Form(...),
    meta: str = Form(""),
    db: Session = Depends(get_db),
):
    meta_payload = None
    if meta.strip():
        try:
            meta_payload = json.loads(meta)
        except json.JSONDecodeError:
            return _redirect_with_message(request, "Meta must be valid JSON.", "error")

    project = models.Project(name=name, path=path, meta=meta_payload)
    try:
        db.add(project)
        db.commit()
    except IntegrityError:
        db.rollback()
        return _redirect_with_message(request, "Project name must be unique.", "error")

    return _redirect_with_message(request, "Project added successfully.", "success")


@router.post("/scans", response_class=HTMLResponse, name="start_scan_web")
def start_scan(
    request: Request,
    project_id: str = Form(...),
    target: str = Form(...),
    tools: list[str] = Form(default=[]),
    db: Session = Depends(get_db),
):
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        return _redirect_with_message(request, "Project not found. Please add one first.", "error")

    selected_tools = tools or TOOLBOX
    scan = models.Scan(
        project_id=project_id,
        target=target,
        tools=selected_tools,
        status=models.ScanStatus.PENDING,
    )
    db.add(scan)
    db.commit()
    db.refresh(scan)

    run_scan_task.delay(scan.id)
    return _redirect_with_message(request, "Scan started. Refreshing status soon.", "success", scan.id)


@router.get("/sample-contract", response_class=Response, name="download_sample_contract")
def download_sample_contract():
    headers = {"Content-Disposition": "attachment; filename=SampleToken.sol"}
    return Response(content=SAMPLE_CONTRACT, media_type="text/plain", headers=headers)
