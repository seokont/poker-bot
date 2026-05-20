from typing import Any

from pydantic import BaseModel, Field


class BackendBotQueueJob(BaseModel):
    job_id: str = Field(alias="jobId", min_length=1)
    turn_id: str = Field(alias="turnId", min_length=1)
    bot_id: str = Field(alias="botId", min_length=1)
    table_id: str = Field(alias="tableId", min_length=1)
    hand_id: str = Field(alias="handId", min_length=1)
    street: str
    acting_seat: int | None = Field(default=None, alias="actingSeat")
    game_type: str = Field(default="TEXAS_HOLDEM", alias="gameType")
    visible_state: dict[str, Any] = Field(default_factory=dict, alias="visibleState")
    enqueued_at: int | None = Field(default=None, alias="enqueuedAt")
    complexity: str = "normal"

    model_config = {"populate_by_name": True, "extra": "allow"}
