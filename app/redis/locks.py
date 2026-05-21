from redis import Redis

from app.config import get_settings
from app.integrations.redis_client import acquire_turn_lock, release_turn_lock


def turn_lock_key(bot_id: str, hand_id: str, turn_id: str) -> str:
    return f"lock:bot:{bot_id}:hand:{hand_id}:turn:{turn_id}"


def sent_action_key(bot_id: str, hand_id: str, turn_id: str) -> str:
    return f"sent:bot:{bot_id}:hand:{hand_id}:turn:{turn_id}"


def acquire_bot_turn_lock(
    redis_client: Redis,
    bot_id: str,
    hand_id: str,
    turn_id: str,
    ttl_seconds: int | None = None,
) -> bool:
    ttl = ttl_seconds if ttl_seconds is not None else get_settings().bot_lock_ttl_seconds
    return acquire_turn_lock(redis_client, turn_lock_key(bot_id, hand_id, turn_id), ttl)


def release_bot_turn_lock(redis_client: Redis, bot_id: str, hand_id: str, turn_id: str) -> None:
    release_turn_lock(redis_client, turn_lock_key(bot_id, hand_id, turn_id))
