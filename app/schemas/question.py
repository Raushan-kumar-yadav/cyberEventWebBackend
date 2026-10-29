import uuid
from typing import Literal

from pydantic import BaseModel

from app.schemas.common import LocalDatetime

QuestionState = Literal["active", "solved", "skipped", "blocked", "out_of_retries"]


# team view of  question
class QuestionOut(BaseModel):
    question_id: uuid.UUID
    path_id: int | None
    title: str
    story: str
    monument: str
    is_final: bool
    file_url: str | None
    state: QuestionState
    current_points: int
    points_awarded: int
    retries_total: int
    retries_left: int
    hints_available: list[int]
    hint1: str | None
    hint2: str | None
    blocked_until: LocalDatetime | None
    wait_until: LocalDatetime | None
    first_solve_open: bool
