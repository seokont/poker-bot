from sqlalchemy import select
from sqlalchemy.orm import Session

from app.bots.bot_profiles import PROFILE_DEFAULTS, BotProfile, BotProfileType, default_profile
from app.models.bot_profile_model import BotProfileModel
from app.schemas.bot_profile_schema import BotProfileUpsert


class BotManager:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_or_create_profile(self, bot_id: str) -> BotProfile:
        row = self.db.get(BotProfileModel, bot_id)
        if row is None:
            profile = default_profile(bot_id)
            row = BotProfileModel(
                bot_id=profile.bot_id,
                profile_type=profile.profile_type.value,
                display_name=profile.display_name,
                is_enabled=profile.is_enabled,
                is_bot=True,
                vpip=profile.vpip,
                pfr=profile.pfr,
                aggression=profile.aggression,
                looseness=profile.looseness,
                bluff_frequency=profile.bluff_frequency,
                mistake_rate=profile.mistake_rate,
                bluff_chance=profile.bluff_chance,
                mistake_chance=profile.mistake_chance,
                thinking_min_ms=profile.thinking_min_ms,
                thinking_max_ms=profile.thinking_max_ms,
                target_table_id=profile.target_table_id,
                preferred_seat=profile.preferred_seat,
            )
            self.db.add(row)
            self.db.commit()
            self.db.refresh(row)
        return self._to_profile(row)

    def list_profiles(self) -> list[BotProfile]:
        rows = self.db.scalars(select(BotProfileModel).order_by(BotProfileModel.bot_id)).all()
        return [self._to_profile(row) for row in rows]

    def upsert_profile(self, data: BotProfileUpsert) -> BotProfile:
        row = self.db.get(BotProfileModel, data.bot_id)
        defaults = PROFILE_DEFAULTS[data.profile_type]
        display_name = data.display_name or f"BOT {data.bot_id}"
        if not display_name.startswith("BOT "):
            display_name = f"BOT {display_name}"

        values = {
            "profile_type": data.profile_type.value,
            "display_name": display_name,
            "is_enabled": data.enabled,
            "is_bot": True,
            "vpip": data.vpip if data.vpip is not None else defaults["vpip"],
            "pfr": data.pfr if data.pfr is not None else defaults["pfr"],
            "aggression": data.aggression if data.aggression is not None else defaults["aggression"],
            "looseness": data.looseness if data.looseness is not None else defaults["looseness"],
            "bluff_frequency": data.bluff_frequency if data.bluff_frequency is not None else defaults["bluff_frequency"],
            "mistake_rate": data.mistake_rate if data.mistake_rate is not None else defaults["mistake_rate"],
            "bluff_chance": data.bluff_chance if data.bluff_chance is not None else defaults["bluff_chance"],
            "mistake_chance": data.mistake_chance if data.mistake_chance is not None else defaults["mistake_chance"],
            "thinking_min_ms": data.thinking_min_ms if data.thinking_min_ms is not None else defaults["thinking_min_ms"],
            "thinking_max_ms": data.thinking_max_ms if data.thinking_max_ms is not None else defaults["thinking_max_ms"],
            "target_table_id": data.target_table_id.strip() if data.target_table_id else None,
            "preferred_seat": data.preferred_seat,
        }

        if row is None:
            row = BotProfileModel(bot_id=data.bot_id, **values)
            self.db.add(row)
        else:
            for field, value in values.items():
                setattr(row, field, value)
        self.db.commit()
        self.db.refresh(row)
        return self._to_profile(row)

    def set_enabled(self, bot_id: str, enabled: bool) -> BotProfile:
        self.get_or_create_profile(bot_id)
        row = self.db.get(BotProfileModel, bot_id)
        if row is None:
            raise RuntimeError("bot profile disappeared during update")
        row.is_enabled = enabled
        row.is_bot = True
        if not row.display_name.startswith("BOT "):
            row.display_name = f"BOT {row.display_name}"
        self.db.commit()
        self.db.refresh(row)
        return self._to_profile(row)

    def delete_profile(self, bot_id: str) -> bool:
        row = self.db.get(BotProfileModel, bot_id)
        if row is None:
            return False
        self.db.delete(row)
        self.db.commit()
        return True

    @staticmethod
    def _to_profile(row: BotProfileModel) -> BotProfile:
        return BotProfile(
            bot_id=row.bot_id,
            profile_type=BotProfileType(row.profile_type),
            display_name=row.display_name if row.display_name.startswith("BOT ") else f"BOT {row.display_name}",
            is_enabled=row.is_enabled,
            vpip=row.vpip,
            pfr=row.pfr,
            aggression=row.aggression,
            looseness=row.looseness,
            bluff_frequency=row.bluff_frequency,
            mistake_rate=row.mistake_rate,
            bluff_chance=row.bluff_chance,
            mistake_chance=row.mistake_chance,
            thinking_min_ms=row.thinking_min_ms,
            thinking_max_ms=row.thinking_max_ms,
            target_table_id=row.target_table_id,
            preferred_seat=row.preferred_seat,
            is_bot=True,
        )
