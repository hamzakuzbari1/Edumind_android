"""Student Language Learning — access, placement, and Phase C1 lessons."""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import require_student_actor
from app.core.listening_deployment_deps import require_listening_deployment_ready
from app.db.session import get_db
from app.models.language.analytics import LanguageAnalytics
from app.models.language.enums import LanguageLevel, LanguageOnboardingStep, LanguageSkill
from app.models.user import User
from app.schemas.language import (
    LanguageAccessOut,
    LanguagePlacementSkipRequest,
    LanguageProductOut,
    LanguageSubscribeOut,
    LanguageSubscribeRequest,
)
from app.schemas.language_listening_acquisition import ListeningNextResponseOut
from app.schemas.language_listening_bundles import (
    LessonExperienceBundleOut,
    ListeningJourneyBundleOut,
    ListeningLessonSubmitBundleOut,
)
from app.schemas.language_writing_bundles import (
    WritingDraftSubmitIn,
    WritingDraftSubmitOut,
    WritingGenerateIn,
    WritingGenerateOut,
    WritingJourneyBundleOut,
)
from app.schemas.language_learning import (
    LanguageHubOut,
    LanguageProgressOut,
    LessonListItemOut,
    LessonListOut,
    LessonProgressOut,
    LessonSubmitIn,
    LessonSubmitOut,
    ListeningLessonOut,
    SpeakingListOut,
    SpeakingPromptOut,
    SpeakingConversationProgressOut,
    SpeakingConversationResetOut,
    SpeakingConversationStateOut,
    SpeakingConversationTurnOut,
    SpeakingSubmitIn,
    SpeakingSubmitOut,
    ShadowSentenceListOut,
    ShadowSubmitOut,
    DictionarySearchOut,
    VocabularyAiGenerateOut,
    VocabularyCardOut,
    LearnerModelProfileOut,
    LearnerPracticeSetOut,
    LearnerPracticeSubmitIn,
    LearnerPracticeSubmitOut,
    VocabularyChallengeOut,
    VocabularyChallengeSubmitIn,
    VocabularyChallengeSubmitOut,
    VocabularySaveIn,
    VocabularySaveOut,
    VocabularyListOut,
    VocabularyReviewIn,
    VocabQuizOut,
    VocabQuizSpellingIn,
    VocabQuizSpellingOut,
    VocabQuizCompleteIn,
    VocabQuizCompleteOut,
    WordAnalysisIn,
    WordAnalysisOut,
    WritingListOut,
    WritingPromptOut,
    WritingSubmitIn,
    WritingSubmitOut,
)
from app.schemas.language_placement import (
    PlacementHistoryLatestOut,
    PlacementHistoryListOut,
    PlacementSpeakingUploadOut,
)
from app.schemas.language_reading_v2 import (
    ReadingV2AttemptOut,
    ReadingV2GenerateAttemptIn,
    ReadingV2HistoryOut,
    ReadingV2OverviewOut,
    ReadingV2PathOut,
    ReadingV2SubmitAttemptIn,
    ReadingV2SubmitAttemptOut,
)
from app.schemas.language_certificate import LanguageCertificateListOut
from app.services.language_access_service import (
    build_language_access,
    require_active_language_subscription,
    require_language_learning_ready,
)
from app.services.language_content_service import (
    get_listening_lesson,
    lesson_body_for_student,
    list_lessons,
    resolve_listening_audio,
)
from app.services.language_curriculum_service import build_curriculum_overview, record_objective_practice
from app.services.language_microlesson_service import get_micro_lesson
from app.services.language_placement_history_service import list_placement_history
from app.services.language_xp_service import award_daily_mission_xp, get_xp_overview
from app.services.language_daily_mission_service import build_daily_mission, renew_daily_mission
from app.services.language_rate_limit_service import check_or_raise
from app.services.language_hub_service import build_language_hub, build_language_progress
from app.schemas.language_curriculum import (
    CurriculumOverviewOut,
    DailyMissionRenewOut,
    DailyPlanOut,
    ObjectivePracticeIn,
    ObjectivePracticeOut,
)
from app.services.language_listening_acquisition import acquire_next_listening
from app.services.language_listening_journey.builder import build_listening_journey_bundle
from app.services.language_listening_lesson_experience.service import (
    build_student_lesson_bundle,
    build_submit_bundle,
)
from app.services.language_listening_prefill_task import background_prefill_listening_pool
from app.services.language_listening_service import skip_listening
from app.services.language_skill_progress_service import submit_listening
from app.services.language_tts_service import get_lesson_audio
from app.services.language_speaking_service import (
    get_speaking_prompt,
    list_speaking,
    submit_speaking,
    upload_speaking_recording,
)
from app.services.language_conversation_service import (
    get_conversation_progress,
    get_conversation_session_detail,
    get_conversation_state,
    get_turn_explanation,
    list_conversation_sessions,
    process_conversation_turn,
    reset_conversation,
)
from app.services.language_conversation_scenario_service import (
    end_session_with_feedback,
    get_scenario_session,
    list_scenario_sessions,
    list_scenarios,
    process_scenario_turn,
    start_scenario_session,
)
from app.services.language_shadowing_service import list_shadow_sentences, submit_shadow
from app.services.language_transcription_service import transcribe_english_audio
from app.services.language_adaptive_service import get_adaptive_state_overview
from app.services.language_learner_model_service import LanguageLearnerModelService
from app.services.language_practice_service import generate_practice_set, submit_practice
from app.services.language_reading_v2_service import (
    build_reading_v2_history,
    build_reading_v2_overview,
    build_reading_v2_path,
    create_reading_v2_attempt,
    submit_reading_v2_attempt,
)
from app.services.language_learning_path_service import generate_learning_path
from app.services.language_progression_service import sync_progression_from_skill_levels
from app.services.language_subscription_service import (
    ensure_language_profile,
    get_default_language,
    get_default_product,
    subscribe_language,
)
from app.services.language_vocabulary_service import (
    analyze_word,
    assess_word_pronunciation,
    say_word,
    generate_ai_vocabulary_batch,
    generate_vocabulary_challenge,
    get_vocabulary_card,
    list_vocabulary,
    review_vocabulary,
    save_word,
    submit_vocabulary_challenge,
)
from app.services.language_vocabulary_sr_service import get_vocabulary_stats
from app.services.language_vocabulary_quiz_service import (
    build_daily_quiz,
    check_quiz_spelling,
    record_quiz_completion,
)
from app.services.language_writing.enums import OfficialWritingCEFR, WritingGoal
from app.services.language_writing_evaluation_runtime.runtime_api import submit_writing_draft_for_evaluation
from app.services.language_writing_journey.builder import build_writing_journey_bundle
from app.services.language_writing_runtime.runtime_api import generate_writing_lesson_for_student
from app.services.language_writing_service import get_writing_prompt, list_writing, submit_writing
from app.services.language_certificate_service import list_student_certificates

router = APIRouter(prefix="/student/languages", tags=["Language Learning"])
logger = logging.getLogger(__name__)

_LEGACY_PLACEMENT_REMOVED_DETAIL = {
    "code": "legacy_placement_removed",
    "message": "The legacy placement system was removed. Use the AI placement exam instead.",
    "redirect": "/student/languages/exam",
}


def _raise_legacy_placement_removed() -> None:
    """Compatibility response with no authentication, body parsing, or database access."""
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail=_LEGACY_PLACEMENT_REMOVED_DETAIL,
    )


def _progress_out(row) -> LessonProgressOut:
    if not row:
        return LessonProgressOut()
    return LessonProgressOut(
        status=row.status.value if hasattr(row.status, "value") else str(row.status),
        score_percent=row.score_percent,
        completed_at=row.completed_at,
        attempt_count=int(row.attempt_count or 0),
    )


@router.get("/access", response_model=LanguageAccessOut)
async def language_access(
    student: User = Depends(require_student_actor()),
    db: AsyncSession = Depends(get_db),
):
    return await build_language_access(db, student.id)


@router.get("/product", response_model=LanguageProductOut)
async def language_product(db: AsyncSession = Depends(get_db)):
    product = await get_default_product(db)
    return LanguageProductOut(
        id=product.id,
        slug=product.slug,
        name_ar=product.name_ar,
        description_ar=product.description_ar,
        price=product.price,
        currency=product.currency,
        term_days=product.term_days,
    )


@router.post("/subscribe", response_model=LanguageSubscribeOut)
async def language_subscribe(
    body: LanguageSubscribeRequest,
    student: User = Depends(require_student_actor()),
    db: AsyncSession = Depends(get_db),
):
    result = await subscribe_language(db, student.id, body.method)
    await db.commit()
    return result


@router.post("/placement/skip", response_model=LanguageAccessOut)
async def skip_language_placement(
    body: LanguagePlacementSkipRequest | None = None,
    student: User = Depends(require_active_language_subscription()),
    db: AsyncSession = Depends(get_db),
):
    """Learner shortcut: unlock language learning at a selected CEFR baseline."""
    language = await get_default_language(db)
    profile = await ensure_language_profile(db, student.id, language.id)
    now = datetime.now(timezone.utc)
    payload = body or LanguagePlacementSkipRequest()
    baseline = LanguageLevel(payload.baseline_level)
    skill_levels = {
        LanguageSkill.reading: baseline,
        LanguageSkill.listening: baseline,
        LanguageSkill.writing: baseline,
        LanguageSkill.speaking: baseline,
    }

    profile.placement_completed_at = profile.placement_completed_at or now
    profile.last_assessment_date = profile.last_assessment_date or profile.placement_completed_at
    profile.onboarding_step = LanguageOnboardingStep.dashboard

    analytics = await db.get(LanguageAnalytics, {"student_id": student.id, "language_id": language.id})
    if analytics is None:
        analytics = LanguageAnalytics(student_id=student.id, language_id=language.id)
        db.add(analytics)
        await db.flush()
    analytics.reading_level = baseline
    analytics.listening_level = baseline
    analytics.writing_level = baseline
    analytics.speaking_level = baseline
    analytics.overall_level_internal = baseline
    analytics.primary_focus_skill = "reading"
    analytics.strength_skill = "reading"

    await sync_progression_from_skill_levels(
        db,
        student_id=student.id,
        language_id=language.id,
        skill_levels=skill_levels,
        overall=baseline,
        source="placement_skip",
    )
    await generate_learning_path(
        db,
        student_id=student.id,
        language_id=language.id,
        assessment_id=None,
        overall_level=baseline,
        skill_levels=skill_levels,
    )
    await db.commit()
    return await build_language_access(db, student.id)


@router.api_route(
    "/placement/{legacy_path:path}",
    methods=["POST", "PUT", "PATCH", "DELETE"],
    include_in_schema=False,
)
async def legacy_placement_removed(legacy_path: str):
    """One inert compatibility route replaces every legacy placement mutation handler."""
    del legacy_path
    _raise_legacy_placement_removed()


@router.get("/placement-history", response_model=PlacementHistoryListOut)
async def placement_history(
    student: User = Depends(require_student_actor()),
    db: AsyncSession = Depends(get_db),
):
    """Return coherent historical snapshots owned by the authenticated student."""
    results = await list_placement_history(db, student_id=student.id)
    return PlacementHistoryListOut(available=bool(results), results=results)


@router.get("/placement-history/latest", response_model=PlacementHistoryLatestOut)
async def latest_placement_history(
    student: User = Depends(require_student_actor()),
    db: AsyncSession = Depends(get_db),
):
    """Return the latest coherent placement snapshot, never a live-analytics composite."""
    results = await list_placement_history(db, student_id=student.id, limit=1)
    latest = results[0] if results else None
    return PlacementHistoryLatestOut(available=latest is not None, result=latest)


@router.get("/hub", response_model=LanguageHubOut)
async def language_hub(
    student: User = Depends(require_language_learning_ready()),
    db: AsyncSession = Depends(get_db),
):
    return await build_language_hub(db, student_id=student.id)


@router.get("/curriculum", response_model=CurriculumOverviewOut)
async def language_curriculum(
    student: User = Depends(require_language_learning_ready()),
    db: AsyncSession = Depends(get_db),
):
    payload = await build_curriculum_overview(db, student_id=student.id)
    return CurriculumOverviewOut(**payload)


@router.get("/daily-plan", response_model=DailyPlanOut)
async def language_daily_plan(
    student: User = Depends(require_language_learning_ready()),
    db: AsyncSession = Depends(get_db),
):
    payload = await build_daily_mission(db, student_id=student.id)
    # Grant bounded XP for completed daily-mission tasks (round-scoped, reduced for renewed rounds).
    language = await get_default_language(db)
    await award_daily_mission_xp(db, student_id=student.id, language_id=language.id, plan=payload)
    # Phase 11 — record today's progress snapshot for analytics time-series (idempotent, best-effort).
    try:
        from app.services.language_progress_analytics_service import record_snapshot

        await record_snapshot(db, student_id=student.id, language_id=language.id)
    except Exception:
        pass
    await db.commit()
    return DailyPlanOut(**payload)


@router.post("/daily-plan/renew", response_model=DailyMissionRenewOut)
async def language_daily_plan_renew(
    student: User = Depends(require_language_learning_ready()),
    db: AsyncSession = Depends(get_db),
):
    """Renew the daily mission for a fresh round (only once the current one is finished).
    Renewed rounds award reduced XP, for integrity."""
    result = await renew_daily_mission(db, student_id=student.id)
    await db.commit()
    return DailyMissionRenewOut(**result)


@router.get("/xp")
async def language_xp(
    student: User = Depends(require_language_learning_ready()),
    db: AsyncSession = Depends(get_db),
):
    language = await get_default_language(db)
    return await get_xp_overview(db, student_id=student.id, language_id=language.id)


@router.post("/curriculum/objective/practiced", response_model=ObjectivePracticeOut)
async def language_curriculum_objective_practiced(
    body: ObjectivePracticeIn,
    student: User = Depends(require_language_learning_ready()),
    db: AsyncSession = Depends(get_db),
):
    result = await record_objective_practice(db, student_id=student.id, objective_id=body.objective_id)
    await db.commit()
    return ObjectivePracticeOut(**result)


@router.get("/curriculum/objective/{objective_id}/lesson")
async def language_objective_lesson(
    objective_id: str,
    student: User = Depends(require_language_learning_ready()),
    db: AsyncSession = Depends(get_db),
):
    return await get_micro_lesson(objective_id=objective_id)


@router.get("/adaptive/state")
async def language_adaptive_state(
    student: User = Depends(require_language_learning_ready()),
    db: AsyncSession = Depends(get_db),
):
    language = await get_default_language(db)
    result = await get_adaptive_state_overview(db, student_id=student.id, language_id=language.id)
    await db.commit()
    return result


@router.get("/reading-v2/overview", response_model=ReadingV2OverviewOut)
async def reading_v2_overview(
    student: User = Depends(require_language_learning_ready()),
    db: AsyncSession = Depends(get_db),
):
    language = await get_default_language(db)
    result = await build_reading_v2_overview(db, student_id=student.id, language_id=language.id)
    await db.commit()
    return result


@router.get("/reading-v2/path", response_model=ReadingV2PathOut)
async def reading_v2_path(
    student: User = Depends(require_language_learning_ready()),
    db: AsyncSession = Depends(get_db),
):
    language = await get_default_language(db)
    result = await build_reading_v2_path(db, student_id=student.id, language_id=language.id)
    await db.commit()
    return result


@router.post("/reading-v2/attempts", response_model=ReadingV2AttemptOut)
async def reading_v2_create_attempt(
    body: ReadingV2GenerateAttemptIn,
    student: User = Depends(require_language_learning_ready()),
    db: AsyncSession = Depends(get_db),
):
    language = await get_default_language(db)
    result = await create_reading_v2_attempt(db, student_id=student.id, language_id=language.id, mode=body.mode)
    await db.commit()
    return result


@router.post("/reading-v2/attempts/{attempt_id}/submit", response_model=ReadingV2SubmitAttemptOut)
async def reading_v2_submit_attempt(
    attempt_id: int,
    body: ReadingV2SubmitAttemptIn,
    student: User = Depends(require_language_learning_ready()),
    db: AsyncSession = Depends(get_db),
):
    language = await get_default_language(db)
    result = await submit_reading_v2_attempt(
        db,
        student_id=student.id,
        language_id=language.id,
        attempt_id=attempt_id,
        answers=body.answers,
        duration_seconds=body.duration_seconds,
    )
    await db.commit()
    return result


@router.get("/reading-v2/history", response_model=ReadingV2HistoryOut)
async def reading_v2_history(
    limit: int = 30,
    student: User = Depends(require_language_learning_ready()),
    db: AsyncSession = Depends(get_db),
):
    language = await get_default_language(db)
    return await build_reading_v2_history(db, student_id=student.id, language_id=language.id, limit=limit)


@router.get("/listening", response_model=LessonListOut)
async def listening_list(
    student: User = Depends(require_language_learning_ready()),
    db: AsyncSession = Depends(get_db),
):
    student_level, lesson_level, items, progress_map = await list_lessons(
        db, student_id=student.id, skill=LanguageSkill.listening
    )
    out_lessons: list[LessonListItemOut] = []
    for item in items:
        _url, audio_available = await resolve_listening_audio(db, item)
        out_lessons.append(
            LessonListItemOut(
                id=item.id,
                title=item.title,
                level=item.level.value if item.level else (lesson_level.value if lesson_level else ""),
                sort_order=item.sort_order,
                progress=_progress_out(progress_map.get(item.id)),
                audio_available=audio_available,
            )
        )
    return LessonListOut(
        student_level=student_level.value,
        lesson_level=lesson_level.value if lesson_level else None,
        lessons=out_lessons,
    )


@router.post("/vocabulary/save", response_model=VocabularySaveOut)
async def vocabulary_save(
    body: VocabularySaveIn,
    student: User = Depends(require_language_learning_ready()),
    db: AsyncSession = Depends(get_db),
):
    """Save a word the learner met during practice to their vocabulary bank."""
    result = await save_word(db, student_id=student.id, word=body.word)
    await db.commit()
    return VocabularySaveOut(**result)


@router.get("/listening/journey", response_model=ListeningJourneyBundleOut)
async def listening_journey(
    student: User = Depends(require_language_learning_ready()),
    db: AsyncSession = Depends(get_db),
    _deployment: None = Depends(require_listening_deployment_ready),
):
    """Canonical journey bundle: timeline, promotion, and personal goal only."""

    language = await get_default_language(db)
    return await build_listening_journey_bundle(db, student_id=student.id, language_id=language.id)


@router.get("/listening/next", response_model=ListeningNextResponseOut)
async def listening_next(
    background_tasks: BackgroundTasks,
    student: User = Depends(require_language_learning_ready()),
    db: AsyncSession = Depends(get_db),
    _deployment: None = Depends(require_listening_deployment_ready),
    attempt: int = 1,
):
    """Adaptive listening session entry: returns a lesson or explicit acquisition state."""

    response, schedule_prefill = await acquire_next_listening(
        db, student_id=student.id, attempt=max(1, attempt)
    )
    await db.commit()
    if schedule_prefill:
        background_tasks.add_task(background_prefill_listening_pool, student_id=student.id)
    return response


@router.get("/listening/acquisition", response_model=ListeningNextResponseOut)
async def listening_acquisition_status(
    background_tasks: BackgroundTasks,
    student: User = Depends(require_language_learning_ready()),
    db: AsyncSession = Depends(get_db),
    _deployment: None = Depends(require_listening_deployment_ready),
    attempt: int = 1,
):
    """Poll-friendly alias with the same response contract as /listening/next."""

    response, schedule_prefill = await acquire_next_listening(
        db, student_id=student.id, attempt=max(1, attempt)
    )
    await db.commit()
    if schedule_prefill:
        background_tasks.add_task(background_prefill_listening_pool, student_id=student.id)
    return response


@router.post("/listening/skip")
async def listening_skip_active(
    student: User = Depends(require_language_learning_ready()),
    db: AsyncSession = Depends(get_db),
    _deployment: None = Depends(require_listening_deployment_ready),
):
    cleared = await skip_listening(db, student_id=student.id, content_id=None)
    return {"cleared": cleared}


@router.post("/listening/{content_id}/skip")
async def listening_skip(
    content_id: int,
    student: User = Depends(require_language_learning_ready()),
    db: AsyncSession = Depends(get_db),
    _deployment: None = Depends(require_listening_deployment_ready),
):
    cleared = await skip_listening(db, student_id=student.id, content_id=content_id)
    return {"cleared": cleared}


@router.get("/listening/{content_id}", response_model=LessonExperienceBundleOut)
async def listening_detail(
    content_id: int,
    student: User = Depends(require_language_learning_ready()),
    db: AsyncSession = Depends(get_db),
    _deployment: None = Depends(require_listening_deployment_ready),
):
    item, progress, audio_url, audio_available = await get_listening_lesson(
        db, student_id=student.id, content_id=content_id
    )
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lesson not found")
    from app.services.language_listening_reservation import listening_session_reservation_service

    language = await get_default_language(db)
    await listening_session_reservation_service.touch_started(
        db,
        student_id=student.id,
        language_id=language.id,
        content_item_id=content_id,
    )
    await db.commit()
    return await build_student_lesson_bundle(
        db,
        item=item,
        student_id=student.id,
        language_id=language.id,
        progress_out=_progress_out(progress).model_dump(),
    )
    body = lesson_body_for_student(item)
    # No pre-recorded audio? Synthesize (and cache) lesson audio on demand — best effort.
    if not audio_url:
        try:
            tts = await get_lesson_audio(db, content_item_id=item.id)
            if tts and tts.get("public_url"):
                audio_url = tts["public_url"]
                audio_available = True
                await db.commit()
        except Exception:
            await db.rollback()
    return ListeningLessonOut(
        id=item.id,
        title=item.title,
        level=item.level.value if item.level else "A1",
        instructions=body.get("instructions"),
        questions=body.get("questions") or [],
        audio_url=audio_url,
        audio_available=audio_available,
        progress=_progress_out(progress),
    )


@router.post("/listening/{content_id}/submit", response_model=ListeningLessonSubmitBundleOut)
async def listening_submit(
    content_id: int,
    body: LessonSubmitIn,
    student: User = Depends(require_language_learning_ready()),
    db: AsyncSession = Depends(get_db),
    _deployment: None = Depends(require_listening_deployment_ready),
):
    result = await submit_listening(db, student_id=student.id, content_id=content_id, answers=body.answers)
    await db.commit()
    item, progress, _audio_url, _audio_available = await get_listening_lesson(
        db, student_id=student.id, content_id=content_id
    )
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lesson not found")
    language = await get_default_language(db)
    return await build_submit_bundle(
        db,
        item=item,
        student_id=student.id,
        language_id=language.id,
        progress_out=_progress_out(progress).model_dump(),
        submit_result=result,
    )


@router.get("/progress", response_model=LanguageProgressOut)
async def language_progress(
    student: User = Depends(require_language_learning_ready()),
    db: AsyncSession = Depends(get_db),
):
    return await build_language_progress(db, student_id=student.id)


@router.get("/vocabulary", response_model=VocabularyListOut)
async def vocabulary_list(
    student: User = Depends(require_language_learning_ready()),
    db: AsyncSession = Depends(get_db),
):
    return await list_vocabulary(db, student_id=student.id)


@router.get("/vocabulary/stats")
async def vocabulary_stats(
    student: User = Depends(require_language_learning_ready()),
    db: AsyncSession = Depends(get_db),
):
    language = await get_default_language(db)
    return await get_vocabulary_stats(db, student_id=student.id, language_id=language.id)


@router.post("/vocabulary/analyze", response_model=WordAnalysisOut)
async def vocabulary_analyze(
    body: WordAnalysisIn,
    student: User = Depends(require_language_learning_ready()),
    db: AsyncSession = Depends(get_db),
):
    """On-demand AI vocabulary lookup: definition, example, pronunciation, synonyms (English only)."""
    return await analyze_word(word=body.word, level=body.level)


@router.post("/vocabulary/generate-ai", response_model=VocabularyAiGenerateOut)
async def vocabulary_generate_ai(
    student: User = Depends(require_language_learning_ready()),
    db: AsyncSession = Depends(get_db),
):
    """AI-generated, interest-aware vocabulary batch (Claude), max 10/day, auto-scheduled for SM-2 review."""
    return await generate_ai_vocabulary_batch(db, student_id=student.id)


@router.post("/vocabulary/{content_id}/image")
async def vocabulary_word_image(
    content_id: int,
    student: User = Depends(require_language_learning_ready()),
    db: AsyncSession = Depends(get_db),
):
    """Illustration for a vocabulary word (Gemini), generated once and cached on the content item."""
    from app.services.language_vocabulary_image_service import get_or_create_word_image

    url = await get_or_create_word_image(db, content_id=content_id)
    return {"image_url": url}


class WordSayIn(BaseModel):
    word: str


@router.post("/vocabulary/say")
async def vocabulary_say(
    body: WordSayIn,
    student: User = Depends(require_language_learning_ready()),
    db: AsyncSession = Depends(get_db),
):
    """Hear the word: synthesize its pronunciation (edge-tts, no quota)."""
    return await say_word(body.word)


@router.post("/vocabulary/pronounce")
async def vocabulary_pronounce(
    word: str = Form(...),
    file: UploadFile = File(...),
    duration_seconds: int | None = Form(default=None),
    student: User = Depends(require_language_learning_ready()),
    db: AsyncSession = Depends(get_db),
):
    """Say the word: AI grades pronunciation + flags if a different word was said."""
    check_or_raise("speaking", student.id)
    data = await file.read()
    if not data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="The audio file is empty")
    suffix = ".webm"
    if file.filename and "." in file.filename:
        suffix = "." + file.filename.rsplit(".", 1)[-1].lower()
    language = await get_default_language(db)
    result = await assess_word_pronunciation(
        db, student_id=student.id, language_id=language.id, word=word, data=data, suffix=suffix
    )
    await db.commit()
    return result


@router.get("/vocabulary/challenge", response_model=VocabularyChallengeOut)
async def vocabulary_challenge(
    student: User = Depends(require_language_learning_ready()),
    db: AsyncSession = Depends(get_db),
):
    """Daily fill-in-the-blanks challenge built from the student's due vocabulary (English only)."""
    return await generate_vocabulary_challenge(db, student_id=student.id)


@router.post("/vocabulary/challenge/submit", response_model=VocabularyChallengeSubmitOut)
async def vocabulary_challenge_submit(
    body: VocabularyChallengeSubmitIn,
    student: User = Depends(require_language_learning_ready()),
    db: AsyncSession = Depends(get_db),
):
    """Record a finished daily challenge as learner-model evidence (source='daily')."""
    result = await submit_vocabulary_challenge(
        db, student_id=student.id, results=[r.model_dump() for r in body.results]
    )
    await db.commit()
    return result


@router.get("/vocabulary/quiz/daily", response_model=VocabQuizOut)
async def vocabulary_quiz_daily(
    student: User = Depends(require_language_learning_ready()),
    db: AsyncSession = Depends(get_db),
):
    """Daily spelling + pronunciation quiz over words the student has ALREADY learned —
    today's served batch, topped up with due/learned words if the batch was short."""
    language = await get_default_language(db)
    return await build_daily_quiz(db, student_id=student.id, language_id=language.id)


@router.post("/vocabulary/quiz/daily/spelling", response_model=VocabQuizSpellingOut)
async def vocabulary_quiz_daily_spelling(
    body: VocabQuizSpellingIn,
    student: User = Depends(require_language_learning_ready()),
    db: AsyncSession = Depends(get_db),
):
    """Grade one spelling guess server-side (the target word is never sent to the client
    beforehand) and reveal the correct word."""
    language = await get_default_language(db)
    return await check_quiz_spelling(
        db, language_id=language.id, content_id=body.item_id, guess=body.guess
    )


@router.post("/vocabulary/quiz/daily/complete", response_model=VocabQuizCompleteOut)
async def vocabulary_quiz_daily_complete(
    body: VocabQuizCompleteIn,
    student: User = Depends(require_language_learning_ready()),
    db: AsyncSession = Depends(get_db),
):
    """Record the finished quiz as learner-model evidence (never touches the SM-2 schedule)."""
    language = await get_default_language(db)
    result = await record_quiz_completion(
        db, student_id=student.id, language_id=language.id,
        results=[r.model_dump() for r in body.results],
    )
    await db.commit()
    return result


@router.get("/learner-model/profile", response_model=LearnerModelProfileOut)
async def learner_model_profile(
    student: User = Depends(require_language_learning_ready()),
    db: AsyncSession = Depends(get_db),
):
    """Unified learner-model snapshot: component mastery, per-skill confidence, due-review count."""
    language = await get_default_language(db)
    service = LanguageLearnerModelService(db)
    components = await service.get_component_profile(student_id=student.id, language_id=language.id)
    skill_confidence = await service.get_skill_confidence(student_id=student.id, language_id=language.id)
    due = await service.get_due_reviews(student_id=student.id, language_id=language.id)
    return {"components": components, "skill_confidence": skill_confidence, "due_count": len(due)}


@router.get("/learner-model/practice", response_model=LearnerPracticeSetOut)
async def learner_model_practice(
    count: int = 4,
    skill: str = "",
    student: User = Depends(require_language_learning_ready()),
    db: AsyncSession = Depends(get_db),
):
    """Adaptive 'smart review': MCQs targeting the learner's weakest knowledge components.

    Optional ``skill`` drills one skill (reading/listening/writing/speaking).
    """
    return await generate_practice_set(db, student_id=student.id, count=count, skill=skill)


@router.post("/learner-model/practice/submit", response_model=LearnerPracticeSubmitOut)
async def learner_model_practice_submit(
    body: LearnerPracticeSubmitIn,
    student: User = Depends(require_language_learning_ready()),
    db: AsyncSession = Depends(get_db),
):
    """Record answered smart-review questions as learner-model evidence (source='daily')."""
    result = await submit_practice(
        db, student_id=student.id, results=[r.model_dump() for r in body.results]
    )
    await db.commit()
    return result


@router.get("/dictionary", response_model=DictionarySearchOut)
async def dictionary_search(
    q: str = "",
    student: User = Depends(require_active_language_subscription()),
):
    """Global English dictionary (WordNet): word definitions + synonyms + prefix suggestions."""
    from fastapi.concurrency import run_in_threadpool

    from app.services.language_dictionary_service import search

    return await run_in_threadpool(search, q)


@router.get("/vocabulary/{content_id}", response_model=VocabularyCardOut)
async def vocabulary_detail(
    content_id: int,
    student: User = Depends(require_language_learning_ready()),
    db: AsyncSession = Depends(get_db),
):
    return await get_vocabulary_card(db, student_id=student.id, content_id=content_id)


@router.post("/vocabulary/{content_id}/review", response_model=VocabularyCardOut)
async def vocabulary_review(
    content_id: int,
    body: VocabularyReviewIn,
    student: User = Depends(require_language_learning_ready()),
    db: AsyncSession = Depends(get_db),
):
    result = await review_vocabulary(db, student_id=student.id, content_id=content_id, quality=body.quality)
    await db.commit()
    return result


@router.get("/writing", response_model=WritingListOut)
async def writing_list(
    student: User = Depends(require_language_learning_ready()),
    db: AsyncSession = Depends(get_db),
):
    payload = await list_writing(db, student_id=student.id)
    await db.commit()
    return payload


@router.get("/writing/journey", response_model=WritingJourneyBundleOut)
async def writing_journey(
    student: User = Depends(require_language_learning_ready()),
    db: AsyncSession = Depends(get_db),
):
    language = await get_default_language(db)
    return await build_writing_journey_bundle(db, student_id=student.id, language_id=language.id)


@router.post("/writing/generate", response_model=WritingGenerateOut)
async def writing_generate(
    body: WritingGenerateIn,
    student: User = Depends(require_language_learning_ready()),
    db: AsyncSession = Depends(get_db),
):
    try:
        goal = WritingGoal(body.goal) if body.goal else None
        official_cefr = OfficialWritingCEFR(body.official_cefr) if body.official_cefr else None
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "invalid_writing_generation_request", "message": str(exc)},
        ) from exc
    result = await generate_writing_lesson_for_student(
        db,
        student_id=student.id,
        goal=goal,
        chain_id=body.chain_id,
        node_id=body.node_id,
        official_cefr=official_cefr,
    )
    await db.commit()
    return WritingGenerateOut.model_validate(result)


@router.post("/writing/{content_item_id}/draft", response_model=WritingDraftSubmitOut)
async def writing_draft_submit(
    content_item_id: int,
    body: WritingDraftSubmitIn,
    student: User = Depends(require_language_learning_ready()),
    db: AsyncSession = Depends(get_db),
):
    language = await get_default_language(db)
    result = await submit_writing_draft_for_evaluation(
        db,
        student_id=student.id,
        content_item_id=content_item_id,
        draft_text=body.draft_text,
        complete_if_ready=body.complete_if_ready,
        language_id=language.id,
    )
    await db.commit()
    return WritingDraftSubmitOut.model_validate(result)


@router.get("/writing/{prompt_id}", response_model=WritingPromptOut)
async def writing_detail(
    prompt_id: int,
    student: User = Depends(require_language_learning_ready()),
    db: AsyncSession = Depends(get_db),
):
    return await get_writing_prompt(db, student_id=student.id, prompt_id=prompt_id)


@router.post("/writing/{prompt_id}/submit", response_model=WritingSubmitOut)
async def writing_submit(
    prompt_id: int,
    body: WritingSubmitIn,
    student: User = Depends(require_language_learning_ready()),
    db: AsyncSession = Depends(get_db),
):
    result = await submit_writing(
        db, student_id=student.id, prompt_id=prompt_id, response_text=body.response_text
    )
    await db.commit()
    return WritingSubmitOut(**result)


@router.get("/speaking", response_model=SpeakingListOut)
async def speaking_list(
    student: User = Depends(require_language_learning_ready()),
    db: AsyncSession = Depends(get_db),
):
    return await list_speaking(db, student_id=student.id)


@router.get("/speaking/conversation", response_model=SpeakingConversationStateOut)
async def speaking_conversation_state(
    student: User = Depends(require_language_learning_ready()),
    db: AsyncSession = Depends(get_db),
):
    payload = await get_conversation_state(db, student_id=student.id)
    await db.commit()
    return SpeakingConversationStateOut(**payload)


@router.get("/speaking/conversation/progress", response_model=SpeakingConversationProgressOut)
async def speaking_conversation_progress(
    student: User = Depends(require_language_learning_ready()),
    db: AsyncSession = Depends(get_db),
):
    payload = await get_conversation_progress(db, student_id=student.id)
    await db.commit()
    return SpeakingConversationProgressOut(**payload)


@router.post("/speaking/conversation/turn", response_model=SpeakingConversationTurnOut)
async def speaking_conversation_turn(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    duration_seconds: int | None = Form(default=None),
    tts_voice: str | None = Form(default=None),
    focus: str | None = Form(default=None),
    student: User = Depends(require_language_learning_ready()),
    db: AsyncSession = Depends(get_db),
):
    check_or_raise("speaking", student.id)  # per-user rate limit on the costly audio turn
    result = await process_conversation_turn(
        db,
        student_id=student.id,
        file=file,
        duration_seconds=duration_seconds,
        voice=tts_voice,
        focus=focus,
    )
    bg = result.pop("_background_tts", None)
    result.pop("turn_id", None)
    await db.commit()
    if bg:
        from app.services.language_conversation_tts_task import generate_conversation_reply_audio

        background_tasks.add_task(generate_conversation_reply_audio, **bg)
    return SpeakingConversationTurnOut(**result)


@router.get("/speaking/conversation/sessions")
async def speaking_conversation_sessions(
    student: User = Depends(require_language_learning_ready()),
    db: AsyncSession = Depends(get_db),
):
    return await list_conversation_sessions(db, student_id=student.id)


@router.get("/speaking/conversation/sessions/{session_id}")
async def speaking_conversation_session_detail(
    session_id: int,
    student: User = Depends(require_language_learning_ready()),
    db: AsyncSession = Depends(get_db),
):
    return await get_conversation_session_detail(db, student_id=student.id, session_id=session_id)


@router.get("/speaking/conversation/turn/{turn_id}/explanation")
async def speaking_conversation_turn_explanation(
    turn_id: int,
    student: User = Depends(require_language_learning_ready()),
    db: AsyncSession = Depends(get_db),
):
    result = await get_turn_explanation(db, student_id=student.id, turn_id=turn_id)
    await db.commit()
    return result


@router.delete("/speaking/conversation", response_model=SpeakingConversationResetOut)
async def speaking_conversation_reset(
    student: User = Depends(require_language_learning_ready()),
    db: AsyncSession = Depends(get_db),
):
    result = await reset_conversation(db, student_id=student.id)
    await db.commit()
    return SpeakingConversationResetOut(**result)


class ScenarioTurnIn(BaseModel):
    session_id: int
    text: str


class ScenarioEndIn(BaseModel):
    session_id: int


@router.get("/speaking/scenarios")
async def speaking_scenarios(
    student: User = Depends(require_language_learning_ready()),
    db: AsyncSession = Depends(get_db),
):
    language = await get_default_language(db)
    scenarios = await list_scenarios(db, student_id=student.id, language_id=language.id)
    return {"scenarios": scenarios}


@router.get("/speaking/scenarios/sessions")
async def speaking_scenario_sessions(
    student: User = Depends(require_language_learning_ready()),
    db: AsyncSession = Depends(get_db),
):
    language = await get_default_language(db)
    return await list_scenario_sessions(db, student_id=student.id, language_id=language.id)


@router.post("/speaking/scenarios/{scenario_id}/start")
async def speaking_scenario_start(
    scenario_id: int,
    student: User = Depends(require_language_learning_ready()),
    db: AsyncSession = Depends(get_db),
):
    language = await get_default_language(db)
    result = await start_scenario_session(
        db, student_id=student.id, language_id=language.id, scenario_id=scenario_id
    )
    await db.commit()
    return result


@router.get("/speaking/scenarios/session/{session_id}")
async def speaking_scenario_session(
    session_id: int,
    student: User = Depends(require_language_learning_ready()),
    db: AsyncSession = Depends(get_db),
):
    return await get_scenario_session(db, session_id=session_id, student_id=student.id)


@router.post("/speaking/scenarios/turn")
async def speaking_scenario_turn(
    body: ScenarioTurnIn,
    student: User = Depends(require_language_learning_ready()),
    db: AsyncSession = Depends(get_db),
):
    language = await get_default_language(db)
    result = await process_scenario_turn(
        db, session_id=body.session_id, student_id=student.id, user_text=body.text, language_id=language.id
    )
    await db.commit()
    return result


@router.post("/speaking/scenarios/turn/voice")
async def speaking_scenario_turn_voice(
    session_id: int = Form(...),
    file: UploadFile = File(...),
    student: User = Depends(require_language_learning_ready()),
    db: AsyncSession = Depends(get_db),
):
    """Voice turn for a role-play scenario: transcribe the audio, then run the same
    text turn pipeline so vocabulary/reply still respect the student's CEFR level."""
    language = await get_default_language(db)
    data = await file.read()
    if not data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="The audio file is empty")
    suffix = ".webm"
    if file.filename and "." in file.filename:
        suffix = "." + file.filename.rsplit(".", 1)[-1].lower()
    stt = await transcribe_english_audio(data, suffix=suffix)
    transcript = (stt.text or "").strip()
    if not transcript:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Could not understand the audio — please try again.",
        )
    result = await process_scenario_turn(
        db, session_id=session_id, student_id=student.id, user_text=transcript, language_id=language.id
    )
    await db.commit()
    result["transcript"] = transcript
    return result


@router.post("/speaking/scenarios/end")
async def speaking_scenario_end(
    body: ScenarioEndIn,
    student: User = Depends(require_language_learning_ready()),
    db: AsyncSession = Depends(get_db),
):
    result = await end_session_with_feedback(db, session_id=body.session_id, student_id=student.id)
    await db.commit()
    return result


@router.get("/speaking/shadow/sentences", response_model=ShadowSentenceListOut)
async def shadow_sentences(
    focus: str | None = None,
    student: User = Depends(require_language_learning_ready()),
    db: AsyncSession = Depends(get_db),
):
    payload = await list_shadow_sentences(db, student_id=student.id, focus=focus)
    return ShadowSentenceListOut(**payload)


@router.post("/speaking/shadow", response_model=ShadowSubmitOut)
async def shadow_submit(
    target_text: str = Form(...),
    file: UploadFile = File(...),
    student: User = Depends(require_language_learning_ready()),
    db: AsyncSession = Depends(get_db),
):
    result = await submit_shadow(db, student_id=student.id, target_text=target_text, file=file)
    await db.commit()
    return ShadowSubmitOut(**result)


@router.get("/speaking/{prompt_id}", response_model=SpeakingPromptOut)
async def speaking_detail(
    prompt_id: int,
    student: User = Depends(require_language_learning_ready()),
    db: AsyncSession = Depends(get_db),
):
    return await get_speaking_prompt(db, student_id=student.id, prompt_id=prompt_id)


@router.post("/speaking/{prompt_id}/upload", response_model=PlacementSpeakingUploadOut)
async def speaking_upload(
    prompt_id: int,
    file: UploadFile = File(...),
    student: User = Depends(require_language_learning_ready()),
    db: AsyncSession = Depends(get_db),
):
    media = await upload_speaking_recording(
        db, student_id=student.id, prompt_id=prompt_id, file=file
    )
    await db.commit()
    return PlacementSpeakingUploadOut(ok=True, media_object_id=media["media_object_id"], public_url=media["public_url"])


@router.post("/speaking/{prompt_id}/submit", response_model=SpeakingSubmitOut)
async def speaking_submit(
    prompt_id: int,
    body: SpeakingSubmitIn,
    student: User = Depends(require_language_learning_ready()),
    db: AsyncSession = Depends(get_db),
):
    result = await submit_speaking(
        db,
        student_id=student.id,
        prompt_id=prompt_id,
        media_object_id=body.media_object_id,
        duration_seconds=body.duration_seconds,
    )
    await db.commit()
    return SpeakingSubmitOut(**result)


@router.get("/certificates", response_model=LanguageCertificateListOut)
async def certificates_list(
    student: User = Depends(require_language_learning_ready()),
    db: AsyncSession = Depends(get_db),
):
    payload = await list_student_certificates(db, student_id=student.id)
    await db.commit()
    return LanguageCertificateListOut(**payload)
