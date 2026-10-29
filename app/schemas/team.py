from pydantic import BaseModel, Field

from app.schemas.common import LocalDatetime


# login request
class TeamLogin(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)


# login response
class TeamSession(BaseModel):
    team_id: int
    team_name: str


# team standing
class TeamMe(BaseModel):
    team_id: int
    team_name: str
    points: int
    powerups_used: int
    playthroughs: int
    has_reached_delhi: bool
    current_path_id: int | None
    frozen_until: LocalDatetime | None
