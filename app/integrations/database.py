from collections.abc import Generator
import time

from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings


class Base(DeclarativeBase):
    pass


settings = get_settings()
engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_database_tables(retries: int = 20, delay_seconds: float = 1.0) -> None:
    # Import models so SQLAlchemy registers them before create_all.
    import app.models.bot_action_log_model  # noqa: F401
    import app.models.bot_profile_model  # noqa: F401
    import app.models.bot_stats_model  # noqa: F401

    for attempt in range(1, retries + 1):
        try:
            Base.metadata.create_all(bind=engine)
            ensure_additive_columns()
            return
        except OperationalError:
            if attempt == retries:
                raise
            time.sleep(delay_seconds)


def ensure_additive_columns() -> None:
    # Demo service uses create_all instead of migrations; these additive checks keep old Docker volumes usable.
    statements = [
        "ALTER TABLE bot_profiles ADD COLUMN IF NOT EXISTS vpip INTEGER NOT NULL DEFAULT 25",
        "ALTER TABLE bot_profiles ADD COLUMN IF NOT EXISTS pfr INTEGER NOT NULL DEFAULT 18",
        "ALTER TABLE bot_profiles ADD COLUMN IF NOT EXISTS bluff_chance INTEGER NOT NULL DEFAULT 10",
        "ALTER TABLE bot_profiles ADD COLUMN IF NOT EXISTS mistake_chance INTEGER NOT NULL DEFAULT 5",
        "ALTER TABLE bot_profiles ADD COLUMN IF NOT EXISTS thinking_min_ms INTEGER NOT NULL DEFAULT 1000",
        "ALTER TABLE bot_profiles ADD COLUMN IF NOT EXISTS thinking_max_ms INTEGER NOT NULL DEFAULT 6500",
        "ALTER TABLE bot_profiles ADD COLUMN IF NOT EXISTS target_table_id VARCHAR(128)",
        "ALTER TABLE bot_profiles ADD COLUMN IF NOT EXISTS preferred_seat INTEGER",
        "ALTER TABLE bot_action_logs ADD COLUMN IF NOT EXISTS street VARCHAR(16) NOT NULL DEFAULT 'UNKNOWN'",
        "ALTER TABLE bot_action_logs ADD COLUMN IF NOT EXISTS decision_time_ms INTEGER NOT NULL DEFAULT 0",
    ]
    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))
