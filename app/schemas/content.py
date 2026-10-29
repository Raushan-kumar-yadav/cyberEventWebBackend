import uuid
from pathlib import PurePosixPath
from typing import Annotated, Self

from pydantic import AfterValidator, AliasChoices, BaseModel, ConfigDict, Field, model_validator

from app.schemas.common import LocalDatetime


def _safe_relative(value: str | None) -> str | None:
    if value is None:
        return None
    path = PurePosixPath(value.replace("\\", "/"))
    if not path.parts or path.is_absolute() or ".." in path.parts or ":" in value:
        raise ValueError("must be a relative path inside the files folder")
    return path.as_posix()


Code = Annotated[str, Field(min_length=1, max_length=64, pattern=r"^[a-z0-9][a-z0-9_-]*$")]
Title = Annotated[str, Field(min_length=1, max_length=200)]
Story = Annotated[str, Field(min_length=1, max_length=20_000)]
Monument = Annotated[str, Field(min_length=1, max_length=128)]
Hint = Annotated[str, Field(min_length=1, max_length=5_000)]
FilePath = Annotated[str, Field(max_length=255), AfterValidator(_safe_relative)]
Flag = Annotated[str, Field(min_length=1, max_length=256)]
Points = Annotated[int, Field(ge=0, le=10_000)]
Seconds = Annotated[int, Field(ge=0, le=3_600)]
Retries = Annotated[int, Field(ge=0, le=100)]
Name = Annotated[str, Field(min_length=1, max_length=64)]


# question create / import row
class QuestionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: Code
    title: Title
    story: Story
    monument: Monument
    hint1: Hint | None = None
    hint2: Hint | None = None
    file_path: FilePath | None = None
    flag: Flag
    case_sensitive: bool = True
    is_final: bool = False
    enabled: bool = True
    base_points: Points
    min_points: Points = 0
    decay_interval_seconds: Seconds = 0
    decay_points: Points = 0
    retries: Retries = 3
    block_seconds: Seconds = 300

    @model_validator(mode="after")
    def _consistent(self) -> Self:
        if self.min_points > self.base_points:
            raise ValueError("min_points cannot exceed base_points")
        if self.hint2 and not self.hint1:
            raise ValueError("hint2 needs hint1")
        return self


# question partial edit
class QuestionUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: Title | None = None
    story: Story | None = None
    monument: Monument | None = None
    hint1: Hint | None = None
    hint2: Hint | None = None
    file_path: FilePath | None = None
    flag: Flag | None = None
    case_sensitive: bool | None = None
    is_final: bool | None = None
    enabled: bool | None = None
    base_points: Points | None = None
    min_points: Points | None = None
    decay_interval_seconds: Seconds | None = None
    decay_points: Points | None = None
    retries: Retries | None = None
    block_seconds: Seconds | None = None


# admin question list row
class QuestionSummary(BaseModel):
    question_id: uuid.UUID
    code: str
    title: str
    monument: str
    base_points: int
    current_points: int
    enabled: bool
    is_final: bool
    path_ids: list[int]


# full admin question
class QuestionAdminOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    question_id: uuid.UUID = Field(validation_alias=AliasChoices("question_id", "id"))
    code: str
    title: str
    story: str
    monument: str
    hint1: str | None
    hint2: str | None
    file_path: str | None
    flag: str
    case_sensitive: bool
    is_final: bool
    enabled: bool
    base_points: int
    min_points: int
    decay_interval_seconds: int
    decay_points: int
    retries: int
    block_seconds: int
    unlocked_at: LocalDatetime | None
    unlocked_by_team_id: int | None
    first_solved_at: LocalDatetime | None
    first_solved_by_team_id: int | None
    blocked_until: LocalDatetime | None
    blocked_by_team_id: int | None
    created_at: LocalDatetime
    path_ids: list[int] = []
    current_points: int = 0
    seconds_since_unlock: int | None = None
    next_drop_in_seconds: int | None = None


# path create / import row
class PathCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Name
    start_region: Name
    sort_order: int = 0
    question_codes: list[Code] = []


# path partial edit
class PathUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Name | None = None
    start_region: Name | None = None
    sort_order: int | None = None
    question_codes: list[Code] | None = None


# question slot on a path
class PathQuestionRef(BaseModel):
    position: int
    question_id: uuid.UUID
    code: str
    title: str


# admin path view
class PathAdminOut(BaseModel):
    path_id: int
    name: str
    start_region: str
    sort_order: int
    questions: list[PathQuestionRef]


# bulk import request
class ContentImport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    questions: list[QuestionCreate] = []
    paths: list[PathCreate] = []


# bulk import result
class ImportResult(BaseModel):
    questions_created: int = 0
    questions_updated: int = 0
    paths_created: int = 0
    paths_updated: int = 0
