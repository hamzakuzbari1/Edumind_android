"""Read-only loader for StudentSpeakingLiveContext (S7.6)."""

from __future__ import annotations

import hashlib

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.language.conversation import LanguageSpeakingConversationTurn
from app.models.language.progress import LanguageSpeakingProgress
from app.models.language.progression import LanguageProgression
from app.services.language_speaking_curriculum.skill_catalog import SPEAKING_SKILL_GRAPH
from app.services.language_speaking_coach.live_context import assemble_student_speaking_live_context
from app.services.language_speaking_coach.types import StudentSpeakingLiveContext
from app.services.language_speaking_evaluator.facts_deserialize import evaluation_result_from_dict
from app.services.language_speaking_evaluator.evaluation_result import SpeakingEvaluationEngineResult
from app.services.language_speaking_knowledge_model.storage import (
    knowledge_model_from_speaking_bucket,
    speaking_bucket_from_payload,
)

_STUDENT_REF_SALT = "eduspark-speaking-live-v1"
_ENGINE_RESULT_KEY = "engine_result"


def opaque_student_reference(*, student_id: int) -> str:
    """Session-safe opaque reference — no email/PII."""
    digest = hashlib.sha256(f"{_STUDENT_REF_SALT}:{student_id}".encode()).hexdigest()
    return f"spk-{digest[:16]}"


async def _load_knowledge_model(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
):
    row = await db.get(LanguageProgression, {"student_id": student_id, "language_id": language_id})
    payload = dict(row.promotion_readiness_json or {}) if row else {}
    speaking_bucket = speaking_bucket_from_payload(payload)
    return knowledge_model_from_speaking_bucket(
        speaking_bucket,
        student_id=student_id,
        language_id=language_id,
    )


async def _load_latest_evaluation(
    db: AsyncSession,
    *,
    student_id: int,
) -> SpeakingEvaluationEngineResult | None:
    turn_result = await db.execute(
        select(LanguageSpeakingConversationTurn)
        .where(LanguageSpeakingConversationTurn.student_id == student_id)
        .order_by(LanguageSpeakingConversationTurn.created_at.desc())
        .limit(1)
    )
    turn = turn_result.scalar_one_or_none()
    if turn and isinstance(turn.evaluation_json, dict):
        raw = turn.evaluation_json.get(_ENGINE_RESULT_KEY) or turn.evaluation_json
        if isinstance(raw, dict):
            parsed = evaluation_result_from_dict(raw)
            if parsed is not None:
                return parsed

    progress_result = await db.execute(
        select(LanguageSpeakingProgress)
        .where(LanguageSpeakingProgress.student_id == student_id)
        .order_by(LanguageSpeakingProgress.submitted_at.desc())
        .limit(1)
    )
    progress = progress_result.scalar_one_or_none()
    if progress and isinstance(progress.ai_evaluation_json, dict):
        raw = progress.ai_evaluation_json.get(_ENGINE_RESULT_KEY)
        if isinstance(raw, dict):
            return evaluation_result_from_dict(raw)
    return None


async def load_student_speaking_live_context(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int = 1,
    speaking_goal: str = "general_english",
) -> StudentSpeakingLiveContext:
    """Load canonical read-only context for authenticated student."""
    km = await _load_knowledge_model(db, student_id=student_id, language_id=language_id)
    evaluation = await _load_latest_evaluation(db, student_id=student_id)
    return assemble_student_speaking_live_context(
        student_reference=opaque_student_reference(student_id=student_id),
        speaking_goal=speaking_goal,
        knowledge_model=km,
        skill_graph=SPEAKING_SKILL_GRAPH,
        latest_evaluation=evaluation,
    )
