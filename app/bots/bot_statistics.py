from sqlalchemy.orm import Session

from app.models.bot_stats_model import BotStatsModel
from app.schemas.bot_action_schema import BotAction
from app.schemas.bot_job_schema import BotTurnJob


def get_or_create_stats(db: Session, bot_id: str) -> BotStatsModel:
    row = db.query(BotStatsModel).filter(BotStatsModel.bot_id == bot_id).one_or_none()
    if row is None:
        row = BotStatsModel(bot_id=bot_id)
        db.add(row)
        db.flush()
    return row


def record_bot_action_stats(db: Session, job: BotTurnJob, action: BotAction) -> None:
    stats = get_or_create_stats(db, job.bot_id)
    if action == BotAction.FOLD:
        stats.fold_count += 1
    elif action == BotAction.CALL:
        stats.call_count += 1
        stats.vpip_count += 1
    elif action in {BotAction.BET, BotAction.RAISE}:
        stats.raise_count += 1
        stats.vpip_count += 1
        if job.street.value == "PREFLOP":
            stats.pfr_count += 1
    elif action == BotAction.ALL_IN:
        stats.all_in_count += 1
        stats.vpip_count += 1
    db.commit()
