from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "senior_jobs",
    broker=settings.celery_broker_url,
    backend=settings.celery_broker_url.replace("/1", "/2"),
    include=["app.tasks.export_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Seoul",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)
