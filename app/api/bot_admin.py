from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.bots.bot_manager import BotManager
from app.bots.bot_profiles import BotProfile, BotProfileType
from app.bots.bot_state import bot_state_key, get_bot_state, set_bot_enabled
from app.integrations.database import get_db
from app.integrations.game_engine_client import GameEngineApplicationError, GameEngineClient
from app.integrations.redis_client import get_redis_client, set_json
from app.schemas.bot_profile_schema import BotProfileResponse, BotProfileUpsert

router = APIRouter(tags=["bot-admin"])


class BotLeaveRequest(BaseModel):
    table_id: str | None = Field(default=None, alias="tableId")

    model_config = {"populate_by_name": True}


def serialize_profile(profile: BotProfile) -> BotProfileResponse:
    return BotProfileResponse(
        bot_id=profile.bot_id,
        profile_type=profile.profile_type,
        display_name=profile.display_name,
        is_enabled=profile.is_enabled,
        is_bot=True,
        vpip=profile.vpip,
        pfr=profile.pfr,
        aggression=profile.aggression,
        looseness=profile.looseness,
        bluff_frequency=profile.bluff_frequency,
        mistake_rate=profile.mistake_rate,
        bluff_chance=profile.bluff_chance,
        mistake_chance=profile.mistake_chance,
        thinking_min_ms=profile.thinking_min_ms,
        thinking_max_ms=profile.thinking_max_ms,
        target_table_id=profile.target_table_id,
        preferred_seat=profile.preferred_seat,
    )


@router.get("/bots")
def list_bots(db: Session = Depends(get_db)) -> dict[str, Any]:
    profiles = BotManager(db).list_profiles()
    redis_client = get_redis_client()
    bots = []
    for profile in profiles:
        bot = serialize_profile(profile).model_dump(by_alias=True, mode="json")
        state = get_bot_state(redis_client, profile.bot_id)
        bot["state"] = {
            "status": state.get("status", "idle"),
            "tableId": state.get("tableId"),
            "handId": state.get("handId"),
            "turnId": state.get("turnId"),
            "lastAction": state.get("lastAction"),
            "thinkingDelayMs": state.get("thinkingDelayMs"),
        }
        bots.append(bot)
    return {
        "bots": bots,
        "isBotOnlyService": True,
    }


@router.post("/bots")
def upsert_bot_profile(data: BotProfileUpsert, db: Session = Depends(get_db)) -> dict[str, Any]:
    profile = BotManager(db).upsert_profile(data)
    return serialize_profile(profile).model_dump(by_alias=True, mode="json")


@router.get("/bot-profile-types")
def list_bot_profile_types() -> dict[str, list[str]]:
    return {"profileTypes": [profile_type.value for profile_type in BotProfileType]}


@router.get("/bots/{bot_id}/state")
def read_bot_state(bot_id: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    profile = BotManager(db).get_or_create_profile(bot_id)
    state = get_bot_state(get_redis_client(), bot_id)
    state.update(
        {
            "botId": bot_id,
            "displayName": profile.display_name,
            "profileType": profile.profile_type.value,
            "targetTableId": profile.target_table_id,
            "preferredSeat": profile.preferred_seat,
            "enabled": profile.is_enabled and state.get("enabled", True),
            "isBot": True,
        }
    )
    return state


@router.post("/bots/{bot_id}/join")
def join_bot_game(bot_id: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    profile = BotManager(db).get_or_create_profile(bot_id)
    if not profile.is_enabled:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="bot is disabled")
    if not profile.target_table_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="targetTableId is not configured")

    try:
        result = GameEngineClient().request_bot_join(
            bot_id=profile.bot_id,
            table_id=profile.target_table_id,
            preferred_seat=profile.preferred_seat,
        )
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "message": "main backend rejected bot join request",
                "backendStatus": exc.response.status_code,
                "backendBody": exc.response.text,
                "expectedEndpoint": "/internal/bot-join",
            },
        ) from exc
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "message": "main backend is unreachable",
                "error": str(exc),
                "expectedEndpoint": "/internal/bot-join",
            },
        ) from exc
    except GameEngineApplicationError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "message": "main backend rejected bot join request",
                "backendBody": exc.payload,
                "expectedEndpoint": "/internal/bot-join",
            },
        ) from exc
    state = set_bot_enabled(get_redis_client(), bot_id, True)
    state.update(
        {
            "status": "join_requested",
            "tableId": profile.target_table_id,
            "preferredSeat": profile.preferred_seat,
        }
    )
    set_json(get_redis_client(), bot_state_key(bot_id), state, ttl_seconds=3600)
    return {
        "queued": False,
        "sent": True,
        "botId": profile.bot_id,
        "tableId": profile.target_table_id,
        "preferredSeat": profile.preferred_seat,
        "backend": result,
    }


@router.post("/bots/{bot_id}/leave")
def leave_bot_game(data: BotLeaveRequest, bot_id: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    profile = BotManager(db).get_or_create_profile(bot_id)
    redis_client = get_redis_client()
    state = get_bot_state(redis_client, bot_id)
    table_id = data.table_id or state.get("tableId") or profile.target_table_id
    if not table_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="bot is not assigned to a table")

    try:
        result = GameEngineClient().request_bot_leave(bot_id=profile.bot_id, table_id=table_id)
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "message": "main backend rejected bot leave request",
                "backendStatus": exc.response.status_code,
                "backendBody": exc.response.text,
                "expectedEndpoint": "/internal/bot-leave",
            },
        ) from exc
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "message": "main backend is unreachable",
                "error": str(exc),
                "expectedEndpoint": "/internal/bot-leave",
            },
        ) from exc
    except GameEngineApplicationError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "message": "main backend rejected bot leave request",
                "backendBody": exc.payload,
                "expectedEndpoint": "/internal/bot-leave",
            },
        ) from exc

    state.update(
        {
            "status": "left_game",
            "tableId": None,
            "handId": None,
            "turnId": None,
            "lastAction": None,
            "thinkingDelayMs": None,
        }
    )
    set_json(redis_client, bot_state_key(bot_id), state, ttl_seconds=3600)
    return {
        "sent": True,
        "botId": profile.bot_id,
        "tableId": table_id,
        "backend": result,
    }


@router.post("/bots/{bot_id}/enable")
def enable_bot(bot_id: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    profile = BotManager(db).set_enabled(bot_id, True)
    state = set_bot_enabled(get_redis_client(), bot_id, True)
    return {
        "botId": bot_id,
        "displayName": profile.display_name,
        "profileType": profile.profile_type.value,
        "enabled": state["enabled"],
        "isBot": True,
    }


@router.post("/bots/{bot_id}/disable")
def disable_bot(bot_id: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    profile = BotManager(db).set_enabled(bot_id, False)
    state = set_bot_enabled(get_redis_client(), bot_id, False)
    return {
        "botId": bot_id,
        "displayName": profile.display_name,
        "profileType": profile.profile_type.value,
        "enabled": state["enabled"],
        "isBot": True,
    }


@router.delete("/bots/{bot_id}")
def delete_bot(bot_id: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    deleted = BotManager(db).delete_profile(bot_id)
    redis_client = get_redis_client()
    redis_client.delete(bot_state_key(bot_id))
    redis_client.delete(f"recent:bot:{bot_id}:actions")
    return {
        "deleted": deleted,
        "botId": bot_id,
    }
