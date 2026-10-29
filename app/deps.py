from typing import Annotated

from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cookies import ADMIN_COOKIE, TEAM_COOKIE
from app.core.db import get_db
from app.core.security import Role, decode_token
from app.models import Admin, Team

DB = Annotated[AsyncSession, Depends(get_db)]


def _unauthorized() -> HTTPException:
    return HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")


def _claims(token: str | None, role: Role) -> tuple[int, int]:
    payload = decode_token(token) if token else None
    if payload is None or payload["role"] != role:
        raise _unauthorized()
    subject_id, session_version = payload.get(f"{role}_id"), payload["sv"]
    if not isinstance(subject_id, int) or not isinstance(session_version, int):
        raise _unauthorized()
    return subject_id, session_version


async def current_team(
    db: DB, token: Annotated[str | None, Cookie(alias=TEAM_COOKIE)] = None
) -> Team:
    team_id, session_version = _claims(token, "team")
    team = await db.get(Team, team_id)
    if team is None or team.session_version != session_version:
        raise _unauthorized()
    return team


async def current_admin(
    db: DB, token: Annotated[str | None, Cookie(alias=ADMIN_COOKIE)] = None
) -> Admin:
    admin_id, session_version = _claims(token, "admin")
    admin = await db.get(Admin, admin_id)
    if admin is None or admin.session_version != session_version:
        raise _unauthorized()
    return admin


CurrentTeam = Annotated[Team, Depends(current_team)]
CurrentAdmin = Annotated[Admin, Depends(current_admin)]
