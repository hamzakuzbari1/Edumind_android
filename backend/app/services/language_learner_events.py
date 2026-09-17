"""Bridge real feature activity into the unified Learner Model.

Every graded feature (reading, listening, writing, speaking, vocabulary) reports its result
here, and this module turns it into one or more `LearningEvent`s fed through
`LanguageLearnerModelService.process_event`. This is the *only* place feature code touches the
learner model, so the mapping from "what the learner just did" to "which knowledge component"
lives in one spot.

Contract for callers:
  * Best-effort — every entry point swallows and logs its own errors so it can NEVER break the
    host submit flow.
  * Non-committing — events are flushed, not committed; the caller's request transaction
    (router-level ``db.commit()``) finalizes them atomically with the rest of the submit.
  * Non-destructive — ongoing practice does NOT overwrite the headline skill CEFR on
    LanguageAnalytics (the existing per-skill nudge/refresh logic owns that). The learner model
    just accumulates component mastery, confidence and the spaced-repetition schedule.
"""

from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.language.enums import LanguageSkill
from app.services.language_learner_model_service import LanguageLearnerModelService, LearningEvent

logger = logging.getLogger(__name__)

# --- question "type" (emitted by the lesson generator) -> knowledge component ---------------
# Generator vocabulary: main_idea | detail | inference | vocab_in_context | tone
_READING_TYPE_TO_COMPONENT = {
    "main_idea": "reading.skim_gist",
    "gist": "reading.skim_gist",
    "heading_match": "reading.skim_gist",  # matching headings = grasping each part's gist
    "detail": "reading.scan_detail",
    "sentence_completion": "reading.scan_detail",  # locate the detail that fills the gap
    "inference": "reading.infer_meaning",
    "true_false_notgiven": "reading.infer_meaning",  # judging support/contradiction = inference
    "vocab_in_context": "reading.vocab_in_context",
    "vocab": "reading.vocab_in_context",
    "purpose": "reading.authors_purpose",
    "tone": "reading.implicit_attitude",
    "attitude": "reading.implicit_attitude",
}
_LISTENING_TYPE_TO_COMPONENT = {
    "main_idea": "listening.main_idea",
    "gist": "listening.main_idea",
    "detail": "listening.specific_info",
    "specific_info": "listening.specific_info",
    "sentence_completion": "listening.specific_info",  # catch the spoken detail that fills the gap
    "inference": "listening.inference",
    "true_false_notgiven": "listening.inference",  # judging support/contradiction = inference
    "vocab_in_context": "listening.speaker_opinion",
    "opinion": "listening.speaker_opinion",
    "tone": "listening.nuance_tone",
    "attitude": "listening.nuance_tone",
}

# --- CEFR-level fallbacks (used when a question carries no usable type, and for writing/speaking
#     where the evidence is a single holistic score at the lesson's level) --------------------
_READING_LEVEL_TO_COMPONENT = {
    "A1": "reading.scan_detail", "A2": "reading.scan_detail", "B1": "reading.infer_meaning",
    "B2": "reading.authors_purpose", "C1": "reading.implicit_attitude", "C2": "reading.implicit_attitude",
}
_LISTENING_LEVEL_TO_COMPONENT = {
    "A1": "listening.specific_info", "A2": "listening.specific_info", "B1": "listening.inference",
    "B2": "listening.relationship_context", "C1": "listening.nuance_tone", "C2": "listening.nuance_tone",
}
_WRITING_LEVEL_TO_COMPONENT = {
    "A1": "grammar.present_simple", "A2": "grammar.past_tenses", "B1": "grammar.present_perfect",
    "B2": "grammar.conditionals", "C1": "writing.formal_register", "C2": "writing.formal_register",
}
_SPEAKING_LEVEL_TO_COMPONENT = {
    "A1": "speaking.intro_personal", "A2": "speaking.describe_routine", "B1": "speaking.justify_opinion",
    "B2": "speaking.hypothetical", "C1": "speaking.fluency_discourse", "C2": "speaking.fluency_discourse",
}

_TYPE_MAP = {LanguageSkill.reading: _READING_TYPE_TO_COMPONENT, LanguageSkill.listening: _LISTENING_TYPE_TO_COMPONENT}
_LEVEL_MAP = {
    LanguageSkill.reading: _READING_LEVEL_TO_COMPONENT,
    LanguageSkill.listening: _LISTENING_LEVEL_TO_COMPONENT,
    LanguageSkill.writing: _WRITING_LEVEL_TO_COMPONENT,
    LanguageSkill.speaking: _SPEAKING_LEVEL_TO_COMPONENT,
}

# Vocabulary practice always exercises the "word meaning in context" component.
_VOCAB_COMPONENT = "reading.vocab_in_context"


def _level_str(level) -> str:
    """Normalize an item.level (enum | str | None) to a CEFR string, defaulting to A2."""
    if level is None:
        return "A2"
    value = getattr(level, "value", level)
    return str(value).upper() if value else "A2"


def component_for_question(skill: LanguageSkill, *, qtype: str | None, level: str) -> str | None:
    """Resolve a lesson question (its `type`, falling back to the lesson level) to a component code."""
    by_type = _TYPE_MAP.get(skill, {})
    code = by_type.get((qtype or "").strip().lower())
    if code:
        return code
    return _LEVEL_MAP.get(skill, {}).get(level)


def _quality_from_percent(score_percent: float) -> int:
    """Map a 0-100 holistic score to an SM-2 recall grade 0-5."""
    return max(0, min(5, round(float(score_percent) / 20.0)))


async def record_lesson_questions(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
    skill: LanguageSkill,
    level,
    question_results: list[dict] | None,
    source: str,
) -> int:
    """Feed per-question reading/listening results into the learner model.

    ``question_results``: ``[{"type": str, "is_correct": bool}, ...]``. Returns #events recorded.
    """
    results = question_results or []
    if not results:
        return 0
    level_str = _level_str(level)
    try:
        service = LanguageLearnerModelService(db)
        recorded = 0
        for r in results:
            code = component_for_question(skill, qtype=r.get("type"), level=level_str)
            if not code:
                continue
            await service.process_event(
                LearningEvent(
                    student_id=student_id, language_id=language_id, component_code=code,
                    correct=bool(r.get("is_correct")), source=source,
                ),
                commit=False, sync_cefr=False,
            )
            recorded += 1
        return recorded
    except Exception as exc:  # never break the host submit flow
        logger.warning("record_lesson_questions failed (%s, student=%s): %s", skill, student_id, exc)
        return 0


async def record_scored_practice(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
    skill: LanguageSkill,
    level,
    score_percent: float,
    source: str,
) -> bool:
    """Feed a single holistic score (writing/speaking) into the learner model. Returns success."""
    level_str = _level_str(level)
    code = _LEVEL_MAP.get(skill, {}).get(level_str)
    if not code:
        return False
    try:
        await LanguageLearnerModelService(db).process_event(
            LearningEvent(
                student_id=student_id, language_id=language_id, component_code=code,
                correct=float(score_percent) >= 60.0, source=source,
                response_quality=_quality_from_percent(score_percent),
            ),
            commit=False, sync_cefr=False,
        )
        return True
    except Exception as exc:
        logger.warning("record_scored_practice failed (%s, student=%s): %s", skill, student_id, exc)
        return False


async def record_speaking_scores(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
    level,
    scores: dict | None,
    source: str = "speaking",
) -> bool:
    """Feed a speaking turn/session (a dict of 0-100 sub-scores) into the model as one event.

    Averages the numeric sub-scores (fluency/grammar/vocabulary/…) into a single holistic score and
    records it against the speaking component for ``level``.
    """
    nums = [v for v in (scores or {}).values() if isinstance(v, (int, float))]
    if not nums:
        return False
    return await record_scored_practice(
        db, student_id=student_id, language_id=language_id, skill=LanguageSkill.speaking,
        level=level, score_percent=sum(nums) / len(nums), source=source,
    )


async def record_component_results(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
    results: list[dict] | None,
) -> int:
    """Feed adaptive-practice answers, each already tagged with its component, into the model.

    ``results``: ``[{"component_code": str, "correct": bool}, ...]`` (source ``daily``). Returns
    #events recorded.
    """
    items = results or []
    if not items:
        return 0
    try:
        service = LanguageLearnerModelService(db)
        recorded = 0
        for r in items:
            code = r.get("component_code")
            if not code:
                continue
            await service.process_event(
                LearningEvent(
                    student_id=student_id, language_id=language_id, component_code=str(code),
                    correct=bool(r.get("correct")), source="daily",
                ),
                commit=False, sync_cefr=False,
            )
            recorded += 1
        return recorded
    except Exception as exc:
        logger.warning("record_component_results failed (student=%s): %s", student_id, exc)
        return 0


async def record_challenge_results(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
    results: list[dict] | None,
) -> int:
    """Feed daily fill-in-the-blanks results into the learner model. Returns #events recorded.

    ``results``: ``[{"word": str, "correct": bool}, ...]`` — one per blank. Each blank is a separate
    recall test, recorded against the vocabulary component with the ``daily`` source.
    """
    items = results or []
    if not items:
        return 0
    try:
        service = LanguageLearnerModelService(db)
        recorded = 0
        for r in items:
            await service.process_event(
                LearningEvent(
                    student_id=student_id, language_id=language_id, component_code=_VOCAB_COMPONENT,
                    correct=bool(r.get("correct")), source="daily",
                ),
                commit=False, sync_cefr=False,
            )
            recorded += 1
        return recorded
    except Exception as exc:
        logger.warning("record_challenge_results failed (student=%s): %s", student_id, exc)
        return 0


async def record_vocabulary_review(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
    quality: int,
) -> bool:
    """Feed one SM-2 vocabulary review (grade 0-5) into the learner model. Returns success."""
    try:
        await LanguageLearnerModelService(db).process_event(
            LearningEvent(
                student_id=student_id, language_id=language_id, component_code=_VOCAB_COMPONENT,
                correct=int(quality) >= 3, source="vocab", response_quality=int(quality),
            ),
            commit=False, sync_cefr=False,
        )
        return True
    except Exception as exc:
        logger.warning("record_vocabulary_review failed (student=%s): %s", student_id, exc)
        return False
