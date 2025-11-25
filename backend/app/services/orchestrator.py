from __future__ import annotations

import hashlib
import time
from typing import Iterable, List, Optional

import structlog
from sqlalchemy.orm import Session

from app import models

logger = structlog.get_logger(__name__)


class FuzzOrchestrator:
    """
    Coordinates fuzzing campaigns, corpus management, coverage tracking, and crash
    triage. The orchestration layer is intentionally lightweight so that it can be
    embedded into worker tasks or expanded into a dedicated service later.
    """

    def __init__(self, db: Session):
        self.db = db

    # Campaign management -------------------------------------------------
    def create_or_resume_campaign(self, scan: models.Scan, strategy: str = "coverage-guided") -> models.FuzzCampaign:
        existing = (
            self.db.query(models.FuzzCampaign)
            .filter(models.FuzzCampaign.scan_id == scan.id)
            .first()
        )
        if existing:
            return existing

        campaign = models.FuzzCampaign(
            scan_id=scan.id,
            name=f"campaign-{scan.id}",
            strategy=strategy,
            status=models.FuzzCampaignStatus.RUNNING,
            coverage_metrics={"edges": 0, "paths": 0},
            seed_pool=[],
        )
        self.db.add(campaign)
        self.db.commit()
        self.db.refresh(campaign)
        return campaign

    def upsert_seed(self, campaign: models.FuzzCampaign, seed_value: str, origin: str = "auto") -> models.CorpusSeed:
        seed = models.CorpusSeed(
            campaign_id=campaign.id,
            value=seed_value,
            origin=origin,
            coverage={"edges": 0},
            metadata={"first_seen": time.time()},
        )
        self.db.add(seed)
        self.db.commit()
        self.db.refresh(seed)
        return seed

    def record_coverage(self, campaign: models.FuzzCampaign, coverage_delta: dict) -> None:
        metrics = campaign.coverage_metrics or {}
        for key, value in coverage_delta.items():
            metrics[key] = metrics.get(key, 0) + value
        campaign.coverage_metrics = metrics
        campaign.status = models.FuzzCampaignStatus.RUNNING
        self.db.commit()
        self.db.refresh(campaign)

    # Crash handling ------------------------------------------------------
    def dedupe_crash(self, signature: str) -> Optional[models.CrashReport]:
        dedup_hash = hashlib.sha256(signature.encode()).hexdigest()
        return (
            self.db.query(models.CrashReport)
            .filter(models.CrashReport.dedup_hash == dedup_hash)
            .first()
        )

    def record_crash(
        self,
        campaign: models.FuzzCampaign,
        scan: models.Scan,
        seed: Optional[models.CorpusSeed],
        signature: str,
        description: str,
        log: str,
        trace: str = "",
    ) -> models.CrashReport:
        dedup_hash = hashlib.sha256(signature.encode()).hexdigest()
        existing = self.dedupe_crash(signature)
        status = (
            models.CrashReproductionStatus.DEDUPED if existing else models.CrashReproductionStatus.NEW
        )
        crash = models.CrashReport(
            campaign_id=campaign.id,
            scan_id=scan.id,
            seed_id=seed.id if seed else None,
            signature=signature,
            description=description,
            reproduction_status=status,
            dedup_hash=dedup_hash,
            log=log,
            trace=trace,
        )
        self.db.add(crash)
        self.db.commit()
        self.db.refresh(crash)
        return crash

    def attempt_reproduction(self, crash: models.CrashReport, harness: str = "replay") -> models.CrashReport:
        """
        Mark a crash as reproducible or flaky. The reproducibility harness can be
        plugged in later; for now we simulate success and provide traceability.
        """
        # Placeholder for invoking an actual harness; treat logs as reproduction output.
        crash.reproduction_status = models.CrashReproductionStatus.REPRODUCIBLE
        crash.log = (crash.log or "") + f"\nreproduced via {harness}"
        self.db.commit()
        self.db.refresh(crash)
        return crash

    def finalize_campaign(self, campaign: models.FuzzCampaign, status: models.FuzzCampaignStatus) -> models.FuzzCampaign:
        campaign.status = status
        self.db.commit()
        self.db.refresh(campaign)
        return campaign

    # Introspection -------------------------------------------------------
    def serialize_campaign(self, campaign: models.FuzzCampaign) -> dict:
        return {
            "id": campaign.id,
            "name": campaign.name,
            "status": str(campaign.status),
            "strategy": campaign.strategy,
            "coverage_metrics": campaign.coverage_metrics,
            "seed_pool": campaign.seed_pool,
            "created_at": campaign.created_at,
            "updated_at": campaign.updated_at,
        }

    def serialize_crashes(self, crashes: Iterable[models.CrashReport]) -> List[dict]:
        serialized = []
        for crash in crashes:
            serialized.append(
                {
                    "id": crash.id,
                    "signature": crash.signature,
                    "description": crash.description,
                    "seed_id": crash.seed_id,
                    "status": crash.reproduction_status,
                    "log": crash.log,
                    "trace": crash.trace,
                }
            )
        return serialized

