from __future__ import annotations

from celery import Celery
from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "scan_tasks",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.task_routes = {"app.workers.tasks.*": {"queue": "scans"}}