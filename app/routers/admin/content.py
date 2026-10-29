import uuid

from fastapi import APIRouter, status

from app.deps import DB, CurrentAdmin
from app.schemas.content import (
    ContentImport,
    ImportResult,
    PathAdminOut,
    PathCreate,
    PathUpdate,
    QuestionAdminOut,
    QuestionCreate,
    QuestionSummary,
    QuestionUpdate,
)
from app.services import audit, content

router = APIRouter()


@router.get("/question/details")
async def list_questions(admin: CurrentAdmin, db: DB) -> list[QuestionSummary]:
    return await content.question_summaries(db)


@router.get("/question/{question_id}")
async def get_question(question_id: uuid.UUID, admin: CurrentAdmin, db: DB) -> QuestionAdminOut:
    return await content.question_out(db, await content.get_question(db, question_id))


@router.post("/question", status_code=status.HTTP_201_CREATED)
async def create_question(body: QuestionCreate, admin: CurrentAdmin, db: DB) -> QuestionAdminOut:
    question = await content.create_question(db, body)
    audit.record(db, admin.id, "question_create", body.code)
    await db.commit()
    return await content.question_out(db, question)


@router.patch("/question/{question_id}")
async def update_question(
    question_id: uuid.UUID, body: QuestionUpdate, admin: CurrentAdmin, db: DB
) -> QuestionAdminOut:
    question = await content.get_question(db, question_id, lock=True)
    changes = body.model_dump(exclude_unset=True)
    await content.update_question(db, question, changes)
    # field names only, never the flag
    audit.record(db, admin.id, "question_update", question.code, fields=sorted(changes))
    await db.commit()
    return await content.question_out(db, question)


@router.get("/path/details")
async def list_paths(admin: CurrentAdmin, db: DB) -> list[PathAdminOut]:
    return await content.path_outs(db)


@router.post("/path", status_code=status.HTTP_201_CREATED)
async def create_path(body: PathCreate, admin: CurrentAdmin, db: DB) -> PathAdminOut:
    path = await content.create_path(db, body)
    audit.record(db, admin.id, "path_create", body.name, question_codes=body.question_codes)
    await db.commit()
    return await content.path_out(db, path)


@router.patch("/path/{path_id}")
async def update_path(path_id: int, body: PathUpdate, admin: CurrentAdmin, db: DB) -> PathAdminOut:
    path = await content.get_path(db, path_id, lock=True)
    changes = body.model_dump(exclude_unset=True)
    if changes.get("name") is not None:
        await content.rename_path(db, path, changes["name"])
    if changes.get("start_region") is not None:
        path.start_region = changes["start_region"]
    if changes.get("sort_order") is not None:
        path.sort_order = changes["sort_order"]
    if changes.get("question_codes") is not None:
        await content.set_path_questions(db, path, changes["question_codes"])
    audit.record(db, admin.id, "path_update", path.name, **changes)
    await db.commit()
    return await content.path_out(db, path)


@router.post("/import")
async def import_content(body: ContentImport, admin: CurrentAdmin, db: DB) -> ImportResult:
    result = await content.import_content(db, body)
    audit.record(db, admin.id, "content_import", None, **result.model_dump())
    await db.commit()
    return result
