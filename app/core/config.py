from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    env: Literal["dev", "prod"] = "dev"
    api_prefix: str = ""
    database_url: str = "postgresql+asyncpg://ctf:ctf@localhost:5432/ctf"

    jwt_secret: str = Field(min_length=32)
    jwt_algorithm: str = "HS256"
    token_ttl_seconds: int = 4 * 60 * 60
    login_attempts_per_minute: int = 10
    submit_attempts_per_minute: int = 10

    cookie_secure: bool = True
    frontend_origins: list[str] = []

    timezone: str = "Asia/Kolkata"
    game_duration_minutes: int = 120
    files_dir: Path = Path("files")

    @field_validator("api_prefix")
    @classmethod
    def _strip_prefix(cls, value: str) -> str:
        value = value.strip().rstrip("/")
        return f"/{value.lstrip('/')}" if value else ""

    @property
    def docs_enabled(self) -> bool:
        return self.env == "dev"


settings = Settings()
