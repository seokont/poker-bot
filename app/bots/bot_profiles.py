from dataclasses import dataclass
from enum import StrEnum


class BotProfileType(StrEnum):
    BEGINNER = "BEGINNER"
    TIGHT_PASSIVE = "TIGHT_PASSIVE"
    TIGHT_AGGRESSIVE = "TIGHT_AGGRESSIVE"
    LOOSE_PASSIVE = "LOOSE_PASSIVE"
    LOOSE_AGGRESSIVE = "LOOSE_AGGRESSIVE"
    BALANCED = "BALANCED"


@dataclass(frozen=True)
class BotProfile:
    bot_id: str
    profile_type: BotProfileType
    display_name: str
    is_enabled: bool
    vpip: int
    pfr: int
    aggression: float
    looseness: float
    bluff_frequency: float
    mistake_rate: float
    bluff_chance: int
    mistake_chance: int
    thinking_min_ms: int
    thinking_max_ms: int
    target_table_id: str | None = None
    preferred_seat: int | None = None
    is_bot: bool = True


PROFILE_DEFAULTS: dict[BotProfileType, dict[str, float | int]] = {
    BotProfileType.BEGINNER: {
        "vpip": 35,
        "pfr": 8,
        "aggression": 0.35,
        "looseness": 0.55,
        "bluff_frequency": 0.05,
        "mistake_rate": 0.18,
        "bluff_chance": 5,
        "mistake_chance": 18,
        "thinking_min_ms": 800,
        "thinking_max_ms": 6000,
    },
    BotProfileType.TIGHT_PASSIVE: {
        "vpip": 15,
        "pfr": 5,
        "aggression": 0.25,
        "looseness": 0.25,
        "bluff_frequency": 0.02,
        "mistake_rate": 0.05,
        "bluff_chance": 2,
        "mistake_chance": 5,
        "thinking_min_ms": 1200,
        "thinking_max_ms": 7000,
    },
    BotProfileType.TIGHT_AGGRESSIVE: {
        "vpip": 20,
        "pfr": 15,
        "aggression": 0.70,
        "looseness": 0.30,
        "bluff_frequency": 0.08,
        "mistake_rate": 0.04,
        "bluff_chance": 8,
        "mistake_chance": 4,
        "thinking_min_ms": 1000,
        "thinking_max_ms": 6500,
    },
    BotProfileType.LOOSE_PASSIVE: {
        "vpip": 45,
        "pfr": 8,
        "aggression": 0.30,
        "looseness": 0.75,
        "bluff_frequency": 0.04,
        "mistake_rate": 0.12,
        "bluff_chance": 4,
        "mistake_chance": 12,
        "thinking_min_ms": 900,
        "thinking_max_ms": 6000,
    },
    BotProfileType.LOOSE_AGGRESSIVE: {
        "vpip": 40,
        "pfr": 28,
        "aggression": 0.85,
        "looseness": 0.75,
        "bluff_frequency": 0.20,
        "mistake_rate": 0.08,
        "bluff_chance": 20,
        "mistake_chance": 8,
        "thinking_min_ms": 800,
        "thinking_max_ms": 7000,
    },
    BotProfileType.BALANCED: {
        "vpip": 25,
        "pfr": 18,
        "aggression": 0.60,
        "looseness": 0.45,
        "bluff_frequency": 0.10,
        "mistake_rate": 0.05,
        "bluff_chance": 10,
        "mistake_chance": 5,
        "thinking_min_ms": 1000,
        "thinking_max_ms": 6500,
    },
}


def default_profile(bot_id: str, profile_type: BotProfileType = BotProfileType.BALANCED) -> BotProfile:
    defaults = PROFILE_DEFAULTS[profile_type]
    return BotProfile(
        bot_id=bot_id,
        profile_type=profile_type,
        display_name=f"BOT {bot_id}",
        is_enabled=True,
        **defaults,
    )
