import json
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import ValidationError

from app.config import get_settings
from app.core.security import verify_service_token
from app.integrations.redis_client import get_redis_client, set_json
from app.schemas.bot_job_schema import BotTurnJob

router = APIRouter(prefix="/bots", tags=["bot-actions"])


@router.post("/action", status_code=202, dependencies=[Depends(verify_service_token)])
async def enqueue_bot_action(request: Request) -> dict[str, Any]:
    raw_body = await request.json()
    if isinstance(raw_body, str):
        try:
            raw_body = json.loads(raw_body)
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="body must be a JSON object") from exc
    if not isinstance(raw_body, dict):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="body must be a JSON object")

    try:
        job = BotTurnJob.model_validate(raw_body)
    except ValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.errors()) from exc

    settings = get_settings()
    redis_client = get_redis_client()
    job_id = str(uuid4())
    payload = job.to_task_payload
    payload["jobId"] = job_id
    set_json(redis_client, f"{settings.bot_job_payload_prefix}{job_id}", payload, ttl_seconds=300)
    redis_client.rpush(settings.bot_job_queue, job_id)
    return {
        "queued": True,
        "jobId": job_id,
        "botId": job.bot_id,
        "tableId": job.table_id,
        "handId": job.hand_id,
        "turnId": job.turn_id,
        "isBot": True,
    }
