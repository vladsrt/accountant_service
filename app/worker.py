"""Celery worker setup for background tasks."""

from celery import Celery

from app.core.config import settings

# Initialize Celery app
celery_app = Celery(
    "accountant_service_worker",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "app.tasks.ksef_tasks",
        "app.tasks.email_tasks",
        "app.tasks.classification_tasks",
    ],
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
