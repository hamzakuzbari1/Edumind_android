"""Teacher AI voice profile — teacher-level, not tied to lessons."""

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import require_role
from app.db.session import get_db
from app.models.user import User, UserRole
from app.schemas.teacher_voice import (
    TeacherVoiceProfileOut,
    TeacherVoiceSampleOut,
    VoicePreviewIn,
    VoicePreviewOut,
)
from app.services import teacher_voice_service

router = APIRouter(prefix="/teacher", tags=["Teacher Voice Profile"])


@router.get("/voice-profile", response_model=TeacherVoiceProfileOut)
async def get_voice_profile(
    db: AsyncSession = Depends(get_db),
    teacher: User = Depends(require_role(UserRole.teacher)),
):
    return await teacher_voice_service.list_voice_samples(db, teacher)


@router.get("/voice-sample", response_model=TeacherVoiceSampleOut)
async def get_voice_sample_status(
    db: AsyncSession = Depends(get_db),
    teacher: User = Depends(require_role(UserRole.teacher)),
):
    return await teacher_voice_service.get_voice_sample_status(db, teacher)


@router.post("/voice-sample", response_model=TeacherVoiceSampleOut)
async def upload_voice_sample(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    teacher: User = Depends(require_role(UserRole.teacher)),
):
    data = await file.read()
    return await teacher_voice_service.upload_voice_sample(
        db, teacher, data, file.filename or "voice-sample.webm"
    )


@router.post("/voice-samples/{sample_id}/regenerate", response_model=TeacherVoiceSampleOut)
async def regenerate_voice_sample(
    sample_id: int,
    db: AsyncSession = Depends(get_db),
    teacher: User = Depends(require_role(UserRole.teacher)),
):
    return await teacher_voice_service.regenerate_voice_sample(db, teacher, sample_id)


@router.delete("/voice-samples/{sample_id}", response_model=TeacherVoiceProfileOut)
async def delete_voice_sample(
    sample_id: int,
    db: AsyncSession = Depends(get_db),
    teacher: User = Depends(require_role(UserRole.teacher)),
):
    return await teacher_voice_service.delete_voice_sample(db, teacher, sample_id)


@router.post("/voice-samples/{sample_id}/preview", response_model=VoicePreviewOut)
async def preview_voice_sample(
    sample_id: int,
    body: VoicePreviewIn,
    db: AsyncSession = Depends(get_db),
    teacher: User = Depends(require_role(UserRole.teacher)),
):
    return await teacher_voice_service.preview_voice_sample(db, teacher, sample_id, body.text)
