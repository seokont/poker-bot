from sqlalchemy.orm import Session

from app.bots.bot_manager import BotManager
from app.bots.bot_statistics import get_or_create_stats, record_bot_action_stats


class BotRepository(BotManager):
    def __init__(self, db: Session) -> None:
        super().__init__(db)


__all__ = ["BotRepository", "get_or_create_stats", "record_bot_action_stats"]
