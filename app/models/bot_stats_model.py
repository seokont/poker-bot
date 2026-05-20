from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.integrations.database import Base


class BotStatsModel(Base):
    __tablename__ = "bot_stats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    bot_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    hands_played: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    hands_won: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    vpip_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    pfr_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    fold_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    call_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    raise_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    all_in_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    profit_loss: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )
