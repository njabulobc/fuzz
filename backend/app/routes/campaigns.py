from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.db.session import SessionLocal
from app.services.orchestrator import FuzzOrchestrator

router = APIRouter(prefix="/campaigns", tags=["campaigns"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("", response_model=list[schemas.FuzzCampaignRead])
def list_campaigns(db: Session = Depends(get_db)):
    return db.query(models.FuzzCampaign).order_by(models.FuzzCampaign.created_at.desc()).all()


@router.get("/{campaign_id}", response_model=schemas.FuzzCampaignDetail)
def get_campaign(campaign_id: str, db: Session = Depends(get_db)):
    campaign = (
        db.query(models.FuzzCampaign)
        .filter(models.FuzzCampaign.id == campaign_id)
        .first()
    )
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return campaign


@router.post("/{scan_id}", response_model=schemas.FuzzCampaignDetail)
def bootstrap_campaign(scan_id: str, db: Session = Depends(get_db)):
    scan = db.query(models.Scan).filter(models.Scan.id == scan_id).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    orchestrator = FuzzOrchestrator(db)
    campaign = orchestrator.create_or_resume_campaign(scan)
    return campaign

