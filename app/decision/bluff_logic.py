import random

from app.bots.bot_profiles import BotProfile


def should_bluff(profile: BotProfile, board_texture: float, fold_pressure: float) -> bool:
    probability = profile.bluff_frequency + profile.aggression * 0.08 + fold_pressure * 0.05
    probability -= board_texture * 0.04
    return random.random() < max(0.0, min(0.40, probability))


def should_make_mistake(profile: BotProfile) -> bool:
    return random.random() < profile.mistake_rate
