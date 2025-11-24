.PHONY: dev backend worker test

dev:
docker compose up --build

backend:
cd backend && uvicorn app.main:app --reload

worker:
cd backend && celery -A app.workers.celery_app:celery_app worker -Q scans -l info

test:
cd backend && pytest