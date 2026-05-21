from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "poker-bot-server"
    bot_server_port: int = Field(default=8000, alias="BOT_SERVER_PORT")
    database_url: str = Field(
        default="postgresql+psycopg2://bot:bot@localhost:5432/bot_server",
        alias="DATABASE_URL",
    )
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    celery_broker_url: str = Field(default="redis://localhost:6379/1", alias="CELERY_BROKER_URL")
    celery_result_backend: str = Field(default="redis://localhost:6379/2", alias="CELERY_RESULT_BACKEND")
    main_backend_url: str = Field(default="http://localhost:8080", alias="MAIN_BACKEND_URL")
    service_token: str = Field(default="change-me", alias="SERVICE_TOKEN")
    bot_job_queue: str = Field(default="bot_action_queue", alias="BOT_JOB_QUEUE")
    # Avoid `bot:job:` — many backends reuse that pattern for non-string types (WRONGTYPE on GET).
    bot_job_payload_prefix: str = Field(default="poker_bot_server:job:", alias="BOT_JOB_PAYLOAD_PREFIX")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    bot_lock_ttl_seconds: int = Field(
        default=90,
        alias="BOT_LOCK_TTL_SECONDS",
        description="Redis lock TTL while a bot turn is being processed (covers thinking delay).",
    )
    bot_turn_lock_wait_seconds: int = Field(
        default=25,
        alias="BOT_TURN_LOCK_WAIT_SECONDS",
        description="How long to wait for another worker's turn lock before sending anyway.",
    )
    bot_action_send_retries: int = Field(default=3, alias="BOT_ACTION_SEND_RETRIES")
    bot_equity_enabled: bool = Field(default=True, alias="BOT_EQUITY_ENABLED")
    bot_equity_sample_count: int = Field(
        default=300,
        alias="BOT_EQUITY_SAMPLE_COUNT",
        ge=100,
        le=5000,
        description="Monte Carlo samples for PokerKit calculate_equities (300 is faster on small VPS).",
    )
    bot_use_action_history: bool = Field(
        default=True,
        alias="BOT_USE_ACTION_HISTORY",
        description="Tighten/widen villain range using job.previousActions when available.",
    )
    request_timeout_seconds: float = Field(
        default=30.0,
        alias="REQUEST_TIMEOUT_SECONDS",
        description="HTTP read timeout when calling main backend (bot-action, validate-turn, bot-join).",
    )
    dashboard_username: str = Field(default="admin", alias="DASHBOARD_USERNAME")
    dashboard_password: str = Field(default="change-me", alias="DASHBOARD_PASSWORD")
    dashboard_session_secret: str = Field(default="", alias="DASHBOARD_SESSION_SECRET")
    dashboard_cookie_secure: bool = Field(default=False, alias="DASHBOARD_COOKIE_SECURE")
    trust_proxy_headers: bool = Field(default=False, alias="TRUST_PROXY_HEADERS")


@lru_cache
def get_settings() -> Settings:
    return Settings()
