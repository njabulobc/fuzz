from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import models, schemas
from app.db.session import SessionLocal
from app.services.contract_generator import generate_contract
from app.workers.tasks import run_scan_task

router = APIRouter(prefix="/contracts", tags=["contracts"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/generate-and-scan", response_model=schemas.ContractGenerationResponse)
def generate_and_scan(db: Session = Depends(get_db)):
    contract_name, contract_path, _ = generate_contract()

    project = models.Project(name=f"Generated {contract_name}", path=contract_path, meta={"generated": True})
    db.add(project)
    db.commit()
    db.refresh(project)

    scan = models.Scan(
        project_id=project.id,
        target=contract_path,
        tools=["slither", "mythril", "echidna"],
        status=models.ScanStatus.PENDING,
        started_at=datetime.utcnow(),
    )
    db.add(scan)
    db.commit()
    db.refresh(scan)
    run_scan_task.delay(scan.id)

    return schemas.ContractGenerationResponse(
        contract_name=contract_name,
        contract_path=contract_path,
        project=project,
        scan=scan,
    )
