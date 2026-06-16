from celery import Celery

from app.config import settings

celery_app = Celery("learnai", broker=settings.REDIS_URL, backend=settings.REDIS_URL)
celery_app.conf.update(
    task_track_started=True,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
)

