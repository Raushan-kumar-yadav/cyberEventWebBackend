import uuid
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.common import LocalDatetime


# flag submission
class SubmitIn(BaseModel):
    flag: str = Field(min_length=1, max_length=256)
    first_solve_action: Literal["claim", "block"] = "claim"


# submission result
class SubmitOut(BaseModel):
    result: Literal["correct", "wrong", "block", "out_of_retries"]
    already_solved: bool = False
    points_awarded: int = 0
    points: int
    retries_left: int
    first_solver: bool = False
    blocked_until: LocalDatetime | None = None
    next_question_id: uuid.UUID | None = None
    path_completed: bool = False
    reached_delhi: bool = False
