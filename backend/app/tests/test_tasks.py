from app.workers.celery_app import celery_app
from app.workers.tasks import run_scan_task


def test_run_scan_task_routes_to_scans_queue():
    route = celery_app.amqp.router.route({}, name=run_scan_task.name)
    assert route["queue"].name == "scans"
