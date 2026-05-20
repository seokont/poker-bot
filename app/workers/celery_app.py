from celery import Celery

from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "poker_bot_server",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.workers.bot_action_worker"],
)

celery_app.conf.update(
    task_default_queue="bot_action_queue",
    task_routes={"process_bot_action": {"queue": "bot_action_queue"}},
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)
