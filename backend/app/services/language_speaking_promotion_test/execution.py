"""SPA assessment execution lifecycle (S19).

Owns start / submit-score / complete / abandon / timeout / retry-start.
Does not call S7 directly (ownership: evaluator wiring lives in test_api).
Does not write official_speaking_cefr.
"""

from __future__ import annotations

from datetime import datetime, timezone

from app.services.language_speaking_promotion_test.assessment import (
    mint_attempt_id,
    mint_session_id,
    mint_task_attempt_id,
)
from app.services.language_speaking_promotion_test.execution_types import (
    MAX_ATTEMPT_HISTORY,
    SpaAssessmentAttempt,
    SpaAssessmentOutcome,
    SpaAssessmentSession,
    SpaExecutionFailureCode,
    SpaExecutionResult,
    SpaTaskAttempt,
    SpaTaskAttemptStatus,
    SpaTaskScoreSummary,
    SpeakingPromotionAssessment,
)
from app.services.language_speaking_promotion_test.outcome import (
    build_assessment_result,
    decide_spa_pass_gate,
)
from app.services.language_speaking_promotion_test.policy import SpaExecutionMode
from app.services.language_speaking_promotion_test.types import SpaBlueprintStatus


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _terminal_statuses() -> frozenset[SpaBlueprintStatus]:
    return frozenset(
        {
            SpaBlueprintStatus.completed,
            SpaBlueprintStatus.abandoned,
            SpaBlueprintStatus.unavailable,
        }
    )


def _scores_from_attempt(attempt: SpaAssessmentAttempt) -> tuple[SpaTaskScoreSummary, ...]:
    return tuple(t.score for t in attempt.task_attempts if t.score is not None)


def start_speaking_promotion_assessment(
    assessment: SpeakingPromotionAssessment,
    *,
    force_new_attempt: bool = False,
) -> SpaExecutionResult:
    """Start or resume: mint attempt_id when starting; resume in_progress cursor."""
    if not assessment.blueprint.frozen:
        return SpaExecutionResult(
            ok=False,
            failure_code=SpaExecutionFailureCode.blueprint_not_frozen,
            student_safe_message="Assessment blueprint is not ready.",
        )

    # Resume existing in-progress attempt (idempotent reconnect).
    if (
        not force_new_attempt
        and assessment.status == SpaBlueprintStatus.in_progress
        and assessment.session is not None
        and assessment.current_attempt is not None
        and assessment.current_attempt.outcome is None
    ):
        return SpaExecutionResult(ok=True, assessment=assessment, idempotent=True)

    startable = assessment.status in (
        SpaBlueprintStatus.not_started,
        SpaBlueprintStatus.available,
    )
    retryable = (
        assessment.status in _terminal_statuses()
        and assessment.result is not None
        and assessment.result.outcome
        in (
            SpaAssessmentOutcome.FAIL,
            SpaAssessmentOutcome.ABANDONED,
            SpaAssessmentOutcome.TIMEOUT,
            SpaAssessmentOutcome.INCOMPLETE,
        )
    )
    if not startable and not (force_new_attempt and retryable):
        if assessment.status == SpaBlueprintStatus.completed and (
            assessment.result is not None and assessment.result.outcome == SpaAssessmentOutcome.PASS
        ):
            return SpaExecutionResult(
                ok=False,
                failure_code=SpaExecutionFailureCode.retry_not_eligible,
                student_safe_message="This assessment already passed.",
            )
        return SpaExecutionResult(
            ok=False,
            failure_code=SpaExecutionFailureCode.assessment_not_startable,
            student_safe_message="Assessment cannot be started.",
        )

    ts = _now()
    attempt_id = mint_attempt_id()
    session_id = mint_session_id()
    tasks = tuple(
        SpaTaskAttempt(
            task_attempt_id=mint_task_attempt_id(t.task_id),
            task_id=t.task_id,
            task_order=t.task_order,
            attempt_id=attempt_id,
            status=SpaTaskAttemptStatus.pending,
        )
        for t in sorted(assessment.blueprint.tasks, key=lambda x: x.task_order)
    )
    attempt = SpaAssessmentAttempt(
        attempt_id=attempt_id,
        assessment_id=assessment.assessment_id,
        blueprint_id=assessment.blueprint_id,
        started_at=ts,
        updated_at=ts,
        status=SpaBlueprintStatus.in_progress,
        task_attempts=tasks,
    )
    session = SpaAssessmentSession(
        session_id=session_id,
        assessment_id=assessment.assessment_id,
        attempt_id=attempt_id,
        blueprint_id=assessment.blueprint_id,
        current_task_index=0,
        started_at=ts,
        updated_at=ts,
    )

    history = list(assessment.attempt_history)
    if assessment.current_attempt is not None and assessment.current_attempt.outcome is not None:
        history.append(assessment.current_attempt)
        history = history[-MAX_ATTEMPT_HISTORY:]

    updated = SpeakingPromotionAssessment(
        assessment_id=assessment.assessment_id,
        blueprint_id=assessment.blueprint_id,
        blueprint=assessment.blueprint,
        status=SpaBlueprintStatus.in_progress,
        created_at=assessment.created_at,
        updated_at=ts,
        session=session,
        current_attempt=attempt,
        attempt_history=tuple(history),
        result=None,
        mandatory_requirements=assessment.mandatory_requirements,
        evidence_source=assessment.evidence_source,
        schema_version=assessment.schema_version,
    )
    return SpaExecutionResult(ok=True, assessment=updated)


def record_task_score(
    assessment: SpeakingPromotionAssessment,
    *,
    task_id: str,
    score: SpaTaskScoreSummary,
    attempt_id: str | None = None,
) -> SpaExecutionResult:
    """Persist an evaluated task score on the current attempt (idempotent re-submit)."""
    if assessment.status != SpaBlueprintStatus.in_progress or assessment.current_attempt is None:
        return SpaExecutionResult(
            ok=False,
            failure_code=SpaExecutionFailureCode.assessment_not_in_progress,
            student_safe_message="Assessment is not in progress.",
        )
    attempt = assessment.current_attempt
    if attempt_id and attempt.attempt_id != attempt_id:
        return SpaExecutionResult(
            ok=False,
            failure_code=SpaExecutionFailureCode.attempt_mismatch,
            student_safe_message="Assessment attempt mismatch.",
        )
    if assessment.session is None:
        return SpaExecutionResult(
            ok=False,
            failure_code=SpaExecutionFailureCode.assessment_not_in_progress,
            student_safe_message="Assessment session missing.",
        )

    ordered = sorted(assessment.blueprint.tasks, key=lambda t: t.task_order)
    cursor = assessment.session.current_task_index
    if cursor < 0 or cursor >= len(ordered):
        return SpaExecutionResult(
            ok=False,
            failure_code=SpaExecutionFailureCode.task_not_current,
            student_safe_message="No current task.",
        )
    current_task = ordered[cursor]
    if current_task.task_id != task_id:
        # Idempotent: allow re-submit of already-evaluated current/previous task.
        existing = next((t for t in attempt.task_attempts if t.task_id == task_id), None)
        if (
            existing is not None
            and existing.status == SpaTaskAttemptStatus.evaluated
            and existing.score is not None
        ):
            return SpaExecutionResult(ok=True, assessment=assessment, idempotent=True)
        return SpaExecutionResult(
            ok=False,
            failure_code=SpaExecutionFailureCode.task_not_current,
            student_safe_message="Submit the current assessment task.",
        )

    mode = current_task.execution_mode
    if mode not in (SpaExecutionMode.recorded_response, SpaExecutionMode.controlled_response):
        return SpaExecutionResult(
            ok=False,
            failure_code=SpaExecutionFailureCode.invalid_execution_mode,
            student_safe_message="This task cannot be submitted.",
        )

    ts = _now()
    new_tasks: list[SpaTaskAttempt] = []
    for ta in attempt.task_attempts:
        if ta.task_id != task_id:
            new_tasks.append(ta)
            continue
        if ta.status == SpaTaskAttemptStatus.evaluated and ta.score is not None:
            # Idempotent replay of same evaluation id.
            if ta.score.evaluation_id == score.evaluation_id:
                return SpaExecutionResult(ok=True, assessment=assessment, idempotent=True)
            return SpaExecutionResult(
                ok=False,
                failure_code=SpaExecutionFailureCode.task_already_terminal,
                student_safe_message="Task already submitted.",
            )
        new_tasks.append(
            SpaTaskAttempt(
                task_attempt_id=ta.task_attempt_id,
                task_id=ta.task_id,
                task_order=ta.task_order,
                attempt_id=ta.attempt_id,
                status=SpaTaskAttemptStatus.evaluated,
                score=score,
                started_at=ta.started_at or ts,
                completed_at=ts,
            )
        )

    next_index = cursor + 1
    session = SpaAssessmentSession(
        session_id=assessment.session.session_id,
        assessment_id=assessment.session.assessment_id,
        attempt_id=assessment.session.attempt_id,
        blueprint_id=assessment.session.blueprint_id,
        current_task_index=min(next_index, len(ordered)),
        started_at=assessment.session.started_at,
        updated_at=ts,
        expires_at=assessment.session.expires_at,
    )
    new_attempt = SpaAssessmentAttempt(
        attempt_id=attempt.attempt_id,
        assessment_id=attempt.assessment_id,
        blueprint_id=attempt.blueprint_id,
        started_at=attempt.started_at,
        updated_at=ts,
        status=SpaBlueprintStatus.in_progress,
        task_attempts=tuple(new_tasks),
    )
    updated = SpeakingPromotionAssessment(
        assessment_id=assessment.assessment_id,
        blueprint_id=assessment.blueprint_id,
        blueprint=assessment.blueprint,
        status=SpaBlueprintStatus.in_progress,
        created_at=assessment.created_at,
        updated_at=ts,
        session=session,
        current_attempt=new_attempt,
        attempt_history=assessment.attempt_history,
        result=None,
        mandatory_requirements=assessment.mandatory_requirements,
        evidence_source=assessment.evidence_source,
        schema_version=assessment.schema_version,
    )
    return SpaExecutionResult(ok=True, assessment=updated)


def complete_speaking_promotion_assessment(
    assessment: SpeakingPromotionAssessment,
) -> SpaExecutionResult:
    """Aggregate PASS/FAIL when all tasks are terminal; never writes CEFR."""
    if assessment.current_attempt is None:
        return SpaExecutionResult(
            ok=False,
            failure_code=SpaExecutionFailureCode.assessment_not_in_progress,
            student_safe_message="Assessment is not in progress.",
        )
    if assessment.status == SpaBlueprintStatus.completed and assessment.result is not None:
        return SpaExecutionResult(ok=True, assessment=assessment, idempotent=True)

    scores = _scores_from_attempt(assessment.current_attempt)
    tasks_total = len(assessment.blueprint.tasks)
    if len(scores) < tasks_total:
        return SpaExecutionResult(
            ok=False,
            failure_code=SpaExecutionFailureCode.validation_failed,
            student_safe_message="Not all assessment tasks are complete.",
        )

    gate = decide_spa_pass_gate(
        scores=scores,
        tasks_total=tasks_total,
        requirements=assessment.mandatory_requirements,
    )
    ts = _now()
    result = build_assessment_result(
        assessment_id=assessment.assessment_id,
        attempt_id=assessment.current_attempt.attempt_id,
        blueprint_id=assessment.blueprint_id,
        outcome=gate.outcome,
        pass_gate=gate,
        scores=scores,
        completed_at=ts,
    )
    finished_attempt = SpaAssessmentAttempt(
        attempt_id=assessment.current_attempt.attempt_id,
        assessment_id=assessment.current_attempt.assessment_id,
        blueprint_id=assessment.current_attempt.blueprint_id,
        started_at=assessment.current_attempt.started_at,
        updated_at=ts,
        status=SpaBlueprintStatus.completed,
        task_attempts=assessment.current_attempt.task_attempts,
        outcome=gate.outcome,
        completed_at=ts,
    )
    terminal_history = tuple(
        a for a in (list(assessment.attempt_history) + [finished_attempt]) if a.outcome is not None
    )[-MAX_ATTEMPT_HISTORY:]
    updated = SpeakingPromotionAssessment(
        assessment_id=assessment.assessment_id,
        blueprint_id=assessment.blueprint_id,
        blueprint=assessment.blueprint,
        status=SpaBlueprintStatus.completed,
        created_at=assessment.created_at,
        updated_at=ts,
        session=None,
        current_attempt=finished_attempt,
        attempt_history=terminal_history,
        result=result,
        mandatory_requirements=assessment.mandatory_requirements,
        evidence_source=assessment.evidence_source,
        schema_version=assessment.schema_version,
    )
    return SpaExecutionResult(ok=True, assessment=updated)


def abandon_speaking_promotion_assessment(
    assessment: SpeakingPromotionAssessment,
) -> SpaExecutionResult:
    return _terminate_non_pass(assessment, SpaAssessmentOutcome.ABANDONED, SpaBlueprintStatus.abandoned)


def timeout_speaking_promotion_assessment(
    assessment: SpeakingPromotionAssessment,
) -> SpaExecutionResult:
    return _terminate_non_pass(assessment, SpaAssessmentOutcome.TIMEOUT, SpaBlueprintStatus.abandoned)


def _terminate_non_pass(
    assessment: SpeakingPromotionAssessment,
    outcome: SpaAssessmentOutcome,
    status: SpaBlueprintStatus,
) -> SpaExecutionResult:
    if assessment.result is not None and assessment.status in _terminal_statuses():
        return SpaExecutionResult(ok=True, assessment=assessment, idempotent=True)
    if assessment.current_attempt is None and assessment.status == SpaBlueprintStatus.not_started:
        return SpaExecutionResult(
            ok=False,
            failure_code=SpaExecutionFailureCode.assessment_not_in_progress,
            student_safe_message="Assessment has not started.",
        )
    ts = _now()
    attempt = assessment.current_attempt
    attempt_id = attempt.attempt_id if attempt else mint_attempt_id()
    finished = None
    if attempt is not None:
        finished = SpaAssessmentAttempt(
            attempt_id=attempt.attempt_id,
            assessment_id=attempt.assessment_id,
            blueprint_id=attempt.blueprint_id,
            started_at=attempt.started_at,
            updated_at=ts,
            status=status,
            task_attempts=attempt.task_attempts,
            outcome=outcome,
            completed_at=ts,
        )
    result = build_assessment_result(
        assessment_id=assessment.assessment_id,
        attempt_id=attempt_id,
        blueprint_id=assessment.blueprint_id,
        outcome=outcome,
        pass_gate=None,
        scores=_scores_from_attempt(attempt) if attempt else (),
        completed_at=ts,
    )
    history = list(assessment.attempt_history)
    if finished is not None:
        history.append(finished)
    history = history[-MAX_ATTEMPT_HISTORY:]
    updated = SpeakingPromotionAssessment(
        assessment_id=assessment.assessment_id,
        blueprint_id=assessment.blueprint_id,
        blueprint=assessment.blueprint,
        status=status,
        created_at=assessment.created_at,
        updated_at=ts,
        session=None,
        current_attempt=finished,
        attempt_history=tuple(history),
        result=result,
        mandatory_requirements=assessment.mandatory_requirements,
        evidence_source=assessment.evidence_source,
        schema_version=assessment.schema_version,
    )
    return SpaExecutionResult(ok=True, assessment=updated)


def current_task_id(assessment: SpeakingPromotionAssessment) -> str | None:
    if assessment.session is None:
        return None
    ordered = sorted(assessment.blueprint.tasks, key=lambda t: t.task_order)
    idx = assessment.session.current_task_index
    if idx < 0 or idx >= len(ordered):
        return None
    return ordered[idx].task_id
