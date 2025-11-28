from celery import Celery
from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "scan_tasks",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.workers.tasks"],

)

# Automatically discover tasks in any "tasks.py" inside "app.*"
celery_app.autodiscover_tasks(["app"])
# OR if you prefer
# celery_app.autodiscover_tasks(packages=["app.workers"])

celery_app.conf.task_routes = {
    "app.workers.tasks.*": {"queue": "scans"},
}
