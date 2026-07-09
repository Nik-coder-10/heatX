"""
Urban Heat Mitigation Platform - Celery Worker Configuration

Celery is used for:
- Satellite image acquisition (long-running downloads)
- Raster processing pipelines
- ML model training (async)
- Report generation
- Email notifications
- Data export tasks
"""

from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "urbanheat",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,
    task_soft_time_limit=3000,
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=100,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    result_expires=86400,
)

# Auto-discover tasks from app modules
celery_app.autodiscover_tasks([
    "app.satellite",
    "app.preprocessing",
    "app.indices",
    "app.lst",
    "app.ml",
    "app.xai",
    "app.recommendation",
    "app.scenario",
])


@celery_app.task(bind=True, name="health_check")
def health_check(self):
    """Celery worker health check task."""
    return {"status": "ok", "worker": self.request.hostname}
