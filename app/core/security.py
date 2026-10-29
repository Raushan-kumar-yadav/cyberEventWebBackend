from datetime import timedelta
from typing import Any, Literal

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from app.core.clock import utcnow
from app.core.config import settings

Role = Literal["team", "admin"]

_hasher = PasswordHasher()
# equal timeing
_DUMMY_HASH = _hasher.hash("dummy-password")


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, hashed: str | None) -> bool:
    try:
        _hasher.verify(hashed or _DUMMY_HASH, password)
    except (VerificationError, InvalidHashError):
        return False
    return hashed is not None


def create_token(role: Role, subject_id: int, session_version: int) -> str:
    now = utcnow()
    payload = {
        f"{role}_id": subject_id,
        "role": role,
        "sv": session_version,
        "iat": now,
        "exp": now + timedelta(seconds=settings.token_ttl_seconds),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict[str, Any] | None:
    try:
        return jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
            options={"require": ["role", "sv", "exp"]},
        )
    except jwt.PyJWTError:
        return None
