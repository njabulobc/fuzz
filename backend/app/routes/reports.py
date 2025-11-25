from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app import models
from app.db.session import SessionLocal
from app.services import reporting

router = APIRouter(prefix="/reports", tags=["reports"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _get_scan_or_404(scan_id: str, db: Session) -> models.Scan:
    scan = db.query(models.Scan).filter(models.Scan.id == scan_id).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    return scan


@router.get("/{scan_id}/sarif")
def sarif_report(scan_id: str, db: Session = Depends(get_db)):
    scan = _get_scan_or_404(scan_id, db)
    return reporting.generate_sarif(scan)


@router.get("/{scan_id}/json")
def json_report(scan_id: str, db: Session = Depends(get_db)):
    scan = _get_scan_or_404(scan_id, db)
    return reporting.generate_json_report(scan)


@router.post("/{scan_id}/webhook")
def webhook(scan_id: str, payload: dict, db: Session = Depends(get_db)):
    scan = _get_scan_or_404(scan_id, db)
    url = payload.get("url")
    if not url:
        raise HTTPException(status_code=400, detail="url is required")
    status_code, text = reporting.dispatch_webhook(url, reporting.generate_json_report(scan))
    return {"status_code": status_code, "response": text}

