import uuid
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.models.enums import LedgerReason, PathEvent, QuestionEvent
from app.schemas.common import LocalDatetime


# leaderboard row
class LeaderboardRow(BaseModel):
    rank: int
    team_id: int
    team_name: str
    points: int
    has_reached_delhi: bool
    reached_delhi_at: LocalDatetime | None
    powerups_used: int
    playthroughs: int


# team row for admin lists
class TeamSummary(BaseModel):
    team_id: int
    team_name: str
    username: str
    points: int
    current_path_id: int | None
    current_question_id: uuid.UUID | None
    frozen_until: LocalDatetime | None
    has_reached_delhi: bool
    playthroughs: int
    powerups_used: int


# question state on the admin map
class MapQuestion(BaseModel):
    question_id: uuid.UUID
    code: str
    title: str
    enabled: bool
    base_points: int
    current_points: int
    unlocked_at: LocalDatetime | None
    unlocked_by_team_id: int | None
    seconds_since_unlock: int | None
    next_drop_in_seconds: int | None
    first_solved_by_team_id: int | None
    blocked_until: LocalDatetime | None
    blocked_by_team_id: int | None


# admin map
class AdminMapOut(BaseModel):
    teams: list[TeamSummary]
    questions: list[MapQuestion]


# route event
class PathEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    path_id: int
    question_id: uuid.UUID | None
    event: PathEvent
    at: LocalDatetime


# question event
class TeamLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    team_id: int
    question_id: uuid.UUID | None
    event: QuestionEvent
    meta: dict[str, Any]
    created_at: LocalDatetime


# point change
class LedgerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    delta: int
    balance_after: int
    reason: LedgerReason
    question_id: uuid.UUID | None
    admin_id: int | None
    note: str | None
    created_at: LocalDatetime


# full team view
class TeamDetailOut(TeamSummary):
    map: list[PathEventOut]
    logs: list[TeamLogOut]
    ledger: list[LedgerOut]


# admin action
class AuditOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    admin_id: int | None
    action: str
    target: str | None
    payload: dict[str, Any]
    created_at: LocalDatetime


# frozen results
class FinalLeaderboardOut(BaseModel):
    id: int
    created_at: LocalDatetime
    rows: list[LeaderboardRow]
