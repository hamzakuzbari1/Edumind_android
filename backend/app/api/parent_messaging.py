from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import require_parent_viewer
from app.db.session import get_db
from app.models.user import User
from app.schemas.parent_messaging import (
    ParentMessagingSummaryOut,
    ParentTeacherChatOpenIn,
    ParentTeacherChatOpenOut,
    ParentTeachersListOut,
)
from app.services import parent_messaging_service

router = APIRouter(prefix="/parent/messaging", tags=["Parent Messaging"])


@router.get("/teachers", response_model=ParentTeachersListOut)
async def list_child_teachers(
    parent: User = Depends(require_parent_viewer()),
    db: AsyncSession = Depends(get_db),
):
    return await parent_messaging_service.list_parent_teacher_contacts(db, parent)


@router.get("/summary", response_model=ParentMessagingSummaryOut)
async def messaging_summary(
    parent: User = Depends(require_parent_viewer()),
    db: AsyncSession = Depends(get_db),
):
    return await parent_messaging_service.parent_messaging_summary(db, parent)


@router.post(
    "/teachers/{teacher_id}/open-chat",
    response_model=ParentTeacherChatOpenOut,
)
async def open_teacher_chat(
    teacher_id: int,
    body: ParentTeacherChatOpenIn,
    parent: User = Depends(require_parent_viewer()),
    db: AsyncSession = Depends(get_db),
):
    return await parent_messaging_service.open_parent_teacher_chat(
        db,
        parent,
        teacher_id,
        student_id=body.student_id,
        course_id=body.course_id,
    )
