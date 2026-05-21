from app.schemas.game_state_schema import GameType

HOLDEM_GAME_TYPES = {
    GameType.NO_LIMIT_HOLDEM,
    GameType.TEXAS_HOLDEM,
    GameType.NLH,
}

OMAHA_GAME_TYPES = {
    GameType.OMAHA_4,
    GameType.OMAHA_5,
    GameType.OMAHA_6,
    GameType.OMAHA_7,
}

SUPPORTED_GAME_TYPES = HOLDEM_GAME_TYPES | OMAHA_GAME_TYPES

HOLE_CARD_COUNT: dict[GameType, int] = {
    GameType.NO_LIMIT_HOLDEM: 2,
    GameType.TEXAS_HOLDEM: 2,
    GameType.NLH: 2,
    GameType.OMAHA_4: 4,
    GameType.OMAHA_5: 5,
    GameType.OMAHA_6: 6,
    GameType.OMAHA_7: 7,
}


def is_holdem(game_type: GameType) -> bool:
    return game_type in HOLDEM_GAME_TYPES


def is_omaha(game_type: GameType) -> bool:
    return game_type in OMAHA_GAME_TYPES


def is_supported_game_type(game_type: GameType) -> bool:
    return game_type in SUPPORTED_GAME_TYPES


def expected_hole_card_count(game_type: GameType) -> int:
    return HOLE_CARD_COUNT[game_type]


def game_type_label(game_type: GameType) -> str:
    if is_holdem(game_type):
        return "Hold'em"
    return f"Omaha {expected_hole_card_count(game_type)}"
