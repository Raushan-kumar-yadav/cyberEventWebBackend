from pydantic import BaseModel, Field

from app.models.enums import GameStatus
from app.schemas.common import LocalDatetime


# public game clock
class GameStateOut(BaseModel):
    status: GameStatus
    start_at: LocalDatetime | None
    end_at: LocalDatetime | None
    remaining_seconds: int | None
    version: int


# admin game clock
class AdminGameStateOut(GameStateOut):
    paused_at: LocalDatetime | None
    paused_seconds: int
    active_seconds: int


# start request
class GameStart(BaseModel):
    duration_minutes: int | None = Field(default=None, ge=1, le=600)


# time increase request
class TimeIncrease(BaseModel):
    minutes: int = Field(ge=1, le=180)
