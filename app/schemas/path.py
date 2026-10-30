import uuid
from typing import Literal

from pydantic import BaseModel

from app.schemas.common import LocalDatetime


# path on the map
class PathOut(BaseModel):
    path_id: int
    name: str
    start_region: str
    question_count: int
    completed: bool
    is_current: bool
    current_question_id: uuid.UUID | None


# team active path
class CurrentPathOut(BaseModel):
    path_id: int | None
    switch_from_path_id: int | None
    frozen_until: LocalDatetime | None


# next question on a path
class PathQuestionOut(BaseModel):
    path_id: int
    question_id: uuid.UUID | None
    completed: bool


# path switch request
class PathChangeIn(BaseModel):
    mode: Literal["pay", "wait"] = "pay"


# path switch result
class PathChangeOut(BaseModel):
    ok: bool = True
    path_id: int
    mode: Literal["free", "pay", "wait"]
    charged: int
    points: int
    starts_at: LocalDatetime
    frozen_until: LocalDatetime | None


# switch cancel result
class PathCancelOut(BaseModel):
    ok: bool = True
    path_id: int
