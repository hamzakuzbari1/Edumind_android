"""Teacher voice sample upload, validation, and AI processing."""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.catalog import TeacherProfile
from app.models.teacher_voice import TeacherVoiceSample, VoiceSampleStatus
from app.models.user import User
from app.services.elevenlabs_service import create_voice_clone, delete_voice
from app.services.teacher_setup_service import get_or_create_teacher_profile
from app.services.voice_service import build_persona_prompt, transcribe_audio
from app.services.voice_validation_service import validate_voice_sample

logger = logging.getLogger(__name__)
settings = get_settings()

_running: set[int] = set()

STATUS_LABELS = {
    VoiceSampleStatus.pending.value: "جاري معالجة الصوت",
    VoiceSampleStatus.processing.value: "جاري معالجة الصوت",
    VoiceSampleStatus.ready.value: "تم تجهيز الصوت للذكاء الاصطناعي",
    VoiceSampleStatus.failed.value: "فشل التحليل",
}


def _voice_storage_dir(teacher_id: int) -> Path:
    root = Path(settings.UPLOAD_DIR) / f"teacher_{teacher_id}" / "voice_samples"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _tts_provider() -> str:
    return (settings.TTS_PROVIDER or "elevenlabs").strip().lower()


def _should_create_elevenlabs_voice() -> bool:
    return bool(settings.ENABLE_TTS and _tts_provider() == "elevenlabs")


def _elevenlabs_voice_name(sample_id: int) -> str:
    prefix = (settings.ELEVENLABS_VOICE_NAME_PREFIX or "EduSpark Teacher").strip()
    return f"{prefix} {sample_id}"


async def _delete_external_voice(sample: TeacherVoiceSample) -> None:
    voice_id = getattr(sample, "elevenlabs_voice_id", None)
    if voice_id:
        await delete_voice(voice_id)
        sample.elevenlabs_voice_id = None
        sample.elevenlabs_requires_verification = False


def _sample_out(sample: TeacherVoiceSample | None) -> dict:
    if not sample:
        return {
            "has_sample": False,
            "processing_status": None,
            "status_label": None,
            "duration_seconds": None,
            "uploaded_at": None,
            "error_message": None,
        }
    st = sample.processing_status
    if hasattr(st, "value"):
        st = st.value
    return {
        "has_sample": True,
        "id": sample.id,
        "processing_status": st,
        "status_label": STATUS_LABELS.get(st, st),
        "duration_seconds": round(sample.duration_seconds, 1) if sample.duration_seconds else None,
        "uploaded_at": sample.uploaded_at.isoformat() if sample.uploaded_at else None,
        "error_message": sample.error_message,
        "requires_verification": bool(sample.elevenlabs_requires_verification),
        "ready": st == VoiceSampleStatus.ready.value,
    }


async def get_latest_ready_voice_sample(
    db: AsyncSession, teacher_profile_id: int
) -> TeacherVoiceSample | None:
    result = await db.execute(
        select(TeacherVoiceSample)
        .where(
            TeacherVoiceSample.teacher_profile_id == teacher_profile_id,
            TeacherVoiceSample.processing_status == VoiceSampleStatus.ready.value,
        )
        .order_by(TeacherVoiceSample.uploaded_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def list_voice_samples(db: AsyncSession, user: User) -> dict:
    tp = await get_or_create_teacher_profile(db, user)
    result = await db.execute(
        select(TeacherVoiceSample)
        .where(TeacherVoiceSample.teacher_profile_id == tp.id)
        .order_by(TeacherVoiceSample.uploaded_at.desc())
    )
    samples = list(result.scalars().all())
    latest_ready = await get_latest_ready_voice_sample(db, tp.id)
    latest_ready_id = latest_ready.id if latest_ready else None

    items = []
    for sample in samples:
        st = sample.processing_status
        if hasattr(st, "value"):
            st = st.value
        items.append(
            {
                "id": sample.id,
                "processing_status": st,
                "status_label": STATUS_LABELS.get(st, st),
                "duration_seconds": round(sample.duration_seconds, 1) if sample.duration_seconds else None,
                "uploaded_at": sample.uploaded_at.isoformat() if sample.uploaded_at else None,
                "error_message": sample.error_message,
                "requires_verification": bool(sample.elevenlabs_requires_verification),
                "ready": st == VoiceSampleStatus.ready.value,
                "is_latest_ready": sample.id == latest_ready_id,
            }
        )

    return {
        "has_ready_profile": latest_ready_id is not None,
        "latest_ready_id": latest_ready_id,
        "samples": items,
    }


async def get_voice_sample_status(db: AsyncSession, user: User) -> dict:
    tp = await get_or_create_teacher_profile(db, user)
    sample = await get_latest_voice_sample(db, tp.id)
    return _sample_out(sample)


async def get_latest_voice_sample(db: AsyncSession, teacher_profile_id: int) -> TeacherVoiceSample | None:
    result = await db.execute(
        select(TeacherVoiceSample)
        .where(TeacherVoiceSample.teacher_profile_id == teacher_profile_id)
        .order_by(TeacherVoiceSample.uploaded_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


def empty_sample_out() -> dict:
    return _sample_out(None)


async def create_voice_sample(
    db: AsyncSession,
    user: User,
    data: bytes,
    filename: str,
    *,
    commit: bool = True,
) -> tuple[TeacherVoiceSample, dict]:
    if len(data) < 1024:
        raise HTTPException(status_code=400, detail="الملف الصوتي فارغ")

    tp = await get_or_create_teacher_profile(db, user)
    ext = Path(filename or "voice.webm").suffix or ".webm"
    storage_dir = _voice_storage_dir(user.id)
    storage_path = storage_dir / f"sample_{uuid.uuid4().hex}{ext}"
    storage_path.write_bytes(data)

    validation = validate_voice_sample(storage_path)
    if not validation.ok:
        storage_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail=validation.error or "الملف الصوتي غير صالح")

    sample = TeacherVoiceSample(
        teacher_profile_id=tp.id,
        storage_path=str(storage_path),
        duration_seconds=validation.duration_seconds,
        processing_status=VoiceSampleStatus.pending.value,
        error_message=None,
        uploaded_at=datetime.now(timezone.utc),
    )
    db.add(sample)
    await db.flush()
    if commit:
        await db.commit()
        schedule_voice_sample_processing(sample.id)
    return sample, _sample_out(sample)


async def upload_voice_sample(db: AsyncSession, user: User, data: bytes, filename: str) -> dict:
    _, out = await create_voice_sample(db, user, data, filename, commit=True)
    return out


async def _process_voice_sample(sample_id: int) -> None:
    if sample_id in _running:
        return
    _running.add(sample_id)
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(TeacherVoiceSample).where(TeacherVoiceSample.id == sample_id))
            sample = result.scalar_one_or_none()
            if not sample:
                return

            sample.processing_status = VoiceSampleStatus.processing.value
            sample.error_message = None
            await db.commit()

            try:
                path = Path(sample.storage_path)
                if not path.exists():
                    raise ValueError("ملف العينة الصوتية غير موجود")

                revalidation = validate_voice_sample(path)
                if not revalidation.ok:
                    raise ValueError(revalidation.error or "فشل التحقق من الصوت")

                sample.duration_seconds = revalidation.duration_seconds
                transcript = await transcribe_audio(path)
                if not transcript or len(transcript.strip()) < 15:
                    raise ValueError("لم يُستخرج كلام واضح من التسجيل — تحدث بوضوح لمدة 60 ثانية على الأقل")

                # Teacher-level voice profile — same persona for all courses/grades
                persona = await build_persona_prompt(transcript, "عام", "جميع الصفوف")
                sample.transcript = transcript
                sample.persona_prompt = persona
                sample.elevenlabs_requires_verification = False

                if _should_create_elevenlabs_voice():
                    await _delete_external_voice(sample)
                    clone = await create_voice_clone(
                        path,
                        name=_elevenlabs_voice_name(sample.id),
                        description="EduSpark teacher voice sample",
                    )
                    sample.elevenlabs_voice_id = clone.voice_id
                    sample.elevenlabs_requires_verification = clone.requires_verification
                    if clone.requires_verification:
                        raise ValueError(
                            "يتطلب ElevenLabs التحقق من ملكية الصوت قبل استخدام هذه العينة"
                        )

                sample.processing_status = VoiceSampleStatus.ready.value
                sample.error_message = None
            except Exception as exc:
                logger.exception("Voice sample processing failed id=%s", sample_id)
                sample.processing_status = VoiceSampleStatus.failed.value
                sample.error_message = str(exc)

            await db.commit()
    finally:
        _running.discard(sample_id)


def schedule_voice_sample_processing(sample_id: int) -> None:
    asyncio.create_task(_process_voice_sample(sample_id))


async def _owned_sample(db: AsyncSession, user: User, sample_id: int) -> TeacherVoiceSample:
    tp = await get_or_create_teacher_profile(db, user)
    sample = await db.get(TeacherVoiceSample, sample_id)
    if not sample or sample.teacher_profile_id != tp.id:
        raise HTTPException(status_code=404, detail="العينة الصوتية غير موجودة")
    return sample


async def regenerate_voice_sample(db: AsyncSession, user: User, sample_id: int) -> dict:
    sample = await _owned_sample(db, user, sample_id)
    if not Path(sample.storage_path).exists():
        raise HTTPException(status_code=400, detail="ملف العينة الصوتية غير موجود")

    await _delete_external_voice(sample)
    sample.processing_status = VoiceSampleStatus.pending.value
    sample.error_message = None
    await db.commit()
    schedule_voice_sample_processing(sample.id)
    return _sample_out(sample)


async def delete_voice_sample(db: AsyncSession, user: User, sample_id: int) -> dict:
    sample = await _owned_sample(db, user, sample_id)
    await _delete_external_voice(sample)
    Path(sample.storage_path).unlink(missing_ok=True)
    await db.delete(sample)
    await db.commit()
    return await list_voice_samples(db, user)


async def preview_voice_sample(
    db: AsyncSession, user: User, sample_id: int, text: str
) -> dict:
    from app.core.config import get_settings
    from app.services.tts_service import synthesize_preview_audio

    cfg = get_settings()
    sample = await _owned_sample(db, user, sample_id)
    if sample.processing_status != VoiceSampleStatus.ready.value:
        raise HTTPException(status_code=400, detail="العينة الصوتية غير جاهزة بعد")

    if not cfg.ENABLE_TTS:
        return {
            "audio_url": None,
            "message": "توليد الصوت غير مفعّل على الخادم — فعّل ENABLE_TTS",
        }

    audio_url = await synthesize_preview_audio(
        text.strip() or "مرحباً، أنا معلمك الذكي.",
        sample.storage_path,
        sample_id=sample.id,
        voice_id=sample.elevenlabs_voice_id,
    )
    if not audio_url:
        return {"audio_url": None, "message": "تعذر توليد معاينة الصوت"}
    return {"audio_url": audio_url, "message": "تم توليد المعاينة"}


async def get_ready_voice_path_for_teacher(db: AsyncSession, teacher_user_id: int) -> str | None:
    tp = await db.execute(select(TeacherProfile).where(TeacherProfile.user_id == teacher_user_id))
    profile = tp.scalar_one_or_none()
    if not profile:
        return None
    sample = await get_latest_ready_voice_sample(db, profile.id)
    if sample and Path(sample.storage_path).exists():
        return sample.storage_path
    return None


async def get_ready_tts_reference_for_teacher(db: AsyncSession, teacher_user_id: int) -> dict:
    tp = await db.execute(select(TeacherProfile).where(TeacherProfile.user_id == teacher_user_id))
    profile = tp.scalar_one_or_none()
    if not profile:
        return {"speaker_wav": None, "elevenlabs_voice_id": None}
    sample = await get_latest_ready_voice_sample(db, profile.id)
    if sample and Path(sample.storage_path).exists():
        return {
            "speaker_wav": sample.storage_path,
            "elevenlabs_voice_id": sample.elevenlabs_voice_id,
        }
    return {"speaker_wav": None, "elevenlabs_voice_id": None}


async def get_ready_persona_for_teacher(db: AsyncSession, teacher_user_id: int) -> str | None:
    tp = await db.execute(select(TeacherProfile).where(TeacherProfile.user_id == teacher_user_id))
    profile = tp.scalar_one_or_none()
    if not profile:
        return None
    sample = await get_latest_ready_voice_sample(db, profile.id)
    return sample.persona_prompt if sample and sample.persona_prompt else None


# Late import avoids circular dependency at module load
from app.db.session import AsyncSessionLocal  # noqa: E402
