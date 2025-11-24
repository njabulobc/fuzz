from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app import models, schemas


class FuzzingOrchestrator:
    """Coordinates campaigns, corpora, and crash triage."""

    def __init__(self, db: Session):
        self.db = db

    def create_campaign(self, payload: schemas.FuzzCampaignCreate) -> models.FuzzCampaign:
        campaign = models.FuzzCampaign(
            name=payload.name,
            target=payload.target,
            strategy=payload.strategy,
            status=models.FuzzCampaignStatus.RUNNING,
            meta=payload.meta or {},
            coverage={},
            metrics={},
        )
        self.db.add(campaign)
        self.db.commit()
        self.db.refresh(campaign)
        return campaign

    def get_campaign(self, campaign_id: str) -> Optional[models.FuzzCampaign]:
        return self.db.query(models.FuzzCampaign).filter(models.FuzzCampaign.id == campaign_id).first()

    def add_seed(self, campaign: models.FuzzCampaign, payload: schemas.FuzzSeedCreate) -> models.FuzzSeed:
        seed = models.FuzzSeed(
            campaign_id=campaign.id,
            source=payload.source,
            corpus_path=payload.corpus_path,
            dedupe_key=payload.dedupe_key,
            coverage=payload.coverage,
        )
        self.db.add(seed)
        self.db.commit()
        self.db.refresh(seed)
        return seed

    def record_coverage(self, campaign: models.FuzzCampaign, payload: schemas.CoverageSignalCreate) -> models.CoverageSignal:
        signal = models.CoverageSignal(
            campaign_id=campaign.id,
            run_identifier=payload.run_identifier,
            covered_edges=payload.covered_edges,
            functions=payload.functions,
        )
        self.db.add(signal)
        campaign.coverage = campaign.coverage or {}
        campaign.coverage["last_run"] = payload.run_identifier
        campaign.coverage["covered_edges"] = max(
            payload.covered_edges, campaign.coverage.get("covered_edges", 0)
        )
        campaign.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(signal)
        self.db.refresh(campaign)
        return signal

    def record_crash(self, campaign: models.FuzzCampaign, payload: schemas.CrashReportCreate) -> models.CrashReport:
        existing = None
        if payload.dedupe_key:
            existing = (
                self.db.query(models.CrashReport)
                .filter(models.CrashReport.dedupe_key == payload.dedupe_key)
                .first()
            )
        status = models.CrashStatus.DUPLICATE if existing else models.CrashStatus.NEW
        crash = models.CrashReport(
            campaign_id=campaign.id,
            scan_id=payload.scan_id,
            signature=payload.signature,
            dedupe_key=payload.dedupe_key,
            status=status,
            input_reference=payload.input_reference,
            stacktrace=payload.stacktrace,
            reproducer=payload.reproducer,
            meta=payload.meta,
        )
        self.db.add(crash)
        campaign.metrics = campaign.metrics or {}
        campaign.metrics.setdefault("crashes", 0)
        if status == models.CrashStatus.NEW:
            campaign.metrics["crashes"] += 1
        self.db.commit()
        self.db.refresh(crash)
        self.db.refresh(campaign)
        return crash

    def update_status(self, campaign: models.FuzzCampaign, status: models.FuzzCampaignStatus) -> models.FuzzCampaign:
        campaign.status = status
        campaign.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(campaign)
        return campaign
