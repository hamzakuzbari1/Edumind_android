from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import require_role
from app.db.session import get_db
from app.models.user import User, UserRole
from app.schemas.planner import PlannerVisibilityOut
from app.schemas.teacher_students import (
    TeacherStudentNoteCreateIn,
    TeacherStudentNoteOut,
    TeacherStudentNoteUpdateIn,
    TeacherStudentProfileOut,
    TeacherStudentSearchOut,
)
from app.services import teacher_student_service
from app.services import parent_note_service
from app.schemas.parent_notes import (
    ParentNoteCategoryOptionOut,
    ParentNoteCreateIn,
    ParentNoteListOut,
    ParentNoteOut,
    ParentNotePriorityOptionOut,
    ParentNoteReplyCreateIn,
    ParentNoteReplyUpdateIn,
    ParentNoteStatusOptionOut,
    ParentNoteUpdateIn,
)

router = APIRouter(prefix="/teacher/students", tags=["Teacher Students"])


@router.get("", response_model=TeacherStudentSearchOut)
async def search_students(
    q: str | None = Query(None, description="Partial match on name or email"),
    grade: int | None = Query(None, ge=1, le=12),
    subject_id: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
    teacher: User = Depends(require_role(UserRole.teacher)),
):
    return await teacher_student_service.search_teacher_students(
        db, teacher, q=q, grade=grade, subject_id=subject_id
    )


@router.get("/parent-notes/categories", response_model=list[ParentNoteCategoryOptionOut])
async def parent_note_categories(
    teacher: User = Depends(require_role(UserRole.teacher)),
):
    return parent_note_service.list_category_options()


@router.get("/parent-notes/priorities", response_model=list[ParentNotePriorityOptionOut])
async def parent_note_priorities(
    teacher: User = Depends(require_role(UserRole.teacher)),
):
    return parent_note_service.list_priority_options()


@router.get("/parent-notes/statuses", response_model=list[ParentNoteStatusOptionOut])
async def parent_note_statuses(
    teacher: User = Depends(require_role(UserRole.teacher)),
):
    return parent_note_service.list_status_options()


@router.get("/{student_id}", response_model=TeacherStudentProfileOut)
async def student_profile(
    student_id: int,
    db: AsyncSession = Depends(get_db),
    teacher: User = Depends(require_role(UserRole.teacher)),
):
    return await teacher_student_service.get_teacher_student_profile(db, teacher, student_id)


@router.get("/{student_id}/planner", response_model=PlannerVisibilityOut)
async def student_planner_visibility(
    student_id: int,
    db: AsyncSession = Depends(get_db),
    teacher: User = Depends(require_role(UserRole.teacher)),
):
    await teacher_student_service.assert_student_in_teacher_scope(db, teacher, student_id)
    data = await teacher_student_service.get_teacher_scoped_planner_visibility(db, teacher, student_id)
    return PlannerVisibilityOut(**data)


@router.get("/{student_id}/notes", response_model=list[TeacherStudentNoteOut])
async def list_notes(
    student_id: int,
    db: AsyncSession = Depends(get_db),
    teacher: User = Depends(require_role(UserRole.teacher)),
):
    return await teacher_student_service.list_teacher_notes(db, teacher, student_id)


@router.post("/{student_id}/notes", response_model=TeacherStudentNoteOut, status_code=201)
async def create_note(
    student_id: int,
    body: TeacherStudentNoteCreateIn,
    db: AsyncSession = Depends(get_db),
    teacher: User = Depends(require_role(UserRole.teacher)),
):
    return await teacher_student_service.create_teacher_note(db, teacher, student_id, body.note_text)


@router.patch("/{student_id}/notes/{note_id}", response_model=TeacherStudentNoteOut)
async def update_note(
    student_id: int,
    note_id: int,
    body: TeacherStudentNoteUpdateIn,
    db: AsyncSession = Depends(get_db),
    teacher: User = Depends(require_role(UserRole.teacher)),
):
    return await teacher_student_service.update_teacher_note(
        db, teacher, student_id, note_id, body.note_text
    )


@router.delete("/{student_id}/notes/{note_id}", status_code=204)
async def delete_note(
    student_id: int,
    note_id: int,
    db: AsyncSession = Depends(get_db),
    teacher: User = Depends(require_role(UserRole.teacher)),
):
    await teacher_student_service.delete_teacher_note(db, teacher, student_id, note_id)


@router.get("/{student_id}/parent-notes", response_model=ParentNoteListOut)
async def list_parent_notes(
    student_id: int,
    limit: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    teacher: User = Depends(require_role(UserRole.teacher)),
):
    return await parent_note_service.list_teacher_parent_notes(db, teacher, student_id, limit=limit)


@router.post("/{student_id}/parent-notes", response_model=ParentNoteOut, status_code=201)
async def create_parent_note(
    student_id: int,
    body: ParentNoteCreateIn,
    db: AsyncSession = Depends(get_db),
    teacher: User = Depends(require_role(UserRole.teacher)),
):
    return await parent_note_service.create_parent_note(db, teacher, student_id, body)


@router.patch("/{student_id}/parent-notes/{note_id}", response_model=ParentNoteOut)
async def update_parent_note(
    student_id: int,
    note_id: int,
    body: ParentNoteUpdateIn,
    db: AsyncSession = Depends(get_db),
    teacher: User = Depends(require_role(UserRole.teacher)),
):
    return await parent_note_service.update_parent_note(db, teacher, student_id, note_id, body)


@router.delete("/{student_id}/parent-notes/{note_id}", status_code=204)
async def delete_parent_note(
    student_id: int,
    note_id: int,
    db: AsyncSession = Depends(get_db),
    teacher: User = Depends(require_role(UserRole.teacher)),
):
    await parent_note_service.delete_parent_note(db, teacher, student_id, note_id)


@router.get("/{student_id}/parent-notes/{note_id}", response_model=ParentNoteOut)
async def get_parent_note(
    student_id: int,
    note_id: int,
    db: AsyncSession = Depends(get_db),
    teacher: User = Depends(require_role(UserRole.teacher)),
):
    return await parent_note_service.get_teacher_parent_note(db, teacher, student_id, note_id)


@router.post("/{student_id}/parent-notes/{note_id}/close", response_model=ParentNoteOut)
async def close_parent_note(
    student_id: int,
    note_id: int,
    db: AsyncSession = Depends(get_db),
    teacher: User = Depends(require_role(UserRole.teacher)),
):
    return await parent_note_service.close_parent_note(db, teacher, student_id, note_id)


@router.post("/{student_id}/parent-notes/{note_id}/reply", response_model=ParentNoteOut)
async def reply_parent_note(
    student_id: int,
    note_id: int,
    body: ParentNoteReplyCreateIn,
    db: AsyncSession = Depends(get_db),
    teacher: User = Depends(require_role(UserRole.teacher)),
):
    return await parent_note_service.create_note_reply(
        db, teacher, note_id, body, student_id=student_id
    )


@router.patch("/{student_id}/parent-notes/{note_id}/replies/{reply_id}", response_model=ParentNoteOut)
async def update_parent_note_reply(
    student_id: int,
    note_id: int,
    reply_id: int,
    body: ParentNoteReplyUpdateIn,
    db: AsyncSession = Depends(get_db),
    teacher: User = Depends(require_role(UserRole.teacher)),
):
    return await parent_note_service.update_note_reply(
        db, teacher, note_id, reply_id, body, student_id=student_id
    )


@router.delete("/{student_id}/parent-notes/{note_id}/replies/{reply_id}", response_model=ParentNoteOut)
async def delete_parent_note_reply(
    student_id: int,
    note_id: int,
    reply_id: int,
    db: AsyncSession = Depends(get_db),
    teacher: User = Depends(require_role(UserRole.teacher)),
):
    return await parent_note_service.delete_note_reply(
        db, teacher, note_id, reply_id, student_id=student_id
    )
