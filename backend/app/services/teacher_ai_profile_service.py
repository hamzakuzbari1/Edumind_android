"""Teacher AI profile for lesson chat identity."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.catalog import TeacherProfile
from app.models.user import User
from app.schemas.teacher_ai_profile import TeacherAiProfileOut, TeacherAiProfileUpdate
from app.services.teacher_setup_service import get_or_create_teacher_profile


def teacher_ai_profile_out(tp: TeacherProfile) -> TeacherAiProfileOut:
    return TeacherAiProfileOut(
        teacher_teaching_style=tp.teacher_teaching_style,
        teacher_tone=tp.teacher_tone,
        teacher_question_style=tp.teacher_question_style,
        teacher_motivation_level=tp.teacher_motivation_level,
        teacher_display_name=tp.teacher_display_name,
        teacher_bio=tp.bio,
        teacher_signature_phrase=tp.teacher_signature_phrase,
    )


def teacher_chat_kwargs(tp: TeacherProfile | None) -> dict:
    if not tp:
        return {}
    return {
        "teacher_teaching_style": tp.teacher_teaching_style,
        "teacher_tone": tp.teacher_tone,
        "teacher_question_style": tp.teacher_question_style,
        "teacher_motivation_level": tp.teacher_motivation_level,
        "teacher_display_name": (tp.teacher_display_name or tp.full_name or "").strip() or None,
        "teacher_bio": tp.bio,
        "teacher_signature_phrase": tp.teacher_signature_phrase,
    }


async def get_ai_profile(db: AsyncSession, user: User) -> TeacherAiProfileOut:
    tp = await get_or_create_teacher_profile(db, user)
    return teacher_ai_profile_out(tp)


async def update_ai_profile(
    db: AsyncSession,
    user: User,
    body: TeacherAiProfileUpdate,
) -> TeacherAiProfileOut:
    tp = await get_or_create_teacher_profile(db, user)
    tp.teacher_teaching_style = body.teacher_teaching_style
    tp.teacher_tone = body.teacher_tone
    tp.teacher_question_style = body.teacher_question_style
    tp.teacher_motivation_level = body.teacher_motivation_level
    tp.teacher_display_name = (body.teacher_display_name or "").strip() or None
    tp.bio = body.teacher_bio
    tp.teacher_signature_phrase = (body.teacher_signature_phrase or "").strip() or None
    await db.flush()
    return teacher_ai_profile_out(tp)
