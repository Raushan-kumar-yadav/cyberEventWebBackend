from fastapi import APIRouter, HTTPException, Request, Response, status
from sqlalchemy import select

from app.core.clock import utcnow
from app.core.cookies import clear_auth_cookie, set_auth_cookie
from app.core.ratelimit import login_limiter
from app.core.security import create_token, verify_password
from app.deps import DB, CurrentTeam
from app.models import Team
from app.schemas.team import TeamLogin, TeamMe, TeamSession
from app.services import progression

router = APIRouter(prefix="/team", tags=["team"])


@router.post("/login")
async def login(body: TeamLogin, request: Request, response: Response, db: DB) -> TeamSession:
    client = request.client.host if request.client else "unknown"
    login_limiter.hit(f"team:{client}:{body.username}")

    team = await db.scalar(select(Team).where(Team.username == body.username))
    valid = verify_password(body.password, team.password_hash if team else None)
    if team is None or not valid:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid username or password")

    # newest login works
    team.session_version += 1
    await db.commit()
    set_auth_cookie(response, "team", create_token("team", team.id, team.session_version))
    return TeamSession(team_id=team.id, team_name=team.name)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(team: CurrentTeam, response: Response, db: DB) -> None:
    team.session_version += 1
    await db.commit()
    clear_auth_cookie(response, "team")


@router.get("/me")
async def me(team: CurrentTeam) -> TeamMe:
    frozen = progression.frozen_until(team, utcnow())
    return TeamMe(
        team_id=team.id,
        team_name=team.name,
        points=team.points,
        powerups_used=team.powerups_used,
        playthroughs=team.playthroughs,
        has_reached_delhi=team.has_reached_delhi,
        current_path_id=team.current_path_id,
        frozen_until=frozen,
    )
