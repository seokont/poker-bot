from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.bots.bot_profiles import BotProfileType
from app.integrations.database import Base


class BotProfileModel(Base):
    __tablename__ = "bot_profiles"

    bot_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    profile_type: Mapped[str] = mapped_column(String(32), default=BotProfileType.BALANCED.value, nullable=False)
    display_name: Mapped[str] = mapped_column(String(128), nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_bot: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    vpip: Mapped[int] = mapped_column(Integer, default=25, nullable=False)
    pfr: Mapped[int] = mapped_column(Integer, default=18, nullable=False)
    aggression: Mapped[float] = mapped_column(Float, default=0.55, nullable=False)
    looseness: Mapped[float] = mapped_column(Float, default=0.45, nullable=False)
    bluff_frequency: Mapped[float] = mapped_column(Float, default=0.10, nullable=False)
    mistake_rate: Mapped[float] = mapped_column(Float, default=0.02, nullable=False)
    bluff_chance: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    mistake_chance: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    thinking_min_ms: Mapped[int] = mapped_column(Integer, default=1000, nullable=False)
    thinking_max_ms: Mapped[int] = mapped_column(Integer, default=6500, nullable=False)
    target_table_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    preferred_seat: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )
