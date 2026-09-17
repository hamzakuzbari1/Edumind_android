"""GrammarLearningPipeline — end-to-end orchestration (Integration Phase 1).

Wires existing Grammar Engine packages. No educational algorithms.
"""

from __future__ import annotations

import time
from uuid import uuid4

from app.services.language_grammar_pipeline.errors import PipelineValidationError
from app.services.language_grammar_pipeline.flags import grammar_pipeline_enabled
from app.services.language_grammar_pipeline.stages import (
    ensure_specification_patterns,
    stage_author_activity,
    stage_evaluate,
    stage_evidence_batch,
    stage_execute,
    stage_mastery,
    stage_plan_lesson,
    stage_recommend,
    stage_resolve_targets,
    stage_review,
)
from app.services.language_grammar_pipeline.store import save_replay_bundle
from app.services.language_grammar_pipeline.transactions import (
    abort_before_writes,
    mark_evaluation_succeeded,
    mark_evidence_ready,
    mark_mastery_applied,
    mark_progression_synced,
    mark_review_applied,
)
from app.services.language_grammar_pipeline.types import (
    GRAMMAR_PIPELINE_PACKAGE_VERSION,
    PipelineEventLog,
    PipelineEventType,
    PipelineMode,
    PipelineObservability,
    PipelineOutcome,
    PipelineReplayBundle,
    PipelineRequest,
    PipelineStage,
    PipelineStageFailure,
    PipelineStatus,
    WriteGate,
)


def _new_pipeline_id() -> str:
    return f"gpipe_{uuid4().hex[:12]}"


def _fail(
    *,
    pipeline_id: str,
    log: PipelineEventLog,
    gate: WriteGate,
    failures: list[PipelineStageFailure],
    stage: PipelineStage,
    code: str,
    message: str,
    started: float,
    request: PipelineRequest,
    observability_partial: dict,
    llm_invoked: bool = False,
    authoring_invoked: bool = False,
    execution_invoked: bool = False,
    **artifacts: object,
) -> PipelineOutcome:
    failures.append(
        PipelineStageFailure(stage=stage, code=code, message=message, recoverable=True)
    )
    log.emit(
        PipelineEventType.StageFailed,
        stage=stage.value,
        at=request.as_of,
        detail=f"{code}:{message}",
    )
    log.emit(
        PipelineEventType.PipelineFailed,
        stage=stage.value,
        at=request.as_of,
        detail=code,
    )
    aborted = abort_before_writes(gate, f"{stage.value}:{code}")
    obs = PipelineObservability(
        pipeline_id=pipeline_id,
        duration_ms=round((time.perf_counter() - started) * 1000, 3),
        mode=request.mode.value,
        **observability_partial,
    )
    return PipelineOutcome(
        status=PipelineStatus.failed,
        observability=obs,
        write_gate=aborted,
        events=tuple(log.events),
        failures=tuple(failures),
        llm_authoring_invoked=llm_invoked,
        authoring_invoked=authoring_invoked,
        execution_invoked=execution_invoked,
        notes=f"failed_at={stage.value};{code}",
        **artifacts,  # type: ignore[arg-type]
    )


def run_grammar_learning_pipeline(request: PipelineRequest) -> PipelineOutcome:
    """Sole public orchestration entry — Integration Phase 1."""
    started = time.perf_counter()
    pipeline_id = request.pipeline_id or (
        request.replay_bundle.pipeline_id if request.replay_bundle else _new_pipeline_id()
    )
    log = PipelineEventLog(pipeline_id=pipeline_id)
    failures: list[PipelineStageFailure] = []
    gate = WriteGate()
    obs_ids: dict[str, str] = {}

    if not grammar_pipeline_enabled():
        log.emit(PipelineEventType.PipelineDisabled, detail="LANG_GRAMMAR_PIPELINE_ENABLED")
        return PipelineOutcome(
            status=PipelineStatus.disabled,
            observability=PipelineObservability(
                pipeline_id=pipeline_id,
                duration_ms=round((time.perf_counter() - started) * 1000, 3),
                mode=request.mode.value,
            ),
            write_gate=abort_before_writes(gate, "pipeline_disabled"),
            events=tuple(log.events),
            failures=(
                PipelineStageFailure(
                    stage=PipelineStage.resolve,
                    code="pipeline_disabled",
                    message="LANG_GRAMMAR_PIPELINE_ENABLED is false",
                ),
            ),
            notes="disabled",
        )

    is_replay = request.mode is PipelineMode.replay or request.replay_bundle is not None
    bundle = request.replay_bundle
    authoring_invoked = False
    llm_invoked = False
    execution_invoked = False

    log.emit(
        PipelineEventType.GrammarLessonStarted,
        stage=PipelineStage.resolve.value,
        at=request.as_of,
        detail="replay" if is_replay else "run",
    )

    # --- Resolve ---
    try:
        log.emit(PipelineEventType.StageStarted, stage=PipelineStage.resolve.value, at=request.as_of)
        if is_replay and bundle is not None:
            grammar_targets = bundle.grammar_targets or tuple(bundle.specification.grammar_targets)
            snapshot = request.learning_snapshot
        else:
            if request.learning_snapshot is None:
                raise PipelineValidationError(
                    "missing_learning_snapshot",
                    "Pipeline requires GrammarLearningSnapshot (via Integration)",
                )
            snapshot = request.learning_snapshot
            grammar_targets = stage_resolve_targets(snapshot)
        if not grammar_targets:
            raise PipelineValidationError("missing_grammar_targets", "No grammar targets resolved")
        obs_ids["grammar_target"] = grammar_targets[0]
        log.emit(
            PipelineEventType.StageCompleted,
            stage=PipelineStage.resolve.value,
            at=request.as_of,
            detail=",".join(grammar_targets),
        )
    except Exception as exc:  # noqa: BLE001 — structured stage failure
        return _fail(
            pipeline_id=pipeline_id,
            log=log,
            gate=gate,
            failures=failures,
            stage=PipelineStage.resolve,
            code=getattr(exc, "code", type(exc).__name__),
            message=str(getattr(exc, "message", exc)),
            started=started,
            request=request,
            observability_partial=obs_ids,
        )

    # --- Plan ---
    try:
        log.emit(PipelineEventType.StageStarted, stage=PipelineStage.plan.value, at=request.as_of)
        if is_replay and bundle is not None:
            blueprint = bundle.blueprint
        elif request.blueprint is not None:
            blueprint = request.blueprint
        else:
            if snapshot is None:
                raise PipelineValidationError("missing_snapshot_for_plan", "Plan requires snapshot")
            blueprint = stage_plan_lesson(snapshot)
        obs_ids["lesson_id"] = blueprint.lesson_id or blueprint.fingerprint or grammar_targets[0]
        log.emit(
            PipelineEventType.StageCompleted,
            stage=PipelineStage.plan.value,
            at=request.as_of,
            detail=obs_ids["lesson_id"],
        )
    except Exception as exc:  # noqa: BLE001
        return _fail(
            pipeline_id=pipeline_id,
            log=log,
            gate=gate,
            failures=failures,
            stage=PipelineStage.plan,
            code=getattr(exc, "code", type(exc).__name__),
            message=str(getattr(exc, "message", exc)),
            started=started,
            request=request,
            observability_partial=obs_ids,
            grammar_targets=grammar_targets,
        )

    # --- Author ---
    try:
        log.emit(PipelineEventType.StageStarted, stage=PipelineStage.author.value, at=request.as_of)
        if is_replay and bundle is not None:
            specification = bundle.specification
            expected_patterns = bundle.expected_patterns or request.expected_patterns
        elif request.specification is not None:
            specification = request.specification
            expected_patterns = request.expected_patterns
        else:
            if is_replay:
                raise PipelineValidationError(
                    "replay_missing_specification",
                    "Replay must not regenerate lessons — provide stored ActivitySpecification",
                )
            cefr = (
                snapshot.overall_cefr.value
                if snapshot is not None and hasattr(snapshot.overall_cefr, "value")
                else request.overall_cefr
            )
            specification, authoring_invoked, llm_invoked = stage_author_activity(
                grammar_targets=grammar_targets,
                student_id=request.student_id,
                language_id=request.language_id,
                overall_cefr=str(cefr),
                activity_type=request.activity_type,
                lesson_id=obs_ids.get("lesson_id", ""),
                adaptive_snapshot=request.adaptive_snapshot,
                use_llm_authoring=request.use_llm_authoring,
                localization=request.localization,
                as_of=request.as_of,
            )
            expected_patterns = request.expected_patterns
        specification = ensure_specification_patterns(specification, expected_patterns)
        obs_ids["activity_id"] = specification.activity_id
        log.emit(
            PipelineEventType.LessonGenerated,
            stage=PipelineStage.author.value,
            at=request.as_of,
            detail=specification.activity_id,
        )
        log.emit(
            PipelineEventType.StageCompleted,
            stage=PipelineStage.author.value,
            at=request.as_of,
            detail="replay" if (is_replay and not authoring_invoked) else "authored",
        )
    except Exception as exc:  # noqa: BLE001
        return _fail(
            pipeline_id=pipeline_id,
            log=log,
            gate=gate,
            failures=failures,
            stage=PipelineStage.author,
            code=getattr(exc, "code", type(exc).__name__),
            message=str(getattr(exc, "message", exc)),
            started=started,
            request=request,
            observability_partial=obs_ids,
            grammar_targets=grammar_targets,
            blueprint=blueprint,
            llm_invoked=llm_invoked,
            authoring_invoked=authoring_invoked,
        )

    # --- Execute ---
    execution_result = None
    execution_session_id = ""
    student_response = request.student_response
    try:
        log.emit(PipelineEventType.StageStarted, stage=PipelineStage.execute.value, at=request.as_of)
        if is_replay and bundle is not None:
            student_response = bundle.student_response
            execution_result = bundle.execution_result
            execution_session_id = bundle.execution_session_id
            # Replay never re-enters runtime generation — response is stored.
        else:
            state = stage_execute(
                specification,
                student_id=request.student_id,
                language_id=request.language_id,
                student_response=student_response,
                as_of=request.as_of,
                localization=request.localization,
            )
            execution_invoked = True
            execution_result = state.result
            execution_session_id = state.session.execution_session_id
            if state.session.student_response:
                student_response = state.session.student_response
        obs_ids["execution_id"] = execution_session_id
        log.emit(
            PipelineEventType.LessonExecuted,
            stage=PipelineStage.execute.value,
            at=request.as_of,
            detail=execution_session_id or "stored",
        )
        log.emit(
            PipelineEventType.StageCompleted,
            stage=PipelineStage.execute.value,
            at=request.as_of,
            detail="replay" if (is_replay and not execution_invoked) else "executed",
        )
    except Exception as exc:  # noqa: BLE001
        return _fail(
            pipeline_id=pipeline_id,
            log=log,
            gate=gate,
            failures=failures,
            stage=PipelineStage.execute,
            code=getattr(exc, "code", type(exc).__name__),
            message=str(getattr(exc, "message", exc)),
            started=started,
            request=request,
            observability_partial=obs_ids,
            grammar_targets=grammar_targets,
            blueprint=blueprint,
            specification=specification,
            llm_invoked=llm_invoked,
            authoring_invoked=authoring_invoked,
            execution_invoked=execution_invoked,
        )

    # --- Evaluate (WRITE GATE) ---
    evaluation_result = None
    try:
        log.emit(PipelineEventType.StageStarted, stage=PipelineStage.evaluate.value, at=request.as_of)
        evaluation_id = f"geval_{pipeline_id}"
        if is_replay and bundle is not None and bundle.evaluation_result is not None:
            evaluation_result = bundle.evaluation_result
        else:
            evaluation_result = stage_evaluate(
                grammar_targets=grammar_targets,
                student_response=student_response,
                specification=specification,
                expected_patterns=expected_patterns,
                student_id=request.student_id,
                language_id=request.language_id,
                as_of=request.as_of,
                evaluation_id=evaluation_id,
            )
        obs_ids["evaluation_id"] = evaluation_result.evaluation_id
        gate = mark_evaluation_succeeded(gate)
        log.emit(
            PipelineEventType.GrammarEvaluated,
            stage=PipelineStage.evaluate.value,
            at=request.as_of,
            detail=evaluation_result.evaluation_id,
        )
        log.emit(
            PipelineEventType.StageCompleted,
            stage=PipelineStage.evaluate.value,
            at=request.as_of,
            detail="ok",
        )
    except Exception as exc:  # noqa: BLE001
        return _fail(
            pipeline_id=pipeline_id,
            log=log,
            gate=gate,
            failures=failures,
            stage=PipelineStage.evaluate,
            code=getattr(exc, "code", type(exc).__name__),
            message=str(getattr(exc, "message", exc)),
            started=started,
            request=request,
            observability_partial=obs_ids,
            grammar_targets=grammar_targets,
            blueprint=blueprint,
            specification=specification,
            execution_result=execution_result,
            execution_session_id=execution_session_id,
            llm_invoked=llm_invoked,
            authoring_invoked=authoring_invoked,
            execution_invoked=execution_invoked,
        )

    # --- Evidence ---
    evidence_batch = None
    try:
        log.emit(PipelineEventType.StageStarted, stage=PipelineStage.evidence.value, at=request.as_of)
        if is_replay and bundle is not None and bundle.evidence_batch is not None:
            evidence_batch = bundle.evidence_batch
        else:
            assert evaluation_result is not None
            evidence_batch = stage_evidence_batch(evaluation_result)
        gate = mark_evidence_ready(gate)
        log.emit(
            PipelineEventType.EvidenceProduced,
            stage=PipelineStage.evidence.value,
            at=request.as_of,
            detail=str(len(evidence_batch.observations)),
        )
        log.emit(
            PipelineEventType.StageCompleted,
            stage=PipelineStage.evidence.value,
            at=request.as_of,
            detail="ok",
        )
    except Exception as exc:  # noqa: BLE001
        return _fail(
            pipeline_id=pipeline_id,
            log=log,
            gate=gate,
            failures=failures,
            stage=PipelineStage.evidence,
            code=getattr(exc, "code", type(exc).__name__),
            message=str(getattr(exc, "message", exc)),
            started=started,
            request=request,
            observability_partial=obs_ids,
            grammar_targets=grammar_targets,
            blueprint=blueprint,
            specification=specification,
            execution_result=execution_result,
            execution_session_id=execution_session_id,
            evaluation_result=evaluation_result,
            llm_invoked=llm_invoked,
            authoring_invoked=authoring_invoked,
            execution_invoked=execution_invoked,
        )

    mastery_snapshot = None
    review_snapshot = None
    completed_sync = None
    next_recommendation = None

    if request.apply_learner_writes and gate.may_write_mastery():
        # --- Mastery ---
        try:
            log.emit(PipelineEventType.StageStarted, stage=PipelineStage.mastery.value, at=request.as_of)
            assert evidence_batch is not None
            mastery_snapshot = stage_mastery(
                student_id=request.student_id,
                language_id=request.language_id,
                batch=evidence_batch,
                prior=request.prior_mastery,
            )
            gate = mark_mastery_applied(gate)
            obs_ids["mastery_version"] = str(
                getattr(mastery_snapshot, "schema_version", GRAMMAR_PIPELINE_PACKAGE_VERSION)
            )
            log.emit(
                PipelineEventType.MasteryUpdated,
                stage=PipelineStage.mastery.value,
                at=request.as_of,
                detail=obs_ids["mastery_version"],
            )
            log.emit(
                PipelineEventType.StageCompleted,
                stage=PipelineStage.mastery.value,
                at=request.as_of,
                detail="ok",
            )
        except Exception as exc:  # noqa: BLE001
            return _fail(
                pipeline_id=pipeline_id,
                log=log,
                gate=gate,
                failures=failures,
                stage=PipelineStage.mastery,
                code=getattr(exc, "code", type(exc).__name__),
                message=str(getattr(exc, "message", exc)),
                started=started,
                request=request,
                observability_partial=obs_ids,
                grammar_targets=grammar_targets,
                blueprint=blueprint,
                specification=specification,
                execution_result=execution_result,
                execution_session_id=execution_session_id,
                evaluation_result=evaluation_result,
                evidence_batch=evidence_batch,
                observations=tuple(evidence_batch.observations) if evidence_batch else (),
                llm_invoked=llm_invoked,
                authoring_invoked=authoring_invoked,
                execution_invoked=execution_invoked,
            )

        # --- Review ---
        try:
            log.emit(PipelineEventType.StageStarted, stage=PipelineStage.review.value, at=request.as_of)
            if not gate.may_write_review():
                raise PipelineValidationError("review_blocked", "Review blocked by write gate")
            assert mastery_snapshot is not None
            review_snapshot = stage_review(
                mastery=mastery_snapshot,
                student_id=request.student_id,
                language_id=request.language_id,
                as_of=request.as_of,
            )
            gate = mark_review_applied(gate)
            obs_ids["review_version"] = str(
                getattr(review_snapshot, "schema_version", GRAMMAR_PIPELINE_PACKAGE_VERSION)
            )
            log.emit(
                PipelineEventType.ReviewUpdated,
                stage=PipelineStage.review.value,
                at=request.as_of,
                detail=obs_ids["review_version"],
            )
            log.emit(
                PipelineEventType.StageCompleted,
                stage=PipelineStage.review.value,
                at=request.as_of,
                detail="ok",
            )
        except Exception as exc:  # noqa: BLE001
            return _fail(
                pipeline_id=pipeline_id,
                log=log,
                gate=gate,
                failures=failures,
                stage=PipelineStage.review,
                code=getattr(exc, "code", type(exc).__name__),
                message=str(getattr(exc, "message", exc)),
                started=started,
                request=request,
                observability_partial=obs_ids,
                grammar_targets=grammar_targets,
                blueprint=blueprint,
                specification=specification,
                execution_result=execution_result,
                execution_session_id=execution_session_id,
                evaluation_result=evaluation_result,
                evidence_batch=evidence_batch,
                observations=tuple(evidence_batch.observations) if evidence_batch else (),
                mastery_snapshot=mastery_snapshot,
                llm_invoked=llm_invoked,
                authoring_invoked=authoring_invoked,
                execution_invoked=execution_invoked,
            )

        # --- Recommend / progression sync plan ---
        try:
            log.emit(
                PipelineEventType.StageStarted,
                stage=PipelineStage.recommend.value,
                at=request.as_of,
            )
            if not gate.may_sync_progression():
                raise PipelineValidationError(
                    "progression_blocked",
                    "Progression sync blocked by write gate",
                )
            assert mastery_snapshot is not None
            completed_sync, next_recommendation = stage_recommend(
                student_id=request.student_id,
                language_id=request.language_id,
                progression=request.prior_progression,
                mastery=mastery_snapshot,
            )
            if request.prior_progression is not None:
                gate = mark_progression_synced(gate)
            log.emit(
                PipelineEventType.StageCompleted,
                stage=PipelineStage.recommend.value,
                at=request.as_of,
                detail="ok",
            )
        except Exception as exc:  # noqa: BLE001
            return _fail(
                pipeline_id=pipeline_id,
                log=log,
                gate=gate,
                failures=failures,
                stage=PipelineStage.recommend,
                code=getattr(exc, "code", type(exc).__name__),
                message=str(getattr(exc, "message", exc)),
                started=started,
                request=request,
                observability_partial=obs_ids,
                grammar_targets=grammar_targets,
                blueprint=blueprint,
                specification=specification,
                execution_result=execution_result,
                execution_session_id=execution_session_id,
                evaluation_result=evaluation_result,
                evidence_batch=evidence_batch,
                observations=tuple(evidence_batch.observations) if evidence_batch else (),
                mastery_snapshot=mastery_snapshot,
                review_snapshot=review_snapshot,
                llm_invoked=llm_invoked,
                authoring_invoked=authoring_invoked,
                execution_invoked=execution_invoked,
            )
    elif not request.apply_learner_writes:
        gate = abort_before_writes(gate, "apply_learner_writes=false")
        # Preserve evaluation success markers for observability
        gate = WriteGate(
            evaluation_succeeded=True,
            evidence_ready=True,
            mastery_applied=False,
            review_applied=False,
            progression_synced=False,
            aborted=True,
            abort_reason="apply_learner_writes=false",
        )

    replay = PipelineReplayBundle(
        pipeline_id=pipeline_id,
        blueprint=blueprint,
        specification=specification,
        student_response=student_response,
        grammar_targets=grammar_targets,
        expected_patterns=expected_patterns,
        evaluation_result=evaluation_result,
        evidence_batch=evidence_batch,
        execution_result=execution_result,
        execution_session_id=execution_session_id,
        as_of=request.as_of,
    )
    save_replay_bundle(replay)

    log.emit(
        PipelineEventType.LessonCompleted,
        stage=PipelineStage.recommend.value,
        at=request.as_of,
        detail=pipeline_id,
    )

    return PipelineOutcome(
        status=PipelineStatus.completed,
        observability=PipelineObservability(
            pipeline_id=pipeline_id,
            lesson_id=obs_ids.get("lesson_id", ""),
            grammar_target=obs_ids.get("grammar_target", ""),
            activity_id=obs_ids.get("activity_id", ""),
            execution_id=obs_ids.get("execution_id", ""),
            evaluation_id=obs_ids.get("evaluation_id", ""),
            mastery_version=obs_ids.get("mastery_version", ""),
            review_version=obs_ids.get("review_version", ""),
            duration_ms=round((time.perf_counter() - started) * 1000, 3),
            mode=PipelineMode.replay.value if is_replay else PipelineMode.run.value,
        ),
        write_gate=gate,
        events=tuple(log.events),
        failures=tuple(failures),
        grammar_targets=grammar_targets,
        blueprint=blueprint,
        specification=specification,
        execution_result=execution_result,
        execution_session_id=execution_session_id,
        evaluation_result=evaluation_result,
        evidence_batch=evidence_batch,
        observations=tuple(evidence_batch.observations) if evidence_batch else (),
        mastery_snapshot=mastery_snapshot,
        review_snapshot=review_snapshot,
        completed_sync=completed_sync,
        next_recommendation=next_recommendation,
        replay_bundle=replay,
        llm_authoring_invoked=llm_invoked,
        authoring_invoked=authoring_invoked,
        execution_invoked=execution_invoked,
        notes="completed",
    )


class GrammarLearningPipeline:
    """Named orchestrator surface — Integration Phase 1."""

    @staticmethod
    def run(request: PipelineRequest) -> PipelineOutcome:
        return run_grammar_learning_pipeline(request)

    @staticmethod
    def replay(bundle: PipelineReplayBundle, *, apply_learner_writes: bool = True) -> PipelineOutcome:
        return run_grammar_learning_pipeline(
            PipelineRequest(
                student_id=0,
                language_id=0,
                student_response=bundle.student_response,
                mode=PipelineMode.replay,
                replay_bundle=bundle,
                pipeline_id=bundle.pipeline_id,
                as_of=bundle.as_of,
                apply_learner_writes=apply_learner_writes,
                expected_patterns=bundle.expected_patterns,
            )
        )
