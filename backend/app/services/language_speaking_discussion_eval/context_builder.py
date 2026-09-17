"""Build S7-compatible evaluation packaging from discussion turns (no scoring)."""

from __future__ import annotations

from app.services.language_educational_package.types import DiscussionStep, EducationalPackage
from app.services.language_speaking.enums import SpeakingEvidenceIntent
from app.services.language_speaking_discussion.types import DiscussionRuntimeState
from app.services.language_speaking_discussion_eval.types import (
    DiscussionEvalContext,
    DiscussionEvidenceCategory,
    DiscussionProductionMode,
)
from app.services.language_speaking_evaluator.input_types import (
    SpeakingEvaluationInput,
    SpeakingGoalContext,
    SpeakingTaskContext,
)


def _discussion_id(state: DiscussionRuntimeState) -> str:
    return f"disc:{state.package_id}:{state.started_at or 'open'}"


def _objective_ref(package: EducationalPackage, step: DiscussionStep) -> str:
    meta = package.progression_metadata or {}
    focus = str(meta.get("learning_focus") or package.input_material.title or "")
    return f"{package.mission_id}:{focus}:{step.ladder_band.value}"[:240]


def _target_skill_ids(package: EducationalPackage, step: DiscussionStep) -> tuple[str, ...]:
    skills: list[str] = []
    for raw in list(step.vocabulary_ids) + list(step.grammar_topic_ids):
        s = str(raw).strip()
        if s.startswith("spk_") and s not in skills:
            skills.append(s)
    meta = package.metadata or {}
    for raw in meta.get("target_skill_ids") or []:
        s = str(raw).strip()
        if s and s not in skills:
            skills.append(s)
    return tuple(skills[:12])


def task_type_for_category(category: DiscussionEvidenceCategory) -> str:
    return {
        DiscussionEvidenceCategory.vocabulary: "discussion_vocabulary",
        DiscussionEvidenceCategory.grammar: "discussion_grammar",
        DiscussionEvidenceCategory.communicative: "discussion_communicative",
        DiscussionEvidenceCategory.transfer: "discussion_transfer",
        DiscussionEvidenceCategory.informational: "discussion_informational",
    }.get(category, "discussion_formative")


def build_discussion_eval_context(
    *,
    package: EducationalPackage,
    state: DiscussionRuntimeState,
    step: DiscussionStep,
    student_response: str,
    category: DiscussionEvidenceCategory,
    production_mode: DiscussionProductionMode,
) -> DiscussionEvalContext:
    disc_id = _discussion_id(state)
    return DiscussionEvalContext(
        package_id=package.package_id,
        discussion_id=disc_id,
        discussion_step_id=step.step_id,
        question_id=step.step_id,
        student_response=student_response,
        lesson_objective_ref=_objective_ref(package, step),
        ladder_band=step.ladder_band.value,
        evidence_role=step.evidence_role.value,
        evidence_category=category.value,
        production_mode=production_mode.value,
    )


def build_speaking_task_context(
    *,
    package: EducationalPackage,
    step: DiscussionStep,
    category: DiscussionEvidenceCategory,
) -> SpeakingTaskContext:
    cues = tuple(str(c) for c in (step.success_cues or []) if str(c).strip())
    instructions = (
        f"Guided discussion step ({step.ladder_band.value}). "
        f"Respond using package focus; soft cues are not hard scorer gates."
    )
    return SpeakingTaskContext(
        task_id=f"discussion:{package.package_id}:{step.step_id}",
        task_type=task_type_for_category(category),
        task_prompt=step.prompt,
        task_instructions=instructions,
        success_criteria=cues,
        target_skill_ids=_target_skill_ids(package, step),
    )


def build_speaking_goal_context(
    *,
    package: EducationalPackage,
    evidence_intent: SpeakingEvidenceIntent,
) -> SpeakingGoalContext:
    label = {
        SpeakingEvidenceIntent.transfer: "Discussion transfer practice",
        SpeakingEvidenceIntent.formative: "Discussion formative practice",
    }.get(evidence_intent, "Discussion practice")
    return SpeakingGoalContext(
        speaking_goal=f"discussion_{evidence_intent.value}",
        goal_label=f"{label}: {package.input_material.title}"[:120],
    )


def build_speaking_evaluation_input(
    *,
    student_response: str,
    reliability: float,
) -> SpeakingEvaluationInput:
    text = (student_response or "").strip()
    tokens = tuple(text.lower().split())
    return SpeakingEvaluationInput(
        transcript_text=text,
        transcript_word_count=len(tokens),
        transcript_tokens=tokens,
        evidence_availability={"transcript": bool(text)},
        evidence_reliability=float(reliability) if text else 0.0,
        processing_warnings=("discussion_text_path",),
    )


def mint_turn_reference(
    *,
    package_id: str,
    step_id: str,
    student_turn_index: int,
) -> str:
    return f"discussion:{package_id}:{step_id}:t{student_turn_index}"


def count_student_turns_for_step(state: DiscussionRuntimeState, step_id: str) -> int:
    return sum(1 for t in state.turns if t.role == "student" and t.step_id == step_id)
