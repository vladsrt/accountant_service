"""Celery worker setup for background tasks."""

import os

from celery import Celery

# Initialize Celery app
celery_app = Celery(
    "accountant_service_worker",
    broker=os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0"),
    include=["app.tasks.ksef_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour max run time for sync
)
