from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.integrations.database import Base


class BotActionLogModel(Base):
    __tablename__ = "bot_action_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    bot_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    table_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    hand_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    turn_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    street: Mapped[str] = mapped_column(String(16), default="UNKNOWN", nullable=False)
    action: Mapped[str] = mapped_column(String(16), nullable=False)
    amount: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reason: Mapped[str] = mapped_column(String(500), nullable=False)
    decision_time_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="SENT", nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
