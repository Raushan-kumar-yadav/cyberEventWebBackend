import uuid
from collections import defaultdict
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import utcnow
from app.models import Path, PathQuestion, Question
from app.schemas.content import (
    ContentImport,
    ImportResult,
    PathAdminOut,
    PathCreate,
    PathQuestionRef,
    QuestionAdminOut,
    QuestionCreate,
    QuestionSummary,
)
from app.services import game_clock, scoring

NULLABLE_QUESTION_FIELDS = {"hint1", "hint2", "file_path"}


def _invalid(detail: str) -> HTTPException:
    return HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail)


def _conflict(detail: str) -> HTTPException:
    return HTTPException(status.HTTP_409_CONFLICT, detail)


async def get_question(db: AsyncSession, question_id: uuid.UUID, lock: bool = False) -> Question:
    question = await db.get(Question, question_id, with_for_update=lock)
    if question is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Question not found")
    return question


async def get_path(db: AsyncSession, path_id: int, lock: bool = False) -> Path:
    path = await db.get(Path, path_id, with_for_update=lock)
    if path is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Path not found")
    return path


async def path_ids_by_question(
    db: AsyncSession, question_ids: list[uuid.UUID] | None = None
) -> dict[uuid.UUID, list[int]]:
    stmt = select(PathQuestion.question_id, PathQuestion.path_id).order_by(PathQuestion.path_id)
    if question_ids is not None:
        stmt = stmt.where(PathQuestion.question_id.in_(question_ids))
    grouped: dict[uuid.UUID, list[int]] = defaultdict(list)
    for question_id, path_id in await db.execute(stmt):
        grouped[question_id].append(path_id)
    return grouped


async def check_finals_last(db: AsyncSession) -> None:
    last = (
        select(PathQuestion.path_id, func.max(PathQuestion.position).label("last"))
        .group_by(PathQuestion.path_id)
        .subquery()
    )
    misplaced = await db.scalar(
        select(func.count())
        .select_from(PathQuestion)
        .join(Question, Question.id == PathQuestion.question_id)
        .join(last, last.c.path_id == PathQuestion.path_id)
        .where(Question.is_final, PathQuestion.position != last.c.last)
    )
    if misplaced:
        raise _invalid("the final question must be last on every path")


async def create_question(db: AsyncSession, data: QuestionCreate) -> Question:
    if await db.scalar(select(Question.id).where(Question.code == data.code)):
        raise _conflict("Question code already exists")
    question = Question(**data.model_dump())
    db.add(question)
    await db.flush()
    return question


async def update_question(db: AsyncSession, question: Question, changes: dict[str, Any]) -> None:
    for key, value in changes.items():
        if value is None and key not in NULLABLE_QUESTION_FIELDS:
            raise _invalid(f"{key} cannot be null")
        setattr(question, key, value)
    if question.min_points > question.base_points:
        raise _invalid("min_points cannot exceed base_points")
    if question.hint2 and not question.hint1:
        raise _invalid("hint2 needs hint1")
    if changes.get("is_final"):
        await check_finals_last(db)


async def create_path(db: AsyncSession, data: PathCreate) -> Path:
    if await db.scalar(select(Path.id).where(Path.name == data.name)):
        raise _conflict("Path name already exists")
    path = Path(name=data.name, start_region=data.start_region, sort_order=data.sort_order)
    db.add(path)
    await db.flush()
    await set_path_questions(db, path, data.question_codes)
    return path


async def rename_path(db: AsyncSession, path: Path, name: str) -> None:
    taken = await db.scalar(select(Path.id).where(Path.name == name, Path.id != path.id))
    if taken:
        raise _conflict("Path name already exists")
    path.name = name


async def set_path_questions(db: AsyncSession, path: Path, codes: list[str]) -> None:
    if len(set(codes)) != len(codes):
        raise _invalid("question_codes has duplicates")
    found = {q.code: q for q in await db.scalars(select(Question).where(Question.code.in_(codes)))}
    missing = [code for code in codes if code not in found]
    if missing:
        raise _invalid(f"unknown question codes: {', '.join(missing)}")
    await db.execute(delete(PathQuestion).where(PathQuestion.path_id == path.id))
    db.add_all(
        PathQuestion(path_id=path.id, position=position, question_id=found[code].id)
        for position, code in enumerate(codes)
    )
    await check_finals_last(db)


async def import_content(db: AsyncSession, data: ContentImport) -> ImportResult:
    codes = [item.code for item in data.questions]
    names = [item.name for item in data.paths]
    if len(set(codes)) != len(codes) or len(set(names)) != len(names):
        raise _invalid("duplicate question codes or path names in import")

    result = ImportResult()
    for item in data.questions:
        question = await db.scalar(select(Question).where(Question.code == item.code))
        if question is None:
            db.add(Question(**item.model_dump()))
            result.questions_created += 1
        else:
            for key, value in item.model_dump(exclude={"code"}).items():
                setattr(question, key, value)
            result.questions_updated += 1

    for item in data.paths:
        path = await db.scalar(select(Path).where(Path.name == item.name))
        if path is None:
            path = Path(name=item.name, start_region=item.start_region, sort_order=item.sort_order)
            db.add(path)
            await db.flush()
            result.paths_created += 1
        else:
            path.start_region = item.start_region
            path.sort_order = item.sort_order
            result.paths_updated += 1
        await set_path_questions(db, path, item.question_codes)

    await check_finals_last(db)
    return result


async def _active_now(db: AsyncSession) -> int:
    return game_clock.active_seconds(await game_clock.get_game(db), utcnow())


async def question_out(db: AsyncSession, question: Question) -> QuestionAdminOut:
    path_ids = (await path_ids_by_question(db, [question.id])).get(question.id, [])
    active = await _active_now(db)
    return QuestionAdminOut.model_validate(question).model_copy(
        update={
            "path_ids": path_ids,
            "current_points": scoring.current_points(question, active),
            "seconds_since_unlock": scoring.seconds_since_unlock(question, active),
            "next_drop_in_seconds": scoring.next_drop_in(question, active),
        }
    )


async def question_summaries(db: AsyncSession) -> list[QuestionSummary]:
    path_ids = await path_ids_by_question(db)
    active = await _active_now(db)
    return [
        QuestionSummary(
            question_id=q.id,
            code=q.code,
            title=q.title,
            monument=q.monument,
            base_points=q.base_points,
            current_points=scoring.current_points(q, active),
            enabled=q.enabled,
            is_final=q.is_final,
            path_ids=path_ids.get(q.id, []),
        )
        for q in await db.scalars(select(Question).order_by(Question.code))
    ]


async def path_out(db: AsyncSession, path: Path) -> PathAdminOut:
    rows = await db.execute(
        select(PathQuestion.position, Question.id, Question.code, Question.title)
        .join(Question, Question.id == PathQuestion.question_id)
        .where(PathQuestion.path_id == path.id)
        .order_by(PathQuestion.position)
    )
    return PathAdminOut(
        path_id=path.id,
        name=path.name,
        start_region=path.start_region,
        sort_order=path.sort_order,
        questions=[
            PathQuestionRef(position=position, question_id=qid, code=code, title=title)
            for position, qid, code, title in rows
        ],
    )


async def path_outs(db: AsyncSession) -> list[PathAdminOut]:
    paths = await db.scalars(select(Path).order_by(Path.sort_order, Path.id))
    return [await path_out(db, path) for path in paths]
