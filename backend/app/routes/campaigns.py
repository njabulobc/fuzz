from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.db.session import SessionLocal
from app.services.orchestrator import FuzzingOrchestrator

router = APIRouter(prefix="/campaigns", tags=["campaigns"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("", response_model=schemas.FuzzCampaignRead)
def create_campaign(payload: schemas.FuzzCampaignCreate, db: Session = Depends(get_db)):
    orchestrator = FuzzingOrchestrator(db)
    return orchestrator.create_campaign(payload)


@router.get("", response_model=list[schemas.FuzzCampaignRead])
def list_campaigns(db: Session = Depends(get_db)):
    return db.query(models.FuzzCampaign).order_by(models.FuzzCampaign.created_at.desc()).all()


@router.get("/{campaign_id}", response_model=schemas.FuzzCampaignDetail)
def get_campaign(campaign_id: str, db: Session = Depends(get_db)):
    campaign = db.query(models.FuzzCampaign).filter(models.FuzzCampaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return campaign


@router.post("/{campaign_id}/seeds", response_model=schemas.FuzzSeedRead)
def add_seed(campaign_id: str, payload: schemas.FuzzSeedCreate, db: Session = Depends(get_db)):
    campaign = db.query(models.FuzzCampaign).filter(models.FuzzCampaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    orchestrator = FuzzingOrchestrator(db)
    return orchestrator.add_seed(campaign, payload)


@router.post("/{campaign_id}/coverage", response_model=schemas.CoverageSignalRead)
def push_coverage(campaign_id: str, payload: schemas.CoverageSignalCreate, db: Session = Depends(get_db)):
    campaign = db.query(models.FuzzCampaign).filter(models.FuzzCampaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    orchestrator = FuzzingOrchestrator(db)
    return orchestrator.record_coverage(campaign, payload)


@router.post("/{campaign_id}/crashes", response_model=schemas.CrashReportRead)
def push_crash(campaign_id: str, payload: schemas.CrashReportCreate, db: Session = Depends(get_db)):
    campaign = db.query(models.FuzzCampaign).filter(models.FuzzCampaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    orchestrator = FuzzingOrchestrator(db)
    return orchestrator.record_crash(campaign, payload)


@router.patch("/{campaign_id}/status", response_model=schemas.FuzzCampaignRead)
def update_campaign_status(campaign_id: str, status: models.FuzzCampaignStatus, db: Session = Depends(get_db)):
    campaign = db.query(models.FuzzCampaign).filter(models.FuzzCampaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    orchestrator = FuzzingOrchestrator(db)
    return orchestrator.update_status(campaign, status)
