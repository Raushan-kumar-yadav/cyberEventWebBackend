from fastapi import APIRouter, HTTPException, Request, Response, status
from sqlalchemy import select

from app.core.cookies import clear_auth_cookie, set_auth_cookie
from app.core.ratelimit import login_limiter
from app.core.security import create_token, verify_password
from app.deps import DB, CurrentAdmin
from app.models import Admin
from app.schemas.admin import AdminLogin, AdminSession
from app.services import audit

router = APIRouter()


@router.post("/login")
async def login(body: AdminLogin, request: Request, response: Response, db: DB) -> AdminSession:
    client = request.client.host if request.client else "unknown"
    login_limiter.hit(f"admin:{client}:{body.name}")

    admin = await db.scalar(select(Admin).where(Admin.name == body.name))
    valid = verify_password(body.passcode, admin.passcode_hash if admin else None)
    if admin is None or not valid:
        audit.record(db, None, "login_failed", body.name, ip=client)
        await db.commit()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid name or passcode")

    # multi screen
    audit.record(db, admin.id, "login", ip=client)
    await db.commit()
    set_auth_cookie(response, "admin", create_token("admin", admin.id, admin.session_version))
    return AdminSession(admin_id=admin.id, admin_name=admin.name)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(admin: CurrentAdmin, response: Response, db: DB) -> None:
    admin.session_version += 1
    audit.record(db, admin.id, "logout")
    await db.commit()
    clear_auth_cookie(response, "admin")


@router.get("/me")
async def me(admin: CurrentAdmin) -> AdminSession:
    return AdminSession(admin_id=admin.id, admin_name=admin.name)
