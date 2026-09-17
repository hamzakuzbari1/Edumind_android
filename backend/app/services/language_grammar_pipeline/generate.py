"""Generate-only Grammar lesson path (Product Milestone A).

Stops after Adaptive/LLM Authoring → ActivitySpecification.
Never executes runtime, evaluates, or updates mastery/review/progression.
"""

from __future__ import annotations

import json
import time
from uuid import uuid4

from app.services.language_grammar_activity_authoring.llm.lesson_schema import (
    CANONICAL_LESSON_SCHEMA_VERSION,
    METHODOLOGY_VERSION,
    PAYLOAD_STUDENT_CONTENT_KEY,
    lesson_package_from_specification_payload,
)
from app.services.language_grammar_activity_authoring.llm.errors import LLMSchemaError
from app.services.language_grammar_activity_authoring.llm.lesson_validation import (
    validate_student_content_integrity,
)
from app.services.language_grammar_pipeline.errors import PipelineValidationError
from app.services.language_grammar_pipeline.flags import grammar_pipeline_enabled
from app.services.language_grammar_pipeline.lesson_package_fallback import (
    RETRY_AUTHORING_STATUS,
    RETRY_GENERATION_MODE,
    RETRY_MESSAGE_AR,
    ensure_lesson_package_on_specification,
)
from app.services.language_grammar_pipeline.stages import (
    _grammar_authoring_profile,
    ensure_specification_patterns,
    stage_author_activity,
    stage_plan_lesson,
    stage_resolve_targets,
)
from app.services.language_grammar_pipeline.types import (
    GRAMMAR_PIPELINE_PACKAGE_VERSION,
    PipelineEventLog,
    PipelineEventType,
    PipelineMode,
    PipelineObservability,
    PipelineOutcome,
    PipelineRequest,
    PipelineStage,
    PipelineStageFailure,
    PipelineStatus,
    WriteGate,
)


def _new_id() -> str:
    return f"gpipe_gen_{uuid4().hex[:12]}"


def _max_contrasts_and_mistakes_for_targets(grammar_targets: tuple[str, ...]) -> int | None:
    primary = grammar_targets[0] if grammar_targets else ""
    if primary != "gram_be_present":
        return None
    profile = _grammar_authoring_profile((primary,))
    categories = profile.get("mistake_categories") or []
    if not isinstance(categories, list):
        return None
    count = len([str(item).strip() for item in categories if str(item).strip()])
    return count if count > 4 else None


def generate_grammar_lesson(request: PipelineRequest) -> PipelineOutcome:
    """Orchestrate resolve → plan → author only. Product Milestone A entry."""
    started = time.perf_counter()
    pipeline_id = request.pipeline_id or _new_id()
    log = PipelineEventLog(pipeline_id=pipeline_id)
    gate = WriteGate()  # never opened for mastery/review on this path
    failures: list[PipelineStageFailure] = []
    obs: dict[str, str] = {}

    # Module/product path may run when pipeline full-flag is off; generation uses
    # grammar_module / authoring flags at the API layer. Allow when caller injects
    # a snapshot (offline/verify) or when pipeline flag is on.
    if not grammar_pipeline_enabled() and request.learning_snapshot is None:
        log.emit(PipelineEventType.PipelineDisabled, detail="LANG_GRAMMAR_PIPELINE_ENABLED")
        return PipelineOutcome(
            status=PipelineStatus.disabled,
            observability=PipelineObservability(
                pipeline_id=pipeline_id,
                duration_ms=round((time.perf_counter() - started) * 1000, 3),
                mode="generate",
            ),
            write_gate=gate,
            events=tuple(log.events),
            failures=(
                PipelineStageFailure(
                    stage=PipelineStage.resolve,
                    code="pipeline_disabled",
                    message="Grammar pipeline disabled",
                ),
            ),
            notes="disabled",
        )

    log.emit(
        PipelineEventType.GrammarLessonStarted,
        stage=PipelineStage.resolve.value,
        at=request.as_of,
        detail="generate_only",
    )

    try:
        if request.learning_snapshot is None:
            raise PipelineValidationError(
                "missing_learning_snapshot",
                "Generate-only path requires GrammarLearningSnapshot",
            )
        snapshot = request.learning_snapshot
        grammar_targets = stage_resolve_targets(snapshot)
        if not grammar_targets:
            raise PipelineValidationError("missing_grammar_targets", "No grammar targets resolved")
        obs["grammar_target"] = grammar_targets[0]
    except Exception as exc:  # noqa: BLE001
        failures.append(
            PipelineStageFailure(
                stage=PipelineStage.resolve,
                code=getattr(exc, "code", type(exc).__name__),
                message=str(getattr(exc, "message", exc)),
            )
        )
        log.emit(PipelineEventType.PipelineFailed, stage=PipelineStage.resolve.value)
        return PipelineOutcome(
            status=PipelineStatus.failed,
            observability=PipelineObservability(
                pipeline_id=pipeline_id,
                duration_ms=round((time.perf_counter() - started) * 1000, 3),
                mode="generate",
                **obs,
            ),
            write_gate=gate,
            events=tuple(log.events),
            failures=tuple(failures),
            notes="failed_at=resolve",
        )

    try:
        blueprint = request.blueprint or stage_plan_lesson(snapshot)
        obs["lesson_id"] = blueprint.lesson_id or blueprint.fingerprint or grammar_targets[0]
    except Exception as exc:  # noqa: BLE001
        failures.append(
            PipelineStageFailure(
                stage=PipelineStage.plan,
                code=getattr(exc, "code", type(exc).__name__),
                message=str(getattr(exc, "message", exc)),
            )
        )
        log.emit(PipelineEventType.PipelineFailed, stage=PipelineStage.plan.value)
        return PipelineOutcome(
            status=PipelineStatus.failed,
            observability=PipelineObservability(
                pipeline_id=pipeline_id,
                duration_ms=round((time.perf_counter() - started) * 1000, 3),
                mode="generate",
                grammar_target=obs.get("grammar_target", ""),
            ),
            write_gate=gate,
            events=tuple(log.events),
            failures=tuple(failures),
            grammar_targets=grammar_targets,
            notes="failed_at=plan",
        )

    authoring_invoked = False
    llm_invoked = False
    try:
        if request.specification is not None:
            specification = ensure_specification_patterns(
                request.specification, request.expected_patterns
            )
        else:
            cefr = (
                snapshot.overall_cefr.value
                if hasattr(snapshot.overall_cefr, "value")
                else str(request.overall_cefr)
            )
            specification, authoring_invoked, llm_invoked = stage_author_activity(
                grammar_targets=grammar_targets,
                student_id=request.student_id,
                language_id=request.language_id,
                overall_cefr=str(cefr),
                activity_type=request.activity_type,
                lesson_id=obs.get("lesson_id", ""),
                adaptive_snapshot=request.adaptive_snapshot,
                use_llm_authoring=request.use_llm_authoring,
                localization=request.localization,
                as_of=request.as_of,
            )
            specification = ensure_specification_patterns(
                specification, request.expected_patterns
            )
        specification = ensure_lesson_package_on_specification(
            specification,
            blueprint=blueprint,
            grammar_target=grammar_targets[0],
        )
        obs["activity_id"] = specification.activity_id
        log.emit(
            PipelineEventType.LessonGenerated,
            stage=PipelineStage.author.value,
            at=request.as_of,
            detail=specification.activity_id,
        )
    except Exception as exc:  # noqa: BLE001
        failures.append(
            PipelineStageFailure(
                stage=PipelineStage.author,
                code=getattr(exc, "code", type(exc).__name__),
                message=str(getattr(exc, "message", exc)),
            )
        )
        log.emit(PipelineEventType.PipelineFailed, stage=PipelineStage.author.value)
        return PipelineOutcome(
            status=PipelineStatus.failed,
            observability=PipelineObservability(
                pipeline_id=pipeline_id,
                lesson_id=obs.get("lesson_id", ""),
                grammar_target=obs.get("grammar_target", ""),
                duration_ms=round((time.perf_counter() - started) * 1000, 3),
                mode="generate",
            ),
            write_gate=gate,
            events=tuple(log.events),
            failures=tuple(failures),
            grammar_targets=grammar_targets,
            blueprint=blueprint,
            authoring_invoked=authoring_invoked,
            llm_authoring_invoked=llm_invoked,
            notes="failed_at=author",
        )

    log.emit(
        PipelineEventType.LessonCompleted,
        stage=PipelineStage.author.value,
        at=request.as_of,
        detail="generate_only",
    )

    return PipelineOutcome(
        status=PipelineStatus.completed,
        observability=PipelineObservability(
            pipeline_id=pipeline_id,
            lesson_id=obs.get("lesson_id", ""),
            grammar_target=obs.get("grammar_target", ""),
            activity_id=obs.get("activity_id", ""),
            duration_ms=round((time.perf_counter() - started) * 1000, 3),
            mode="generate",
        ),
        write_gate=gate,
        events=tuple(log.events),
        failures=(),
        grammar_targets=grammar_targets,
        blueprint=blueprint,
        specification=specification,
        authoring_invoked=authoring_invoked,
        llm_authoring_invoked=llm_invoked,
        execution_invoked=False,
        notes="generate_only",
        pipeline_version=GRAMMAR_PIPELINE_PACKAGE_VERSION,
    )


def lesson_dict_from_generation(outcome: PipelineOutcome) -> dict:
    """Map generate-only outcome → student-facing lesson package fields."""
    if outcome.status is not PipelineStatus.completed or outcome.specification is None:
        raise PipelineValidationError(
            "generation_incomplete",
            "Cannot build lesson response from incomplete generation",
        )
    spec = outcome.specification
    blueprint = outcome.blueprint
    payload = dict(spec.payload or {})
    title = ""
    if hasattr(spec.title, "resolve"):
        title = str(spec.title.resolve() or "")
    elif hasattr(spec.title, "values"):
        title = str(next(iter(spec.title.values.values()), "") or "")
    if not title and blueprint is not None:
        title = blueprint.lesson_goal or (blueprint.objectives[0] if blueprint.objectives else "")
    target = outcome.grammar_targets[0] if outcome.grammar_targets else payload.get("grammar_id") or spec.grammar_topic
    display_name = payload.get("display_name") or title or str(target or "").replace("gram_", "").replace("_", " ").title()
    if title.strip().lower().startswith("speaking: gram_") or title.strip().lower().startswith("gram_"):
        title = display_name
    difficulty = getattr(spec.difficulty, "value", None) or str(spec.difficulty or "guided")
    estimated = int(blueprint.estimated_duration_minutes) if blueprint else 10
    lesson_id = (
        (blueprint.lesson_id if blueprint and blueprint.lesson_id else None)
        or spec.lesson_id
        or outcome.observability.lesson_id
        or spec.activity_id
    )
    base_response = {
        "lesson_id": lesson_id,
        "lesson_schema_version": payload.get("canonical_lesson_schema_version") or CANONICAL_LESSON_SCHEMA_VERSION,
        "methodology_version": payload.get("methodology_version") or METHODOLOGY_VERSION,
        "grammar_id": payload.get("grammar_id") or target,
        "display_name": display_name,
        "cefr_level": payload.get("cefr_level") or payload.get("student_cefr") or "",
        "grammar_target": target or payload.get("grammar_focus") or "",
        "lesson_title": title or display_name,
        "estimated_minutes": estimated,
        "difficulty": difficulty,
        "pipeline_id": outcome.observability.pipeline_id,
        "activity_id": spec.activity_id,
    }

    def retry_response(reason: str) -> dict:
        return {
            **base_response,
            "student_content": {},
            "teacher_opening": "",
            "lesson_goal": "",
            "warmup": "",
            "main_activity": "",
            "follow_up_questions": [],
            "common_mistakes": [],
            "expected_patterns": [],
            "completion_message": "",
            "generation_mode": reason or RETRY_GENERATION_MODE,
            "authoring_status": RETRY_AUTHORING_STATUS,
            "retry_message": payload.get("retry_message") or RETRY_MESSAGE_AR,
        }

    generation_mode = str(payload.get("generation_mode") or "").strip().lower()
    if (
        payload.get("authoring_status") == RETRY_AUTHORING_STATUS
        or generation_mode.startswith(("temporary_", "fallback", "retry_required"))
    ):
        return retry_response(payload.get("generation_mode") or RETRY_GENERATION_MODE)

    student_content = {}
    if payload.get(PAYLOAD_STUDENT_CONTENT_KEY):
        try:
            parsed_student_content = json.loads(payload[PAYLOAD_STUDENT_CONTENT_KEY])
        except json.JSONDecodeError:
            parsed_student_content = {}
        if isinstance(parsed_student_content, dict):
            student_content = parsed_student_content
    if not student_content:
        return retry_response("retry_required_missing_student_content")
    if (payload.get("methodology_version") or "") != METHODOLOGY_VERSION:
        return retry_response("retry_required_stale_methodology")
    try:
        validate_student_content_integrity(
            student_content,
            allowed_targets=tuple(outcome.grammar_targets or (target,)),
            support_targets=tuple(
                _grammar_authoring_profile(tuple(outcome.grammar_targets or (target,))).get("support_grammar_targets")
                or ()
            ),
            cefr_level=base_response["cefr_level"],
            max_contrasts_and_mistakes=_max_contrasts_and_mistakes_for_targets(tuple(outcome.grammar_targets or (target,))),
        )
    except LLMSchemaError:
        return retry_response("retry_required_invalid_student_content")

    package = lesson_package_from_specification_payload(payload)
    mistakes = [
        {"incorrect": m.incorrect, "correct": m.correct} for m in package.common_mistakes
    ]
    return {
        **base_response,
        "lesson_title": title or display_name or package.lesson_goal,
        "student_content": student_content,
        "teacher_opening": package.teacher_opening,
        "lesson_goal": package.lesson_goal,
        "warmup": package.warmup,
        "main_activity": package.main_activity,
        "follow_up_questions": list(package.follow_up_questions),
        "common_mistakes": mistakes,
        "expected_patterns": list(package.expected_patterns),
        "completion_message": package.completion_message,
        "generation_mode": payload.get("generation_mode") or "generate_only",
        "authoring_status": "ready",
        "retry_message": "",
    }
