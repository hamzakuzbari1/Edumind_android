from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, require_role
from app.db.session import get_db
from app.models.user import User, UserRole
from app.schemas.messaging import (
    ConversationCreateIn,
    ConversationDetailOut,
    ConversationListOut,
    ConversationMessageOut,
    ConversationOut,
    MessageCreateIn,
    MessageSearchOut,
    MessagingContactsOut,
    MessagingThreadContextOut,
    ParticipantSettingsIn,
    ThreadParticipantsUpdateIn,
)
from app.services import messaging_context_service, messaging_service

router = APIRouter(prefix="/messages", tags=["Messages"])


@router.get("/conversations", response_model=ConversationListOut)
async def list_conversations(
    include_archived: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await messaging_service.list_conversations(db, user, include_archived=include_archived)


@router.get("/conversations/unread-count")
async def conversations_unread_count(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    count = await messaging_service.total_unread_count(db, user)
    return {"unread_count": count}


@router.get("/conversations/{thread_id}", response_model=ConversationDetailOut)
async def get_conversation(
    thread_id: int,
    mark_read: bool = Query(True),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await messaging_service.get_conversation(db, user, thread_id, mark_read=mark_read)


@router.get("/conversations/{thread_id}/context", response_model=MessagingThreadContextOut)
async def get_conversation_context(
    thread_id: int,
    db: AsyncSession = Depends(get_db),
    teacher: User = Depends(require_role(UserRole.teacher)),
):
    return await messaging_context_service.get_thread_context(db, teacher, thread_id)


@router.get("/conversations/{thread_id}/messages/search", response_model=MessageSearchOut)
async def search_conversation_messages(
    thread_id: int,
    q: str = Query(..., min_length=1, max_length=200),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await messaging_service.search_messages(db, user, thread_id, query=q)


@router.patch("/conversations/{thread_id}/settings", response_model=ConversationOut)
async def patch_conversation_settings(
    thread_id: int,
    body: ParticipantSettingsIn,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await messaging_service.update_participant_settings(db, user, thread_id, body)


@router.post("/conversations/{thread_id}/mark-unread", response_model=ConversationOut)
async def mark_conversation_unread(
    thread_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await messaging_service.mark_thread_unread(db, user, thread_id)


@router.patch("/conversations/{thread_id}/participants", response_model=ConversationDetailOut)
async def patch_conversation_participants(
    thread_id: int,
    body: ThreadParticipantsUpdateIn,
    db: AsyncSession = Depends(get_db),
    teacher: User = Depends(require_role(UserRole.teacher)),
):
    return await messaging_service.update_thread_participants(db, teacher, thread_id, body)


@router.post("/conversations", response_model=ConversationDetailOut, status_code=201)
async def create_conversation(
    body: ConversationCreateIn,
    db: AsyncSession = Depends(get_db),
    teacher: User = Depends(require_role(UserRole.teacher)),
):
    return await messaging_service.create_conversation(db, teacher, body)


@router.get("/contacts", response_model=MessagingContactsOut)
async def teacher_contacts(
    db: AsyncSession = Depends(get_db),
    teacher: User = Depends(require_role(UserRole.teacher)),
):
    return await messaging_service.list_teacher_contacts(db, teacher)


@router.post("/conversations/{thread_id}/messages", response_model=ConversationDetailOut)
async def post_message(
    thread_id: int,
    body: MessageCreateIn,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await messaging_service.send_message(db, user, thread_id, body)


@router.post("/conversations/{thread_id}/messages/attachment", response_model=ConversationDetailOut)
async def post_message_attachment(
    thread_id: int,
    file: UploadFile = File(...),
    caption: str = Form(""),
    voice_duration_ms: int | None = Form(None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    content = await file.read()
    return await messaging_service.send_message_with_attachment(
        db,
        user,
        thread_id,
        file_content=content,
        filename=file.filename or "file",
        mime_type=file.content_type or "application/octet-stream",
        caption=caption,
        voice_duration_ms=voice_duration_ms,
    )


@router.delete("/messages/{message_id}", response_model=ConversationMessageOut)
async def delete_message(
    message_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await messaging_service.delete_message(db, user, message_id)


@router.post("/conversations/{thread_id}/read")
async def mark_conversation_read(
    thread_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await messaging_service.mark_thread_read(db, user, thread_id)
    await db.commit()
    return {"ok": True}


@router.post("/messages/{message_id}/read", response_model=ConversationMessageOut)
async def mark_message_read(
    message_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await messaging_service.mark_message_read(db, user, message_id)
