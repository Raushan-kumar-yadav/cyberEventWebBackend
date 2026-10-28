from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from app.core.config import settings

LOCAL_TZ = ZoneInfo(settings.timezone)


def utcnow() -> datetime:
    return datetime.now(UTC)


def to_local(value: datetime) -> datetime:
    return value.astimezone(LOCAL_TZ)
