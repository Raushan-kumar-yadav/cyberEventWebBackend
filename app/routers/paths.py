from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.core.clock import utcnow
from app.deps import DB, CurrentTeam
from app.models import Path
from app.models.enums import GameStatus
from app.schemas.path import CurrentPathOut, PathOut, PathQuestionOut
from app.services import content, game_clock, progression

router = APIRouter(tags=["paths"])


@router.get("/paths")
async def list_paths(team: CurrentTeam, db: DB) -> list[PathOut]:
    game = await game_clock.get_game(db)
    started = game.status != GameStatus.NOT_STARTED
    done = await progression.done_question_ids(db, team.id)
    by_path = await progression.enabled_questions_by_path(db)

    paths = []
    for path in await db.scalars(select(Path).order_by(Path.sort_order, Path.id)):
        ordered = by_path.get(path.id, [])
        upcoming = progression.next_question(ordered, done)
        # locked teams only see ids on their own path
        visible = started and team.current_path_id in (None, path.id)
        paths.append(
            PathOut(
                path_id=path.id,
                name=path.name,
                start_region=path.start_region,
                question_count=len(ordered),
                completed=upcoming is None,
                is_current=team.current_path_id == path.id,
                current_question_id=upcoming if visible else None,
            )
        )
    return paths


@router.get("/path/current")
async def current_path(team: CurrentTeam) -> CurrentPathOut:
    frozen = progression.frozen_until(team, utcnow())
    return CurrentPathOut(
        path_id=team.current_path_id,
        switch_from_path_id=team.switch_from_path_id if frozen else None,
        frozen_until=frozen,
    )


@router.get("/path/{path_id}/current/question")
async def path_current_question(path_id: int, team: CurrentTeam, db: DB) -> PathQuestionOut:
    await game_clock.require_started(db)
    await content.get_path(db, path_id)
    if team.current_path_id not in (None, path_id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Team is on another path")
    question_id = await progression.current_question_id(db, team, path_id)
    return PathQuestionOut(path_id=path_id, question_id=question_id, completed=question_id is None)
