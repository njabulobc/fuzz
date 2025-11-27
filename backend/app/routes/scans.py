from __future__ import annotations

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.db.session import SessionLocal
from app.workers.tasks import run_scan_task

router = APIRouter(prefix="/scans", tags=["scans"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _create_scan(db: Session, project_id: str, target: str, tools: list[str]):
    scan = models.Scan(
        project_id=project_id,
        target=target,
        tools=tools,
        status=models.ScanStatus.PENDING,
    )
    db.add(scan)
    db.commit()
    db.refresh(scan)
    run_scan_task.delay(scan.id)
    return scan


@router.post("", response_model=schemas.ScanRead)
def start_scan(payload: schemas.ScanRequest, db: Session = Depends(get_db)):
    project = db.query(models.Project).filter(models.Project.id == payload.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    scan = _create_scan(db, payload.project_id, payload.target, payload.tools)
    return scan


@router.post("/quick", response_model=schemas.QuickScanResponse)
def quick_scan(payload: schemas.QuickScanRequest, db: Session = Depends(get_db)):
    project = db.query(models.Project).filter(models.Project.name == payload.project.name).first()

    if not project:
        project = models.Project(
            name=payload.project.name,
            path=payload.project.path,
            meta=payload.project.meta,
        )
        db.add(project)
        db.commit()
        db.refresh(project)
    else:
        if project.path != payload.project.path or project.meta != payload.project.meta:
            project.path = payload.project.path
            project.meta = payload.project.meta
            db.commit()
            db.refresh(project)

    scan = _create_scan(db, project.id, payload.target, payload.tools)

    return schemas.QuickScanResponse(project_id=project.id, scan_id=scan.id)


@router.get("", response_model=list[schemas.ScanRead])
def list_scans(db: Session = Depends(get_db)):
    return db.query(models.Scan).order_by(models.Scan.started_at.desc()).all()


@router.get("/{scan_id}", response_model=schemas.ScanDetail)
def get_scan(scan_id: str, db: Session = Depends(get_db)):
    scan = db.query(models.Scan).filter(models.Scan.id == scan_id).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    return scan