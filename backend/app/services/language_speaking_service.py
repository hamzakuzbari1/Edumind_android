"""Speaking prompts — upload + AI feedback (STT, grammar, tutor reply, scoring)."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.language.enums import LanguageSkill
from app.models.language.progress import LanguageSpeakingProgress
from app.models.media import MediaObject
from app.services.language_adaptive_service import record_lesson_result
from app.services.language_analytics_service import refresh_language_analytics
from app.services.language_content_service import get_content_item, list_content_items, pass_threshold_for_item
from app.services.language_curriculum_service import credit_skill_objectives
from app.services.language_engagement_service import record_activity
from app.services.language_grammar.enums import GrammarEvidenceSourceSkill
from app.services.language_grammar_skill_context import (
    SkillGrammarContext,
    build_skill_grammar_context,
    complete_current_skill_activity_async,
)
from app.services.language_learner_events import record_scored_practice
from app.services.language_media_service import upload_student_speaking
from app.services.language_speaking_feedback_service import analyze_speaking_recording
from app.services.language_validation import validate_speaking_duration
from app.services.language_subscription_service import get_default_language

CONTENT_TYPE = "speaking_prompt"
logger = logging.getLogger(__name__)


def _grammar_speaking_instruction(ctx: SkillGrammarContext | None) -> str:
    if ctx is None:
        return ""
    targets = ", ".join(ctx.grammar_targets[:4]) or ctx.display_name
    examples = "; ".join(ctx.examples[:3])
    instruction = (
        f"Grammar focus: {ctx.display_name}. In your spoken answer, use this grammar directly "
        f"at least two times to express real meaning. Useful forms: {targets}."
    )
    if examples:
        instruction += f" Model examples: {examples}."
    return instruction


def _with_grammar_speaking_instruction(prompt: str, ctx: SkillGrammarContext | None) -> str:
    instruction = _grammar_speaking_instruction(ctx)
    base = (prompt or "").strip()
    if not instruction or instruction in base:
        return base
    return f"{base}\n\n{instruction}" if base else instruction


async def _speaking_progress_map(
    db: AsyncSession, *, student_id: int, ids: list[int]
) -> dict[int, LanguageSpeakingProgress]:
    if not ids:
        return {}
    result = await db.execute(
        select(LanguageSpeakingProgress).where(
            LanguageSpeakingProgress.student_id == student_id,
            LanguageSpeakingProgress.content_item_id.in_(ids),
        )
    )
    return {p.content_item_id: p for p in result.scalars().all()}


def _prompt_out(
    item,
    progress: LanguageSpeakingProgress | None,
    public_url: str | None = None,
    grammar_ctx: SkillGrammarContext | None = None,
) -> dict:
    body = item.body_json or {}
    return {
        "id": item.id,
        "title": item.title,
        "level": item.level.value if item.level else None,
        "prompt": _with_grammar_speaking_instruction(body.get("prompt") or "", grammar_ctx),
        "prompt_ar": body.get("prompt_ar"),
        "grammar_id": grammar_ctx.grammar_id if grammar_ctx else body.get("grammar_id"),
        "grammar_title": grammar_ctx.display_name if grammar_ctx else body.get("grammar_title"),
        "min_seconds": int(body.get("min_seconds") or 20),
        "progress": {
            "media_object_id": progress.media_object_id if progress else None,
            "public_url": public_url,
            "duration_seconds": progress.duration_seconds if progress else None,
            "completed_at": progress.completed_at if progress else None,
            "submitted_at": progress.submitted_at if progress else None,
        },
    }


async def list_speaking(db: AsyncSession, *, student_id: int) -> dict:
    student_level, lesson_level, items = await list_content_items(
        db,
        student_id=student_id,
        content_type=CONTENT_TYPE,
        skill=LanguageSkill.speaking,
        level_skill=LanguageSkill.speaking,
    )
    language = await get_default_language(db)
    grammar_ctx = await build_skill_grammar_context(
        db,
        student_id=student_id,
        language_id=language.id,
        source_skill=GrammarEvidenceSourceSkill.speaking,
    )
    prog = await _speaking_progress_map(db, student_id=student_id, ids=[i.id for i in items])
    out = []
    for item in items:
        p = prog.get(item.id)
        url = None
        if p and p.media_object_id:
            media = await db.get(MediaObject, p.media_object_id)
            url = media.public_url if media else None
        out.append(_prompt_out(item, p, url, grammar_ctx))
    return {
        "student_level": student_level.value,
        "lesson_level": lesson_level.value if lesson_level else None,
        "prompts": out,
    }


async def get_speaking_prompt(db: AsyncSession, *, student_id: int, prompt_id: int) -> dict:
    item = await get_content_item(
        db,
        student_id=student_id,
        content_id=prompt_id,
        content_type=CONTENT_TYPE,
        skill=LanguageSkill.speaking,
        level_skill=LanguageSkill.speaking,
    )
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exercise is not available")
    prog = await _speaking_progress_map(db, student_id=student_id, ids=[item.id])
    p = prog.get(item.id)
    language = await get_default_language(db)
    grammar_ctx = await build_skill_grammar_context(
        db,
        student_id=student_id,
        language_id=language.id,
        source_skill=GrammarEvidenceSourceSkill.speaking,
    )
    url = None
    if p and p.media_object_id:
        media = await db.get(MediaObject, p.media_object_id)
        url = media.public_url if media else None
    return _prompt_out(item, p, url, grammar_ctx)


async def upload_speaking_recording(
    db: AsyncSession,
    *,
    student_id: int,
    prompt_id: int,
    file: UploadFile,
) -> dict:
    item = await get_content_item(
        db,
        student_id=student_id,
        content_id=prompt_id,
        content_type=CONTENT_TYPE,
        skill=LanguageSkill.speaking,
        level_skill=LanguageSkill.speaking,
    )
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exercise is not available")
    media = await upload_student_speaking(
        db,
        student_id=student_id,
        subfolder="language_speaking",
        filename_hint=f"prompt_{prompt_id}",
        file=file,
    )
    return {"media_object_id": media.id, "public_url": media.public_url}


async def submit_speaking(
    db: AsyncSession,
    *,
    student_id: int,
    prompt_id: int,
    media_object_id: int,
    duration_seconds: int | None = None,
) -> dict:
    item = await get_content_item(
        db,
        student_id=student_id,
        content_id=prompt_id,
        content_type=CONTENT_TYPE,
        skill=LanguageSkill.speaking,
        level_skill=LanguageSkill.speaking,
    )
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exercise is not available")
    media = await db.get(MediaObject, media_object_id)
    if not media:
        raise HTTPException(status_code=400, detail="Invalid audio recording")

    body = item.body_json or {}
    min_seconds = int(body.get("min_seconds") or 20)
    duration = validate_speaking_duration(duration_seconds, min_seconds=min_seconds)
    language = await get_default_language(db)
    grammar_ctx = await build_skill_grammar_context(
        db,
        student_id=student_id,
        language_id=language.id,
        source_skill=GrammarEvidenceSourceSkill.speaking,
    )
    prompt_text = _with_grammar_speaking_instruction(body.get("prompt") or "", grammar_ctx)

    feedback = await analyze_speaking_recording(
        db,
        student_id=student_id,
        media=media,
        prompt_text=prompt_text,
        level=item.level,
        duration_seconds=duration,
        min_seconds=min_seconds,
    )
    score_pct = feedback["score_percent"]
    metrics = feedback["metrics"]
    level_estimate = feedback["level_estimate"]
    reply_media = feedback.get("reply_media")
    reply_audio_url = reply_media.public_url if reply_media else None

    threshold = pass_threshold_for_item(item)
    passed = score_pct >= threshold and metrics.get("has_media") and duration >= min_seconds

    result = await db.execute(
        select(LanguageSpeakingProgress).where(
            LanguageSpeakingProgress.student_id == student_id,
            LanguageSpeakingProgress.content_item_id == prompt_id,
        )
    )
    progress = result.scalar_one_or_none()
    if not progress:
        progress = LanguageSpeakingProgress(
            student_id=student_id,
            content_item_id=prompt_id,
            media_object_id=media_object_id,
        )
        db.add(progress)
    progress.media_object_id = media_object_id
    progress.duration_seconds = duration
    progress.transcript = feedback["transcript"]
    progress.metrics_json = metrics
    progress.level_estimate = level_estimate
    # AI scoring "ran" when the pipeline produced a transcript; otherwise it degraded to the heuristic.
    progress.scoring_version = "ai_rubric_v2" if feedback.get("transcript") else "rule_v1"
    progress.ai_evaluation_json = {
        "correction": feedback["correction"],
        "reply": feedback["reply"],
        "score_percent": score_pct,
        "level_estimate": level_estimate.value if level_estimate else None,
        "reply_audio_url": reply_audio_url,
    }
    if passed and not progress.completed_at:
        progress.completed_at = datetime.now(timezone.utc)
    await db.flush()

    event = "speaking_completed" if passed else "speaking_submitted"
    await record_activity(
        db,
        student_id=student_id,
        language_id=language.id,
        event_type=event,
        skill=LanguageSkill.speaking,
        duration_seconds=int(duration_seconds or 0),
        payload_json={
            "content_item_id": prompt_id,
            "title": item.title,
            "score_percent": score_pct,
            "passed": passed,
        },
    )
    await refresh_language_analytics(db, student_id=student_id, language_id=language.id)
    await record_lesson_result(
        db, student_id=student_id, language_id=language.id, skill=LanguageSkill.speaking, score_percent=float(score_pct)
    )
    await credit_skill_objectives(
        db, student_id=student_id, language_id=language.id, skill=LanguageSkill.speaking,
        score_percent=float(score_pct), passed=passed,
    )
    if passed:
        from app.services.language_xp_service import award_language_xp

        await award_language_xp(db, student_id=student_id, language_id=language.id, activity="speaking", key=f"speaking:{prompt_id}")
    await record_scored_practice(
        db, student_id=student_id, language_id=language.id, skill=LanguageSkill.speaking,
        level=item.level, score_percent=float(score_pct), source="speaking",
    )
    if passed:
        try:
            await complete_current_skill_activity_async(
                db,
                student_id=student_id,
                language_id=language.id,
                skill=GrammarEvidenceSourceSkill.speaking,
                score=float(score_pct),
                activity_id=f"speaking:{prompt_id}:{media_object_id}",
                activity_type="speaking",
                lesson_id=str(prompt_id),
                context=f"speaking:{prompt_id}",
                observation_id=f"ev_speaking_{prompt_id}_{media_object_id}",
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("grammar speaking evidence completion failed: %s", exc)
    correction = feedback["correction"]
    return {
        "prompt_id": prompt_id,
        "media_object_id": media_object_id,
        "public_url": media.public_url,
        "duration_seconds": progress.duration_seconds,
        "score_percent": float(score_pct),
        "passed": passed,
        "completed_at": progress.completed_at,
        "status": "completed" if progress.completed_at else "in_progress",
        "transcript": feedback["transcript"] or None,
        "correction_text": correction.get("corrected_text") or None,
        "grammar_errors": correction.get("errors") or [],
        "reply": feedback["reply"] or None,
        "reply_audio_url": reply_audio_url,
    }
