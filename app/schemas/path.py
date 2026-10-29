import uuid

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
