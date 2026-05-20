from pydantic import BaseModel, Field, field_validator, model_validator

from app.schemas.bot_action_schema import BotAction
from app.schemas.game_state_schema import GameType, Position, Street


class PreviousAction(BaseModel):
    player_id: str = Field(alias="playerId", min_length=1)
    action: BotAction
    amount: int | None = Field(default=None, ge=0)

    model_config = {"populate_by_name": True}


class BotTurnJob(BaseModel):
    bot_id: str = Field(alias="botId", min_length=1)
    table_id: str = Field(alias="tableId", min_length=1)
    hand_id: str = Field(alias="handId", min_length=1)
    turn_id: str = Field(default="current", alias="turnId", min_length=1)
    street: Street
    game_type: GameType = Field(alias="gameType")
    bot_hole_cards: list[str] = Field(alias="botHoleCards", min_length=2, max_length=2)
    board_cards: list[str] = Field(default_factory=list, alias="boardCards", max_length=5)
    pot_size: int = Field(alias="potSize", ge=0)
    current_bet: int = Field(alias="currentBet", ge=0)
    bot_stack: int = Field(alias="botStack", ge=0)
    bot_current_bet: int = Field(alias="botCurrentBet", ge=0)
    big_blind: int = Field(default=10, alias="bigBlind", ge=1)
    position: Position = Position.UNKNOWN
    active_players_count: int = Field(alias="activePlayersCount", ge=1)
    legal_actions: list[BotAction] = Field(alias="legalActions", min_length=1)
    min_raise: int | None = Field(default=None, alias="minRaise", ge=0)
    max_raise: int | None = Field(default=None, alias="maxRaise", ge=0)
    previous_actions: list[PreviousAction] = Field(default_factory=list, alias="previousActions")

    model_config = {"populate_by_name": True}

    @field_validator("bot_id", "table_id", "hand_id", "turn_id", mode="before")
    @classmethod
    def strip_ids(cls, value: str) -> str:
        return value.strip() if isinstance(value, str) else value

    @model_validator(mode="after")
    def validate_visible_card_counts(self) -> "BotTurnJob":
        if self.game_type not in {GameType.NO_LIMIT_HOLDEM, GameType.TEXAS_HOLDEM, GameType.NLH}:
            raise ValueError(f"{self.game_type} is planned but not implemented yet")
        expected_board_cards = {
            Street.PREFLOP: 0,
            Street.FLOP: 3,
            Street.TURN: 4,
            Street.RIVER: 5,
        }[self.street]
        if len(self.board_cards) != expected_board_cards:
            raise ValueError(f"{self.street} requires {expected_board_cards} board cards")
        return self

    @property
    def to_task_payload(self) -> dict:
        return self.model_dump(by_alias=True, mode="json")
