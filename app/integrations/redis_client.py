import json
from typing import Any

from redis import Redis

from app.config import get_settings


def get_redis_client() -> Redis:
    return Redis.from_url(get_settings().redis_url, decode_responses=True)


def acquire_turn_lock(redis_client: Redis, key: str, ttl_seconds: int) -> bool:
    return bool(redis_client.set(key, "1", nx=True, ex=ttl_seconds))


def release_turn_lock(redis_client: Redis, key: str) -> None:
    redis_client.delete(key)


def get_json(redis_client: Redis, key: str) -> dict[str, Any] | None:
    raw = redis_client.get(key)
    if not raw:
        return None
    return json.loads(raw)


def set_json(redis_client: Redis, key: str, value: dict[str, Any], ttl_seconds: int | None = None) -> None:
    redis_client.set(key, json.dumps(value), ex=ttl_seconds)
