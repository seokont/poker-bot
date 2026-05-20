import json
import time
from typing import Any

from redis.exceptions import ResponseError

from app.config import get_settings
from app.core.logging import configure_logging, logger
from app.integrations.redis_client import get_redis_client
from app.workers.bot_action_worker import process_bot_turn_job
from app.workers.job_normalizer import normalize_backend_queue_job


def main() -> None:
    configure_logging()
    settings = get_settings()
    redis_client = get_redis_client()
    logger.info("Starting raw Redis bot worker on queue %s", settings.bot_job_queue)

    while True:
        try:
            item = redis_client.blpop(settings.bot_job_queue, timeout=5)
            if item is None:
                continue

            _, raw_value = item
            payload = load_payload(redis_client, raw_value)
            job = normalize_backend_queue_job(payload)
            result = process_bot_turn_job(job)
            logger.info("Processed bot job: %s", result)
        except Exception:
            logger.exception("Failed to process bot queue item")
            time.sleep(1)


def load_payload(redis_client, raw_value: str) -> dict[str, Any]:
    settings = get_settings()
    value = raw_value.strip()

    try:
        queue_message = json.loads(value)
    except json.JSONDecodeError:
        queue_message = {"jobId": value}

    if isinstance(queue_message, str):
        queue_message = {"jobId": queue_message}

    if not isinstance(queue_message, dict):
        raise ValueError("bot queue item must be a jobId string or JSON object")

    job_id = queue_message.get("jobId")
    if job_id:
        job_id = str(job_id).strip()
        key = f"{settings.bot_job_payload_prefix}{job_id}"
        try:
            stored_payload = redis_client.get(key)
        except ResponseError as exc:
            if "WRONGTYPE" in str(exc):
                key_type = redis_client.type(key)
                logger.error(
                    "Redis key %s has type %s, but bot-server expects a STRING JSON value. "
                    "Another service may use the same key pattern. Set BOT_JOB_PAYLOAD_PREFIX to a unique prefix "
                    "or delete/rename the conflicting key.",
                    key,
                    key_type,
                )
            raise
        if stored_payload:
            stored = json.loads(stored_payload)
            if isinstance(stored, dict):
                stored.setdefault("jobId", job_id)
                return stored

    return queue_message


if __name__ == "__main__":
    main()
