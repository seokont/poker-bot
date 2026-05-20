from typing import Any

from redis import Redis

from app.integrations.redis_client import get_json, set_json


def bot_state_key(bot_id: str) -> str:
    return f"bot:{bot_id}:state"


def get_bot_state(redis_client: Redis, bot_id: str) -> dict[str, Any]:
    return get_json(redis_client, bot_state_key(bot_id)) or {
        "botId": bot_id,
        "isBot": True,
        "enabled": True,
    }


def set_bot_enabled(redis_client: Redis, bot_id: str, enabled: bool) -> dict[str, Any]:
    state = get_bot_state(redis_client, bot_id)
    state["enabled"] = enabled
    state["isBot"] = True
    set_json(redis_client, bot_state_key(bot_id), state)
    return state
