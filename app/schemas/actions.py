import uuid
from typing import Any, Literal

from pydantic import BaseModel, field_validator

from app.schemas.common import LocalDatetime


# hint purchase, 12 = both
class HintIn(BaseModel):
    hint: Literal["1", "2", "12"]

    @field_validator("hint", mode="before")
    @classmethod
    def _as_text(cls, value: Any) -> Any:
        return str(value) if isinstance(value, int) else value


# hint purchase result
class HintOut(BaseModel):
    question_id: uuid.UUID
    hint1: str | None
    hint2: str | None
    charged: int
    points: int


# retry purchase result
class RetryOut(BaseModel):
    ok: bool = True
    retries_left: int
    charged: int
    points: int


# skip result
class SkipOut(BaseModel):
    ok: bool = True
    charged: int
    points: int
    next_question_id: uuid.UUID | None
    path_completed: bool


# wait request
class WaitIn(BaseModel):
    wait: bool


# wait / cancel result
class WaitOut(BaseModel):
    ok: bool = True
    wait_until: LocalDatetime | None
