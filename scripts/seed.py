import argparse
import asyncio
import json
import sys
from pathlib import Path

from fastapi import HTTPException
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import utcnow
from app.core.db import SessionLocal, engine
from app.core.security import hash_password, verify_password
from app.models import (
    Admin,
    FinalLeaderboard,
    PointLedger,
    Question,
    Team,
    TeamLog,
    TeamPathEvent,
    TeamQuestionState,
)
from app.models.enums import GameStatus
from app.schemas.admin import TeamCreate, TeamUpdate
from app.schemas.content import ContentImport
from app.services import content, game_clock, teams


# admin account
class AdminSeed(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    passcode: str = Field(min_length=8, max_length=128)


# seed file
class SeedFile(ContentImport):
    admins: list[AdminSeed] = []
    teams: list[TeamCreate] = []


async def seed_admins(db: AsyncSession, admins: list[AdminSeed]) -> None:
    for item in admins:
        admin = await db.scalar(select(Admin).where(Admin.name == item.name))
        if admin is None:
            db.add(Admin(name=item.name, passcode_hash=hash_password(item.passcode)))
        elif not verify_password(item.passcode, admin.passcode_hash):
            admin.passcode_hash = hash_password(item.passcode)
            admin.session_version += 1


async def seed_teams(db: AsyncSession, items: list[TeamCreate]) -> None:
    for item in items:
        team = await db.scalar(select(Team).where(Team.username == item.username))
        if team is None:
            await teams.create_team(db, item)
            continue
        # same password keeps the team logged in
        same = verify_password(item.password, team.password_hash)
        teams.update_team(
            team, TeamUpdate(name=item.name, password=None if same else item.password)
        )


async def reset_progress(db: AsyncSession) -> None:
    game = await game_clock.get_game(db, lock=True)
    if game_clock.effective_status(game, utcnow()) in (GameStatus.RUNNING, GameStatus.PAUSED):
        raise SystemExit("Game is live, end it before resetting")

    for model in (TeamQuestionState, PointLedger, TeamLog, TeamPathEvent, FinalLeaderboard):
        await db.execute(delete(model))
    await db.execute(
        update(Team).values(
            points=0,
            powerups_used=0,
            playthroughs=0,
            has_reached_delhi=False,
            reached_delhi_at=None,
            current_path_id=None,
            switch_from_path_id=None,
            frozen_until=None,
        )
    )
    await db.execute(
        update(Question).values(
            unlocked_at=None,
            unlocked_game_seconds=None,
            unlocked_by_team_id=None,
            first_solved_at=None,
            first_solved_by_team_id=None,
            blocked_until=None,
            blocked_by_team_id=None,
        )
    )
    game.status = GameStatus.NOT_STARTED
    game.start_at = game.end_at = game.paused_at = None
    game.paused_seconds = 0
    game.version += 1


async def run(data: SeedFile | None, reset: bool) -> None:
    async with SessionLocal() as db:
        if reset:
            await reset_progress(db)
            print("Game progress reset")
        if data is not None:
            await seed_admins(db, data.admins)
            await seed_teams(db, data.teams)
            result = await content.import_content(
                db, ContentImport(questions=data.questions, paths=data.paths)
            )
            await game_clock.get_game(db)
            print(f"Admins: {len(data.admins)}, teams: {len(data.teams)}")
            print(result.model_dump())
        await db.commit()
    await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description="Load seed data or reset game progress")
    parser.add_argument("file", nargs="?", type=Path, help="seed JSON file")
    parser.add_argument("--reset", action="store_true", help="wipe game progress first")
    args = parser.parse_args()
    if args.file is None and not args.reset:
        parser.error("give a seed file, --reset, or both")

    try:
        data = None
        if args.file is not None:
            data = SeedFile.model_validate(json.loads(args.file.read_text(encoding="utf-8")))
        asyncio.run(run(data, args.reset))
    except (OSError, ValueError, ValidationError) as error:
        sys.exit(f"Seed failed: {error}")
    except HTTPException as error:
        sys.exit(f"Seed failed: {error.detail}")


if __name__ == "__main__":
    main()
