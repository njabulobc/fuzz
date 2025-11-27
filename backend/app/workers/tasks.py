from __future__ import annotations

from datetime import datetime
from sqlalchemy.orm import Session

from app.workers.celery_app import celery_app
from app.db.session import SessionLocal
from app import models
from app.services.scanner import execute_scan


@celery_app.task(bind=True)
def run_scan_task(self, scan_id: str):
    db: Session = SessionLocal()
    try:
        scan = db.query(models.Scan).filter(models.Scan.id == scan_id).first()
        if not scan:
            return
        try:
            execute_scan(db, scan)
        except Exception as exc:  # pragma: no cover - safety net
            scan.status = models.ScanStatus.FAILED
            scan.finished_at = datetime.utcnow()
            scan.logs = f"error: {exc}"
            db.commit()
    finally:
        db.close()
