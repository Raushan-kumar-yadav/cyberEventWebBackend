from typing import Any

from fastapi import Response

from app.core.config import settings
from app.core.security import Role

TEAM_COOKIE = "team_token"
ADMIN_COOKIE = "admin_token"

_NAMES: dict[Role, str] = {"team": TEAM_COOKIE, "admin": ADMIN_COOKIE}


def _options(role: Role) -> dict[str, Any]:
    prefix = settings.api_prefix
    return {
        # admin cookie  
        "path": f"{prefix}/admin" if role == "admin" else f"{prefix}/",
        "secure": settings.cookie_secure,
        "httponly": True,
        "samesite": "strict",
    }


def set_auth_cookie(response: Response, role: Role, token: str) -> None:
    response.set_cookie(_NAMES[role], token, max_age=settings.token_ttl_seconds, **_options(role))


def clear_auth_cookie(response: Response, role: Role) -> None:
    response.delete_cookie(_NAMES[role], **_options(role))
