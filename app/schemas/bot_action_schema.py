from enum import StrEnum

from pydantic import BaseModel, Field, model_validator


class BotAction(StrEnum):
    FOLD = "FOLD"
    CHECK = "CHECK"
    CALL = "CALL"
    BET = "BET"
    RAISE = "RAISE"
    ALL_IN = "ALL_IN"


class BotActionProposal(BaseModel):
    action: BotAction
    amount: int | None = Field(default=None, ge=0)
    reason: str = Field(min_length=1, max_length=500)

    @model_validator(mode="after")
    def validate_amount_for_action(self) -> "BotActionProposal":
        if self.action in {BotAction.FOLD, BotAction.CHECK} and self.amount is not None:
            raise ValueError("FOLD and CHECK must not include an amount")
        if self.action in {BotAction.CALL, BotAction.BET, BotAction.RAISE, BotAction.ALL_IN} and self.amount is None:
            raise ValueError(f"{self.action} requires an amount")
        return self


class BotActionOutput(BotActionProposal):
    bot_id: str = Field(alias="botId")
    table_id: str = Field(alias="tableId")
    hand_id: str = Field(alias="handId")
    turn_id: str = Field(alias="turnId")

    model_config = {"populate_by_name": True}
