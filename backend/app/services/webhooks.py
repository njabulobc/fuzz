from __future__ import annotations

import json
from typing import Any, Dict

import requests

from app import models
from app.config import get_settings
from app.services.reporting import build_scan_report

settings = get_settings()


def dispatch_scan_webhook(scan: models.Scan) -> None:
    """Send structured telemetry to a configured webhook."""

    payload: Dict[str, Any] = build_scan_report(scan)
    payload.update({
        "status": str(scan.status),
        "started_at": scan.started_at.isoformat() if scan.started_at else None,
        "finished_at": scan.finished_at.isoformat() if scan.finished_at else None,
    })

    try:
        requests.post(scan.webhook_url, data=json.dumps(payload), headers={"Content-Type": "application/json"}, timeout=5)
    except Exception:
        # Webhook failures should not crash the scan worker
        pass
