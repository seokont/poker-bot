from enum import StrEnum

from pydantic import BaseModel, Field


class Street(StrEnum):
    PREFLOP = "PREFLOP"
    FLOP = "FLOP"
    TURN = "TURN"
    RIVER = "RIVER"


class GameType(StrEnum):
    NO_LIMIT_HOLDEM = "NO_LIMIT_HOLDEM"
    TEXAS_HOLDEM = "TEXAS_HOLDEM"
    NLH = "NLH"
    OMAHA_4 = "OMAHA_4"
    OMAHA_5 = "OMAHA_5"
    OMAHA_6 = "OMAHA_6"
    OMAHA_7 = "OMAHA_7"
    CRAZY_PINEAPPLE = "CRAZY_PINEAPPLE"


class Position(StrEnum):
    EARLY = "EARLY"
    MIDDLE = "MIDDLE"
    LATE = "LATE"
    BUTTON = "BUTTON"
    SMALL_BLIND = "SMALL_BLIND"
    BIG_BLIND = "BIG_BLIND"
    SB = "SB"
    BB = "BB"
    UTG = "UTG"
    MP = "MP"
    CO = "CO"
    BTN = "BTN"
    UNKNOWN = "UNKNOWN"


class VisibleGameState(BaseModel):
    street: Street
    game_type: GameType = Field(alias="gameType")
    bot_hole_cards: list[str] = Field(alias="botHoleCards", min_length=2, max_length=7)
    board_cards: list[str] = Field(default_factory=list, alias="boardCards", max_length=5)
    pot_size: int = Field(alias="potSize", ge=0)
    current_bet: int = Field(alias="currentBet", ge=0)
    bot_stack: int = Field(alias="botStack", ge=0)
    bot_current_bet: int = Field(alias="botCurrentBet", ge=0)
    position: Position = Position.UNKNOWN
    active_players_count: int = Field(alias="activePlayersCount", ge=1)
    previous_actions: list[dict] = Field(default_factory=list, alias="previousActions")

    model_config = {"populate_by_name": True}
