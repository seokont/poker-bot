import random

from app.bots.bot_profiles import BotProfile


def chance(percent: int | float) -> bool:
    return random.uniform(0, 100) < percent


def apply_mistake_noise(score: float, profile: BotProfile) -> float:
    if not chance(profile.mistake_chance):
        return score
    return max(0.0, min(1.0, score + random.uniform(-0.18, 0.12)))


def occasional_slowdown_ms(profile: BotProfile) -> int:
    if chance(profile.mistake_chance / 3):
        return random.randint(500, 1800)
    return 0
