from pydantic import BaseModel, Field

from app.bots.bot_profiles import BotProfileType


class BotProfileResponse(BaseModel):
    bot_id: str = Field(alias="botId")
    profile_type: BotProfileType = Field(alias="profileType")
    display_name: str = Field(alias="displayName")
    is_enabled: bool = Field(alias="enabled")
    is_bot: bool = Field(default=True, alias="isBot")
    vpip: int
    pfr: int
    aggression: float
    looseness: float
    bluff_frequency: float = Field(alias="bluffFrequency")
    mistake_rate: float = Field(alias="mistakeRate")
    bluff_chance: int = Field(alias="bluffChance")
    mistake_chance: int = Field(alias="mistakeChance")
    thinking_min_ms: int = Field(alias="thinkingMinMs")
    thinking_max_ms: int = Field(alias="thinkingMaxMs")
    target_table_id: str | None = Field(default=None, alias="targetTableId")
    preferred_seat: int | None = Field(default=None, alias="preferredSeat")

    model_config = {"populate_by_name": True}


class BotProfileUpsert(BaseModel):
    bot_id: str = Field(alias="botId", min_length=1, max_length=64)
    profile_type: BotProfileType = Field(default=BotProfileType.BALANCED, alias="profileType")
    display_name: str | None = Field(default=None, alias="displayName", max_length=128)
    enabled: bool = True
    vpip: int | None = Field(default=None, ge=0, le=100)
    pfr: int | None = Field(default=None, ge=0, le=100)
    aggression: float | None = Field(default=None, ge=0.0, le=1.0)
    looseness: float | None = Field(default=None, ge=0.0, le=1.0)
    bluff_frequency: float | None = Field(default=None, alias="bluffFrequency", ge=0.0, le=1.0)
    mistake_rate: float | None = Field(default=None, alias="mistakeRate", ge=0.0, le=1.0)
    bluff_chance: int | None = Field(default=None, alias="bluffChance", ge=0, le=100)
    mistake_chance: int | None = Field(default=None, alias="mistakeChance", ge=0, le=100)
    thinking_min_ms: int | None = Field(default=None, alias="thinkingMinMs", ge=0)
    thinking_max_ms: int | None = Field(default=None, alias="thinkingMaxMs", ge=0)
    target_table_id: str | None = Field(default=None, alias="targetTableId", max_length=128)
    preferred_seat: int | None = Field(default=None, alias="preferredSeat", ge=0)

    model_config = {"populate_by_name": True}
