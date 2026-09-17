"""S7 full-turn evaluation orchestrator — S4 → S5 → S6 → hybrid evaluator."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.services.language_speaking_audio_frontend.artifacts import SpeakingAudioArtifact
from app.services.language_speaking_evaluator.engine import evaluate_speaking_turn, new_evaluation_context
from app.services.language_speaking_evaluator.evaluation_result import SpeakingEvaluationEngineResult
from app.services.language_speaking_evaluator.facts_deserialize import evaluation_result_from_dict
from app.services.language_speaking_evaluator.input_types import (
    SpeakingEvaluationInput,
    SpeakingGoalContext,
    SpeakingOfficialCefrContext,
    SpeakingTaskContext,
)
from app.services.language_speaking_evaluation_runtime.audio_runtime import process_speaking_audio
from app.services.language_speaking_evaluation_runtime.pronunciation_runtime import process_speaking_pronunciation
from app.services.language_speaking_evaluation_runtime.prosody_runtime import process_speaking_prosody

LANGUAGE_SPEAKING_EVALUATION_PIPELINE_VERSION = "7.0.0"
SPEAKING_ENGINE_RESULT_KEY = "engine_result"


@dataclass(frozen=True, slots=True)
class SpeakingEvaluationTurnResult:
    """Canonical turn evaluation output for persistence/API layers."""

    success: bool
    evaluation: SpeakingEvaluationEngineResult | None = None
    persistence_dict: dict[str, object] = field(default_factory=dict)
    bundle_id: str = ""
    processing_warnings: tuple[str, ...] = ()
    error: str = ""
    pipeline_version: str = LANGUAGE_SPEAKING_EVALUATION_PIPELINE_VERSION


def _provenance_from_bundle(bundle) -> tuple[dict[str, object], ...]:
    if bundle is None:
        return ()
    return tuple(p.to_persistence_dict() for p in bundle.provider_provenance)


def _build_input_from_runtimes(*, audio_result, pron_result, pros_result) -> SpeakingEvaluationInput:
    bundle = pros_result.bundle or pron_result.bundle or audio_result.bundle
    transcript_text = ""
    if bundle and bundle.transcript:
        transcript_text = bundle.transcript.text or ""
    elif audio_result.bundle and audio_result.bundle.transcript:
        transcript_text = audio_result.bundle.transcript.text or ""

    availability = dict(bundle.evidence_availability) if bundle else {}
    ref_ids: list[str] = []
    if bundle:
        ref_ids.append(bundle.evidence_bundle_id)
    warnings: list[str] = []
    warnings.extend(audio_result.processing_warnings)
    warnings.extend(pron_result.processing_warnings)
    warnings.extend(pros_result.processing_warnings)

    reliability = 0.0
    if pron_result.pronunciation:
        reliability = max(reliability, pron_result.pronunciation.evidence_reliability)
    if pros_result.prosody:
        reliability = max(reliability, pros_result.prosody.evidence_reliability)
    if bundle and bundle.transcript:
        reliability = max(reliability, float(bundle.transcript.provider_confidence or 0.0))

    tokens = tuple(transcript_text.lower().split())
    return SpeakingEvaluationInput(
        transcript_text=transcript_text,
        transcript_word_count=len(tokens),
        transcript_tokens=tokens,
        pronunciation=pron_result.pronunciation,
        prosody=pros_result.prosody,
        evidence_availability=availability,
        evidence_reliability=reliability,
        provider_provenance=_provenance_from_bundle(bundle),
        evidence_reference_ids=tuple(ref_ids),
        processing_warnings=tuple(warnings),
    )


async def process_speaking_evaluation(
    artifact: SpeakingAudioArtifact,
    audio_bytes: bytes,
    *,
    task: SpeakingTaskContext,
    goal: SpeakingGoalContext,
    official_cefr: SpeakingOfficialCefrContext,
    student_id: int,
    language_id: int,
    revision_number: int = 1,
    previous_attempt_summary: str = "",
    previous_engine_result: dict[str, object] | None = None,
    force_complete: bool = False,
    language: str = "en",
    initial_prompt: str = "",
    pronunciation_provider: str | None = None,
    prosody_provider: str | None = None,
    transcription_provider: str | None = None,
    now: datetime | None = None,
) -> SpeakingEvaluationTurnResult:
    """Run S4→S5→S6 evidence chain then hybrid S7 evaluation."""
    ts = now or datetime.now(tz=timezone.utc)
    warnings: list[str] = []

    audio_result = await process_speaking_audio(
        artifact,
        audio_bytes,
        provider_name=transcription_provider,
        language=language,
        initial_prompt=initial_prompt or task.task_prompt,
        now=ts,
    )
    if not audio_result.success or audio_result.bundle is None:
        return SpeakingEvaluationTurnResult(
            success=False,
            error=str(getattr(audio_result.error, "message", audio_result.error) or "S4 audio processing failed"),
            processing_warnings=tuple(audio_result.processing_warnings),
        )

    transcript_text = audio_result.bundle.transcript.text if audio_result.bundle.transcript else ""
    pron_result = await process_speaking_pronunciation(
        artifact,
        audio_bytes,
        expected_task_text=task.task_prompt,
        transcript_text=transcript_text,
        existing_bundle=audio_result.bundle,
        provider_name=pronunciation_provider,
        now=ts,
    )
    warnings.extend(pron_result.processing_warnings)

    pros_result = await process_speaking_prosody(
        artifact,
        audio_bytes,
        existing_bundle=pron_result.bundle or audio_result.bundle,
        provider_name=prosody_provider,
        now=ts,
    )
    warnings.extend(pros_result.processing_warnings)

    eval_input = _build_input_from_runtimes(
        audio_result=audio_result,
        pron_result=pron_result,
        pros_result=pros_result,
    )

    evaluation_id = f"spk-eval-{uuid.uuid4().hex[:12]}"
    attempt_id = f"attempt-{revision_number}"
    context = new_evaluation_context(
        evaluation_id=evaluation_id,
        student_id=student_id,
        language_id=language_id,
        session_id=artifact.session_id,
        task_id=task.task_id,
        attempt_id=attempt_id,
        revision_number=revision_number,
        task=task,
        goal=goal,
        official_cefr=official_cefr,
        previous_attempt_summary=previous_attempt_summary,
        force_complete=force_complete,
        evaluated_at=ts.isoformat(),
    )

    if previous_engine_result and not previous_attempt_summary:
        prev = evaluation_result_from_dict(previous_engine_result)
        if prev and prev.explanation.summary:
            context = new_evaluation_context(
                evaluation_id=evaluation_id,
                student_id=student_id,
                language_id=language_id,
                session_id=artifact.session_id,
                task_id=task.task_id,
                attempt_id=attempt_id,
                revision_number=revision_number,
                task=task,
                goal=goal,
                official_cefr=official_cefr,
                previous_attempt_summary=prev.explanation.summary[:240],
                force_complete=force_complete,
                evaluated_at=ts.isoformat(),
            )

    evaluation = await evaluate_speaking_turn(eval_input, context)
    persistence = evaluation.to_persistence_dict()
    bundle = pros_result.bundle or pron_result.bundle or audio_result.bundle
    return SpeakingEvaluationTurnResult(
        success=True,
        evaluation=evaluation,
        persistence_dict={SPEAKING_ENGINE_RESULT_KEY: persistence, **persistence},
        bundle_id=bundle.evidence_bundle_id if bundle else "",
        processing_warnings=tuple(warnings),
    )
