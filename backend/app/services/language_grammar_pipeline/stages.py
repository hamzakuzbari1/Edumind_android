"""Thin stage adapters — call existing Grammar Engine public APIs only.

No educational logic lives here.
"""

from __future__ import annotations

import json
from dataclasses import replace

from app.services.language_grammar.enums import GrammarEvidenceSourceSkill
from app.services.language_grammar_activity_authoring import (
    AdaptiveAuthoringContext,
    AuthoringContext,
    AuthoringRequest,
    AuthoringVersionBundle,
    LessonContext,
    StudentProfile,
    TeacherPersona,
    author_activity,
    author_activity_with_llm,
    empty_learning_snapshot,
    llm_authoring_enabled,
)
from app.services.language_grammar_activity_authoring.adaptive import StudentLearningSnapshot
from app.services.language_grammar_activity_spec import (
    ActivitySpecification,
    ActivityType,
    with_fingerprint,
)
from app.services.language_grammar_catalog.catalog import get_topic
from app.services.language_grammar_evaluation import (
    LessonPackageView,
    build_evaluation_request,
    evaluate_grammar,
    lesson_view_from_specification,
)
from app.services.language_grammar_evaluation.types import GrammarEvaluationResult
from app.services.language_grammar_evidence.types import GrammarEvidenceBatch
from app.services.language_grammar_evidence.validation import validate_batch
from app.services.language_grammar_integration import (
    GrammarResolveTargetsRequest,
    resolve_targets_from_snapshot,
    sync_completed_topics,
)
from app.services.language_grammar_integration.types import GrammarLearningSnapshot
from app.services.language_grammar_lesson_planner import plan_lesson
from app.services.language_grammar_lesson_planner.types import GrammarLessonBlueprint
from app.services.language_grammar_mastery import compute_mastery_from_evidence
from app.services.language_grammar_mastery.types import GrammarMasterySnapshot
from app.services.language_grammar_progression.types import (
    GrammarProgressionSnapshot,
    GrammarProgressionStudentState,
)
from app.services.language_grammar_review import compute_from_mastery
from app.services.language_grammar_review.engine import empty_student_state
from app.services.language_grammar_review.types import GrammarReviewSnapshot
from app.services.language_grammar_skill_executor import (
    StudentContext,
    run_execution,
)
from app.services.language_grammar_skill_executor.session import ExecutionEngineState


def _grammar_authoring_profile(grammar_targets: tuple[str, ...]) -> dict[str, object]:
    primary = grammar_targets[0] if grammar_targets else ""
    topic = get_topic(primary) if primary else None
    if topic is None:
        return {
            "selected_grammar_target": primary,
            "display_name": primary,
            "cefr_level": "",
            "learning_objectives": [],
            "canonical_patterns": list(grammar_targets),
            "required_form_keys": list(grammar_targets),
            "permitted_realizations": [],
            "functions": [],
            "mistake_categories": [],
            "forbidden_extensions": [],
            "model_examples": [],
            "common_mistakes": [],
            "teaching_notes": "",
            "focus_note": "",
            "recommended_contexts": [],
            "arabic_speaker_misconceptions": [],
            "prerequisite_reminders": [],
        }

    source_notes = [topic.teaching_notes, topic.focus_note, *topic.common_errors]
    arabic_misconceptions = tuple(
        note for note in source_notes if "arabic" in (note or "").lower()
    )
    scope = _grammar_authoring_scope_profile(primary, topic)
    return {
        "selected_grammar_target": primary,
        "display_name": topic.display_name,
        "cefr_level": topic.cefr_band.value,
        "learning_objectives": list(topic.learning_objectives),
        "canonical_patterns": list(topic.demonstration_patterns or grammar_targets),
        "required_form_keys": list(scope["required_form_keys"]),
        "permitted_realizations": list(scope["permitted_realizations"]),
        "functions": list(scope["functions"]),
        "mistake_categories": list(scope["mistake_categories"]),
        "forbidden_extensions": list(scope["forbidden_extensions"]),
        "model_examples": list(topic.example_sentences),
        "common_mistakes": list(topic.common_errors),
        "teaching_notes": topic.teaching_notes,
        "focus_note": topic.focus_note,
        "recommended_contexts": list(topic.recommended_contexts),
        "arabic_speaker_misconceptions": list(arabic_misconceptions),
        "prerequisite_reminders": list(topic.prerequisite_ids),
        "support_grammar_targets": list(
            dict.fromkeys([*topic.prerequisite_ids, *topic.future_topic_ids])
        ),
    }


def _grammar_authoring_scope_profile(primary: str, topic) -> dict[str, tuple[str, ...]]:
    if primary == "gram_be_present":
        return {
            "required_form_keys": (
                "affirmative_am",
                "affirmative_is",
                "affirmative_are",
                "negative_am_not",
                "negative_is_not",
                "negative_are_not",
                "question_am",
                "question_is",
                "question_are",
                "short_answer_am",
                "short_answer_is",
                "short_answer_are",
            ),
            "permitted_realizations": (
                "am",
                "is",
                "are",
                "am not",
                "is not",
                "are not",
                "isn't",
                "aren't",
                "I'm not",
                "Am I ...?",
                "Is he/she/it ...?",
                "Are you/we/they ...?",
                "Yes, I am.",
                "No, I'm not.",
                "Yes, she is.",
                "No, she isn't.",
                "Yes, they are.",
                "No, they aren't.",
            ),
            "functions": (
                "identity",
                "description/state",
                "location",
                "negative meaning",
                "yes/no question",
                "short answer",
            ),
            "mistake_categories": (
                "be_deletion",
                "wrong_be_agreement",
                "missing_not",
                "statement_order_question",
                "do_does_with_be",
                "incomplete_short_answer",
            ),
            "forbidden_extensions": (
                "past_be_was_were",
                "future_be",
                "present_perfect",
                "present_continuous",
                "modal_verbs",
                "detailed_wh_questions",
                "tag_questions",
                "unrelated_auxiliary_grammar",
                "amn't",
            ),
        }
    patterns = tuple(topic.demonstration_patterns or (primary,))
    return {
        "required_form_keys": patterns,
        "permitted_realizations": patterns,
        "functions": tuple(topic.learning_objectives),
        "mistake_categories": tuple(topic.common_errors),
        "forbidden_extensions": (),
    }


def stage_resolve_targets(snapshot: GrammarLearningSnapshot) -> tuple[str, ...]:
    """Resolve WHAT to teach from Integration snapshot (no progression algorithm here)."""
    targets: list[str] = []
    if snapshot.current_grammar_id:
        targets.append(snapshot.current_grammar_id)
    if snapshot.next_grammar_id and snapshot.next_grammar_id not in targets:
        targets.append(snapshot.next_grammar_id)
    return tuple(targets[:2])


def stage_plan_lesson(snapshot: GrammarLearningSnapshot) -> GrammarLessonBlueprint:
    return plan_lesson(snapshot)


def stage_author_activity(
    *,
    grammar_targets: tuple[str, ...],
    student_id: int,
    language_id: int,
    overall_cefr: str,
    activity_type: str,
    lesson_id: str,
    adaptive_snapshot: StudentLearningSnapshot | None,
    use_llm_authoring: bool,
    localization: str,
    as_of: str,
) -> tuple[ActivitySpecification, bool, bool]:
    """Returns (specification, authoring_invoked, llm_authoring_invoked)."""
    learning = adaptive_snapshot or empty_learning_snapshot()
    ctx = AuthoringContext(
        grammar_targets=grammar_targets,
        student_cefr=overall_cefr,
        learning_objective=f"Practice {grammar_targets[0]}" if grammar_targets else "Practice grammar",
        teacher_persona=TeacherPersona(),
        student_profile=StudentProfile(
            student_id=student_id,
            language_id=language_id,
            overall_cefr=overall_cefr,
            locale=localization,
        ),
        lesson_context=LessonContext(lesson_id=lesson_id, step_id="practice"),
        activity_type=activity_type or ActivityType.voice_recording.value,
        localization=localization,
        adaptive=AdaptiveAuthoringContext(learning_snapshot=learning),
        versions=AuthoringVersionBundle(
            catalog_version="1.0.0",
            grammar_schema_version=1,
            blueprint_version="1.0.0",
            activity_schema_version=1,
            planner_version="1.0.0",
        ),
        extras={
            "grammar_profile_json": json.dumps(
                _grammar_authoring_profile(grammar_targets),
                ensure_ascii=True,
                sort_keys=True,
            )
        },
    )
    request = AuthoringRequest(context=ctx, request_id=f"pipe_{lesson_id or as_of or 'auth'}")
    llm_invoked = False
    if use_llm_authoring and llm_authoring_enabled():
        spec = author_activity_with_llm(request)
        llm_invoked = True
    else:
        spec = author_activity(request)
    return spec, True, llm_invoked


def stage_execute(
    specification: ActivitySpecification,
    *,
    student_id: int,
    language_id: int,
    student_response: str,
    as_of: str,
    localization: str,
) -> ExecutionEngineState:
    """Execute via Skill Executor (placeholder speaking runtime — no speaking journey bridge)."""
    return run_execution(
        specification,
        student=StudentContext(student_id=student_id, language_id=language_id),
        student_response=student_response,
        localization=localization,
        as_of=as_of or "pipeline_t0",
        require_enabled=False,
        emit_evidence=True,
    )


def stage_evaluate(
    *,
    grammar_targets: tuple[str, ...],
    student_response: str,
    specification: ActivitySpecification,
    expected_patterns: tuple[str, ...],
    student_id: int,
    language_id: int,
    as_of: str,
    evaluation_id: str,
) -> GrammarEvaluationResult:
    lesson = lesson_view_from_specification(specification)
    patterns = expected_patterns or tuple(lesson.expected_patterns)
    if not patterns:
        # Fall back to explicit empty lesson view — evaluation validation will reject if required.
        lesson = LessonPackageView(expected_patterns=patterns, grammar_focus=grammar_targets[0] if grammar_targets else "")
    req = build_evaluation_request(
        grammar_targets=grammar_targets,
        student_response=student_response,
        expected_patterns=patterns,
        lesson_package=lesson if patterns else LessonPackageView(expected_patterns=patterns),
        specification=specification,
        student_id=student_id,
        language_id=language_id,
        as_of=as_of,
        evaluation_id=evaluation_id,
        source_skill="speaking",
    )
    return evaluate_grammar(req)


def stage_evidence_batch(result: GrammarEvaluationResult) -> GrammarEvidenceBatch:
    batch = GrammarEvidenceBatch(observations=tuple(result.observations))
    validated = validate_batch(batch)
    if not validated.valid:
        raise ValueError("; ".join(validated.issues))
    return GrammarEvidenceBatch(observations=validated.observations)


def stage_mastery(
    *,
    student_id: int,
    language_id: int,
    batch: GrammarEvidenceBatch,
    prior: GrammarMasterySnapshot | None,
) -> GrammarMasterySnapshot:
    return compute_mastery_from_evidence(
        student_id=student_id,
        language_id=language_id,
        batch=batch,
        prior=prior,
    )


def stage_review(
    *,
    mastery: GrammarMasterySnapshot,
    student_id: int,
    language_id: int,
    as_of: str,
) -> GrammarReviewSnapshot:
    return compute_from_mastery(
        mastery=mastery,
        student=empty_student_state(student_id=student_id, language_id=language_id),
        as_of=as_of or None,
    )


def stage_recommend(
    *,
    student_id: int,
    language_id: int,
    progression: GrammarProgressionSnapshot | None,
    mastery: GrammarMasterySnapshot,
    progression_student: GrammarProgressionStudentState | None = None,
) -> tuple[object, object]:
    """Return (completed_sync_plan, next_recommendation). No DB progression writes."""
    if progression is None:
        return None, None
    student = progression_student or GrammarProgressionStudentState(
        student_id=student_id,
        language_id=language_id,
        current_grammar_id=progression.current_grammar_id,
    )
    sync_plan = sync_completed_topics(mastery=mastery, student=student)
    recommendation = resolve_targets_from_snapshot(
        GrammarResolveTargetsRequest(
            student_id=student_id,
            language_id=language_id,
            source_skill=GrammarEvidenceSourceSkill.speaking,
            max_targets=2,
            prefer_current=True,
        ),
        progression=progression,
        mastery=mastery,
    )
    return sync_plan, recommendation


def ensure_specification_patterns(
    specification: ActivitySpecification,
    expected_patterns: tuple[str, ...],
) -> ActivitySpecification:
    """Attach expected patterns into payload when provided — orchestration glue only."""
    if not expected_patterns:
        return specification
    import json

    payload = dict(specification.payload)
    if not payload.get("expected_patterns"):
        payload["expected_patterns"] = json.dumps(list(expected_patterns))
    if not payload.get("grammar_focus") and specification.grammar_targets:
        payload["grammar_focus"] = specification.grammar_targets[0]
    if payload == specification.payload:
        return specification
    updated = replace(specification, payload=payload)
    return with_fingerprint(updated)
