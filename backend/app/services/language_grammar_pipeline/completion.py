"""Wave B completion orchestration — Evidence → Mastery → Progression sync.

Durable learner writes happen ONLY after successful activity completion.
Generate-only / lesson-start paths must never call this module.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.language_grammar.enums import (
    GrammarEvidenceSourceSkill,
    GrammarMasteryState,
    GrammarObservationType,
)
from app.services.language_grammar.id_canon import assert_canonical_grammar_id
from app.services.language_grammar_evidence.types import (
    GrammarEvidenceBatch,
    GrammarEvidenceObservation,
)
from app.services.language_grammar_evidence.validation import validate_batch
from app.services.language_grammar_integration import sync_completed_topics_async
from app.services.language_grammar_integration.types import GrammarCompletedSyncResult
from app.services.language_grammar_mastery import (
    apply_evidence_and_persist,
    get_grammar_mastery_snapshot,
)
from app.services.language_grammar_mastery.types import GrammarMasterySnapshot
from app.services.language_grammar_pipeline.errors import PipelineValidationError
from app.services.language_grammar_progression.service import get_grammar_progression_snapshot
from app.services.language_grammar_progression.types import GrammarProgressionSnapshot


def _as_of() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True, slots=True)
class ActivityCompletionRequest:
    """One completed learner activity contributing evidence to a grammar node."""

    student_id: int
    language_id: int
    grammar_id: str
    skill: GrammarEvidenceSourceSkill | str
    score: float
    activity_id: str = ""
    activity_type: str = ""
    lesson_id: str = ""
    confidence: float | None = None
    context: str = ""
    observation_id: str = ""
    observed_at: str = ""
    observation_type: GrammarObservationType = GrammarObservationType.summative
    attempt_count: int = 1
    correct_count: int | None = None


@dataclass(frozen=True, slots=True)
class ActivityCompletionResult:
    """Outcome of durable Evidence → Mastery → Progression sync."""

    evidence_batch: GrammarEvidenceBatch
    mastery: GrammarMasterySnapshot
    progression: GrammarProgressionSnapshot
    completed_sync: GrammarCompletedSyncResult
    grammar_id: str
    mastery_state: str
    overall_mastery: float
    unlocked_ids: tuple[str, ...]
    current_grammar_id: str | None
    next_grammar_id: str | None
    evidence_was_new: bool


def _coerce_skill(skill: GrammarEvidenceSourceSkill | str) -> GrammarEvidenceSourceSkill:
    if isinstance(skill, GrammarEvidenceSourceSkill):
        return skill
    key = str(skill or "").strip().lower()
    if key == "grammar":
        key = "grammar_lesson"
    try:
        return GrammarEvidenceSourceSkill(key)
    except ValueError as exc:
        raise PipelineValidationError(
            "invalid_source_skill",
            f"Unsupported evidence source skill: {skill!r}",
        ) from exc


def build_completion_observation(request: ActivityCompletionRequest) -> GrammarEvidenceObservation:
    """Build a validated-shape observation from a completed activity (no DB writes)."""
    gid = assert_canonical_grammar_id(request.grammar_id)
    skill = _coerce_skill(request.skill)
    score = max(0.0, min(100.0, float(request.score)))
    attempts = max(1, int(request.attempt_count))
    if request.correct_count is None:
        correct = attempts if score >= 70.0 else (1 if score >= 40.0 else 0)
        correct = min(attempts, correct)
    else:
        correct = max(0, min(attempts, int(request.correct_count)))

    confidence = request.confidence
    if confidence is None:
        confidence = max(0.35, min(1.0, score / 100.0))

    activity_id = (request.activity_id or "").strip() or f"act_{uuid4().hex[:10]}"
    lesson_id = (request.lesson_id or "").strip()
    activity_type = (request.activity_type or "").strip() or skill.value
    context = (request.context or "").strip() or f"{activity_type}:{activity_id}"
    if lesson_id and lesson_id not in context:
        context = f"{context}|lesson:{lesson_id}"

    observation_id = (request.observation_id or "").strip() or f"ev_{activity_id}_{gid}"
    observed_at = (request.observed_at or "").strip() or _as_of()

    return GrammarEvidenceObservation(
        observation_id=observation_id,
        grammar_id=gid,
        context=context,
        attempt_count=attempts,
        correct_count=correct,
        observation_type=request.observation_type,
        source_skill=skill,
        student_id=int(request.student_id),
        language_id=int(request.language_id),
        observed_at=observed_at,
        confidence=float(confidence),
        understanding_signal=score,
        accuracy_signal=score,
        fluency_signal=max(0.0, score - 5.0),
        retention_signal=max(0.0, score - 10.0),
        activity_id=activity_id,
        activity_type=activity_type,
        lesson_id=lesson_id,
        score=score,
    )


async def apply_activity_completion_async(
    db: AsyncSession,
    request: ActivityCompletionRequest,
) -> ActivityCompletionResult:
    """Persist evidence via Mastery, then sync Progression unlocks.

    Sole durable Wave B write path for completed activities across skills.
    """
    if request.student_id <= 0 or request.language_id <= 0:
        raise PipelineValidationError("invalid_student", "student_id and language_id are required")

    observation = build_completion_observation(request)
    batch = GrammarEvidenceBatch(observations=(observation,))
    validated = validate_batch(batch)
    if not validated.valid:
        raise PipelineValidationError("invalid_evidence", "; ".join(validated.issues))
    evidence_batch = GrammarEvidenceBatch(observations=validated.observations)

    prior = await get_grammar_mastery_snapshot(
        db, student_id=request.student_id, language_id=request.language_id
    )
    already_applied = observation.observation_id in prior.applied_observation_ids

    mastery = await apply_evidence_and_persist(
        db,
        student_id=request.student_id,
        language_id=request.language_id,
        batch=evidence_batch,
    )
    completed_sync = await sync_completed_topics_async(
        db,
        student_id=request.student_id,
        language_id=request.language_id,
    )
    progression = await get_grammar_progression_snapshot(
        db,
        student_id=request.student_id,
        language_id=request.language_id,
        for_selection=True,
    )

    record = mastery.record_for(observation.grammar_id)
    return ActivityCompletionResult(
        evidence_batch=evidence_batch,
        mastery=mastery,
        progression=progression,
        completed_sync=completed_sync,
        grammar_id=observation.grammar_id,
        mastery_state=(record.state.value if record else GrammarMasteryState.unknown.value),
        overall_mastery=float(record.dimensions.overall_mastery) if record else 0.0,
        unlocked_ids=tuple(sorted(progression.unlocked_ids)),
        current_grammar_id=progression.current_grammar_id,
        next_grammar_id=progression.next_grammar_id,
        evidence_was_new=not already_applied,
    )
