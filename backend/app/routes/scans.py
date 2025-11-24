from __future__ import annotations

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app import models, schemas
from app.db.session import SessionLocal
from app.workers.tasks import run_scan_task
from app.services.reporting import build_sarif, build_scan_report
from app.services.webhooks import dispatch_scan_webhook

router = APIRouter(prefix="/scans", tags=["scans"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("", response_model=schemas.ScanRead)
def start_scan(payload: schemas.ScanRequest, db: Session = Depends(get_db)):
    project = db.query(models.Project).filter(models.Project.id == payload.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    scan = models.Scan(
        project_id=payload.project_id,
        target=payload.target,
        tools=payload.tools,
        status=models.ScanStatus.PENDING,
        webhook_url=payload.webhook_url,
    )
    db.add(scan)
    db.commit()
    db.refresh(scan)
    run_scan_task.delay(scan.id)
    return scan


@router.get("", response_model=list[schemas.ScanRead])
def list_scans(db: Session = Depends(get_db)):
    return db.query(models.Scan).order_by(models.Scan.started_at.desc()).all()


@router.get("/{scan_id}", response_model=schemas.ScanDetail)
def get_scan(scan_id: str, db: Session = Depends(get_db)):
    scan = db.query(models.Scan).filter(models.Scan.id == scan_id).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    return scan


@router.get("/{scan_id}/sarif")
def export_scan_sarif(scan_id: str, db: Session = Depends(get_db)):
    scan = db.query(models.Scan).filter(models.Scan.id == scan_id).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    return JSONResponse(content=build_sarif(scan))


@router.get("/{scan_id}/report")
def export_scan_report(scan_id: str, db: Session = Depends(get_db)):
    scan = db.query(models.Scan).filter(models.Scan.id == scan_id).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    return JSONResponse(content=build_scan_report(scan))


@router.post("/{scan_id}/webhook")
def trigger_webhook(scan_id: str, db: Session = Depends(get_db)):
    scan = db.query(models.Scan).filter(models.Scan.id == scan_id).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    if not scan.webhook_url:
        raise HTTPException(status_code=400, detail="No webhook configured for scan")
    dispatch_scan_webhook(scan)
    return {"status": "sent"}