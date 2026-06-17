from celery import Celery

from app.config import settings

celery_app = Celery("learnai", broker=settings.REDIS_URL, backend=settings.REDIS_URL)
celery_app.conf.update(
    task_track_started=True,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    result_expires=3600,
    imports=(
        "app.tasks.document_tasks",
        "app.tasks.generation_tasks",
        "app.tasks.maintenance_tasks",
    ),
    beat_schedule={
        "quota-warning-hourly": {
            "task": "app.tasks.maintenance_tasks.push_quota_warnings",
            "schedule": 3600.0,
        },
        "purge-due-users-daily": {
            "task": "app.tasks.maintenance_tasks.purge_due_users",
            "schedule": 86400.0,
        },
    },
)
