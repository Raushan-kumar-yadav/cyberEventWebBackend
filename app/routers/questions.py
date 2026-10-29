import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException, status
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse

from app.core.clock import utcnow
from app.core.config import settings
from app.deps import DB, CurrentTeam
from app.models.enums import GameStatus
from app.schemas.question import QuestionOut
from app.schemas.submission import SubmitIn, SubmitOut
from app.services import game_clock, questions, submissions

router = APIRouter(prefix="/question", tags=["questions"])

LIVE = (GameStatus.RUNNING, GameStatus.PAUSED)


@router.get("/{question_id}")
async def get_question(question_id: uuid.UUID, team: CurrentTeam, db: DB) -> QuestionOut:
    game = await game_clock.require_started(db)
    question, state, path_id = await questions.resolve(db, team, question_id)
    now = utcnow()
    live = game_clock.effective_status(game, now) in LIVE
    if path_id is not None and live and (state is None or question.unlocked_at is None):
        await questions.lock_team(db, team)
        state = await questions.ensure_state(db, team, question, now)
        question = await questions.unlock(db, question, team, game, now)
        await db.commit()
    active_now = game_clock.active_seconds(game, now)
    return questions.view(question, state, team.id, path_id, active_now, now)


def _locate(relative: str) -> Path | None:
    root = settings.files_dir.resolve()
    target = (root / relative).resolve()
    return target if target.is_relative_to(root) and target.is_file() else None


@router.get("/{question_id}/file")
async def download_file(question_id: uuid.UUID, team: CurrentTeam, db: DB) -> FileResponse:
    await game_clock.require_started(db)
    question, _, _ = await questions.resolve(db, team, question_id)
    target = await run_in_threadpool(_locate, question.file_path) if question.file_path else None
    if target is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "File not found")
    return FileResponse(target, filename=target.name)


@router.post("/save/{question_id}")
async def submit_flag(
    question_id: uuid.UUID, body: SubmitIn, team: CurrentTeam, db: DB
) -> SubmitOut:
    return await submissions.submit(db, team, question_id, body)
