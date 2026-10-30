from pydantic import BaseModel, ConfigDict, Field


# admin login request
class AdminLogin(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    passcode: str = Field(min_length=1, max_length=128)


# admin session
class AdminSession(BaseModel):
    admin_id: int
    admin_name: str


# new team login
class TeamCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=6, max_length=128)


# team edit, new password logs the team out
class TeamUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=128)
    password: str | None = Field(default=None, min_length=6, max_length=128)


# manual point change
class PointsAdjust(BaseModel):
    model_config = ConfigDict(extra="forbid")

    delta: int = Field(ge=-10_000, le=10_000)
    reason: str = Field(min_length=1, max_length=255)
