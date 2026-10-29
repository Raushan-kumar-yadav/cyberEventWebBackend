from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AdminAudit


def record(
    db: AsyncSession, admin_id: int | None, action: str, target: str | None = None, **payload: Any
) -> None:
    db.add(AdminAudit(admin_id=admin_id, action=action, target=target, payload=payload))
