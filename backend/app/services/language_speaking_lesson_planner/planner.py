"""Deterministic speaking lesson blueprint assembly (S9 spine + S10.1 educational missions)."""

from __future__ import annotations

import dataclasses
import hashlib
import uuid
from datetime import datetime, timezone

from app.services.language_speaking.enums import (
    SpeakingEvidenceIntent,
    SpeakingExecutionMode,
    SpeakingMissionKind,
    SpeakingTeachingBlockKind,
)
from app.services.language_speaking_curriculum.skill_catalog import SPEAKING_SKILL_GRAPH
from app.services.language_speaking_curriculum.types import SpeakingSkillGraph
from app.services.language_speaking_diagnostic.types import DiagnosticRecommendation, TargetSelectionReason
from app.services.language_speaking_lesson_planner.blueprint_hash import compute_blueprint_hash
from app.services.language_speaking_lesson_planner.identity import make_task_id
from app.services.language_speaking_lesson_planner.mission_types import (
    SpeakingEducationalMission,
    SpeakingExecutableTask,
    SpeakingLearningObjective,
    SpeakingMissionOutcome,
    SpeakingTeachingBlock,
)
from app.services.language_speaking_lesson_planner.task_taxonomy import taxonomy_entry
from app.services.language_speaking_lesson_planner.types import (
    AlexTutoringContext,
    BLUEPRINT_COMPATIBILITY_NOTES,
    BLUEPRINT_SCHEMA_VERSION,
    BLUEPRINT_VERSION,
    SpeakingLessonBlueprint,
    SpeakingSessionActivity,
    SpeakingSessionActivityKind,
    SpeakingSessionMode,
)

# Legacy S9 activity kind that each educational mission bridges to, when one exists.
# Missions without an entry here are NOT wired to a legacy activity (explicit, not empty
# magic): their executable task carries a blank legacy_activity_ref and remains part of
# the FUTURE execution plan (see identity.py compatibility boundary).
MISSION_LEGACY_ACTIVITY: dict[SpeakingMissionKind, SpeakingSessionActivityKind] = {
    SpeakingMissionKind.guided_practice: SpeakingSessionActivityKind.guided_practice,
    SpeakingMissionKind.speak: SpeakingSessionActivityKind.communicative_task,
}
# Back-compat alias for planners that still import the private name.
_MISSION_LEGACY_ACTIVITY = MISSION_LEGACY_ACTIVITY


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _activity_id(kind: SpeakingSessionActivityKind, target: str) -> str:
    return f"act-{kind.value}-{hashlib.sha256(target.encode()).hexdigest()[:8]}"


def _mission_id(blueprint_id: str, kind: SpeakingMissionKind, order: int) -> str:
    """Blueprint-scoped mission identity — unique across blueprints for the same skill."""
    raw = f"{blueprint_id}:{kind.value}:{order}"
    return f"spk-mis-{kind.value}-{hashlib.sha256(raw.encode()).hexdigest()[:12]}"


def _teaching_block_id(blueprint_id: str, kind: SpeakingTeachingBlockKind, target: str) -> str:
    raw = f"{blueprint_id}:{kind.value}:{target}"
    return f"spk-tb-{kind.value}-{hashlib.sha256(raw.encode()).hexdigest()[:8]}"


def _objective(target: str, label: str, intent: SpeakingEvidenceIntent, prereqs: tuple[str, ...]) -> SpeakingLearningObjective:
    return SpeakingLearningObjective(
        objective_id=f"spk-obj-{hashlib.sha256(f'{target}:{intent.value}'.encode()).hexdigest()[:8]}",
        target_skill_id=target,
        student_objective_text=f"Use {label} clearly when you speak.",
        expected_outcome=f"You can produce {label} in a real speaking turn.",
        evidence_expectation=intent,
        prerequisite_skill_ids=prereqs,
    )


def _teaching_block(blueprint_id: str, kind: SpeakingTeachingBlockKind, target: str, label: str, body: str) -> SpeakingTeachingBlock:
    titles = {
        SpeakingTeachingBlockKind.explanation: f"What is {label}?",
        SpeakingTeachingBlockKind.example: f"Example: {label}",
        SpeakingTeachingBlockKind.contrast: f"Compare: {label}",
        SpeakingTeachingBlockKind.noticing_cue: f"Notice: {label}",
        SpeakingTeachingBlockKind.scaffold: f"Sentence frame for {label}",
        SpeakingTeachingBlockKind.guided_prompt: f"Try it: {label}",
        SpeakingTeachingBlockKind.misconception_correction: f"Common slip with {label}",
    }
    return SpeakingTeachingBlock(
        block_id=_teaching_block_id(blueprint_id, kind, target),
        kind=kind,
        title=titles.get(kind, label),
        body=body,
        target_skill_ids=(target,),
        is_evidence=False,
    )


# --- Adaptive mission-plan selection (S10.1) --------------------------------------
#
# Composition is chosen from the ONLY planning signal currently, truthfully, available
# to the planner: DiagnosticRecommendation.selection_reason. This is coarse,
# recommendation-based branching. Live S2 mastery/confidence, S7 evidence, S8 mutation
# results, and S9 in-session turn state are NOT passed to the planner today and are
# therefore NOT consumed here (documented limitation for S11).

MissionPlan = tuple[SpeakingMissionKind, ...]

PLAN_SUPPORT_HEAVY: MissionPlan = (
    SpeakingMissionKind.teaching,
    SpeakingMissionKind.noticing,
    SpeakingMissionKind.guided_practice,
    SpeakingMissionKind.speak,
    SpeakingMissionKind.feedback,
)
PLAN_STANDARD: MissionPlan = (
    SpeakingMissionKind.noticing,
    SpeakingMissionKind.guided_practice,
    SpeakingMissionKind.speak,
    SpeakingMissionKind.feedback,
)
PLAN_LIGHTER: MissionPlan = (
    SpeakingMissionKind.noticing,
    SpeakingMissionKind.speak,
    SpeakingMissionKind.feedback,
)
PLAN_TRANSFER: MissionPlan = (
    SpeakingMissionKind.speak,
    SpeakingMissionKind.feedback,
    SpeakingMissionKind.transfer,
)
PLAN_RETENTION: MissionPlan = (
    SpeakingMissionKind.speak,
    SpeakingMissionKind.feedback,
    SpeakingMissionKind.retention_review,
)


def select_mission_plan(reason: TargetSelectionReason) -> tuple[str, MissionPlan]:
    """Deterministically map a diagnostic selection reason to a mission plan variant.

    Returns (variant_label, ordered mission kinds). Retry is never included (it is a
    runtime flow decision). Retention only appears under the explicit at_risk_retention
    signal.
    """
    if reason == TargetSelectionReason.sparse_evidence_safe_start:
        return "support_heavy", PLAN_SUPPORT_HEAVY
    if reason == TargetSelectionReason.at_risk_retention:
        return "retention", PLAN_RETENTION
    if reason in (TargetSelectionReason.reinforcement,):
        return "lighter", PLAN_LIGHTER
    if reason in (TargetSelectionReason.progression_next,):
        return "transfer", PLAN_TRANSFER
    # weak_mastery / pronunciation_weakness / delivery_weakness / task_weakness /
    # remediation_follow_up -> standard guided path.
    return "standard", PLAN_STANDARD


def build_educational_missions(
    recommendation: DiagnosticRecommendation,
    *,
    label: str,
    blueprint_id: str,
    activity_ids: dict[SpeakingSessionActivityKind, str],
) -> tuple[SpeakingEducationalMission, ...]:
    """Adaptive, blueprint-scoped educational mission sequence (S10.1).

    Composition varies with the diagnostic selection reason (>= 4 structurally different
    shapes). No LLM, no stage/CEFR mutation, no durable lineage. Retry is never
    pre-emitted; retention only under an explicit signal. Teaching blocks carry
    deterministic scaffolding text; richer content is filled by
    language_speaking_generation.
    """
    target = recommendation.primary_target_skill_id
    prereqs = recommendation.target_skill_ids
    reason = TargetSelectionReason(recommendation.selection_reason)
    _variant_label, plan = select_mission_plan(reason)

    def _task(kind: SpeakingMissionKind, index: int, prompt: str, context_descriptor: str = "") -> SpeakingExecutableTask:
        entry = taxonomy_entry(kind)
        legacy_kind = _MISSION_LEGACY_ACTIVITY.get(kind)
        return SpeakingExecutableTask(
            task_id=make_task_id(blueprint_id, kind.value, index),
            execution_mode=entry.default_execution_mode,
            evidence_intent=entry.default_evidence_intent,
            prompt=prompt,
            target_skill_ids=(target,),
            context_descriptor=context_descriptor,
            legacy_activity_ref=activity_ids.get(legacy_kind, "") if legacy_kind else "",
        )

    def _mission(kind: SpeakingMissionKind, order: int) -> SpeakingEducationalMission:
        entry = taxonomy_entry(kind)
        objectives: tuple[SpeakingLearningObjective, ...] = ()
        teaching_blocks: tuple[SpeakingTeachingBlock, ...] = ()
        tasks: tuple[SpeakingExecutableTask, ...] = ()
        retry_policy = SpeakingMissionOutcome.proceed
        title = kind.value.replace("_", " ").title()
        instructions = ""

        if kind is SpeakingMissionKind.teaching:
            title, instructions = f"Learn: {label}", f"Learn how {label} works before you speak."
            objectives = (_objective(target, label, SpeakingEvidenceIntent.none, prereqs),)
            teaching_blocks = (
                _teaching_block(blueprint_id, SpeakingTeachingBlockKind.explanation, target, label,
                                f"{label} helps you express yourself more clearly."),
                _teaching_block(blueprint_id, SpeakingTeachingBlockKind.example, target, label,
                                f"Listen to a short model that uses {label}."),
            )
        elif kind is SpeakingMissionKind.noticing:
            title, instructions = f"Notice: {label}", f"Spot where {label} appears and why it matters."
            teaching_blocks = (
                _teaching_block(blueprint_id, SpeakingTeachingBlockKind.noticing_cue, target, label,
                                f"Notice the moment where {label} changes the meaning."),
                _teaching_block(blueprint_id, SpeakingTeachingBlockKind.contrast, target, label,
                                f"Compare a weaker answer with one that uses {label}."),
            )
        elif kind is SpeakingMissionKind.guided_practice:
            title, instructions = "Guided practice", f"Practise {label} with short sentence frames."
            objectives = (_objective(target, label, SpeakingEvidenceIntent.formative, prereqs),)
            teaching_blocks = (
                _teaching_block(blueprint_id, SpeakingTeachingBlockKind.scaffold, target, label,
                                f"Frame: 'I think ___ because ___' to practise {label}."),
                _teaching_block(blueprint_id, SpeakingTeachingBlockKind.guided_prompt, target, label,
                                f"Now answer one guided prompt using {label}."),
            )
            tasks = (_task(kind, order, f"Answer using {label} with the sentence frame."),)
            retry_policy = SpeakingMissionOutcome.retry_same_task
        elif kind is SpeakingMissionKind.speak:
            title, instructions = "Speak with Alex", f"Have a natural conversation with Alex and use {label}."
            objectives = (_objective(target, label, SpeakingEvidenceIntent.summative, prereqs),)
            tasks = (_task(kind, order, f"Speak naturally and use {label} in your answers."),)
            retry_policy = SpeakingMissionOutcome.retry_with_scaffold
        elif kind is SpeakingMissionKind.feedback:
            title, instructions = "Feedback", "Review one clear, actionable point from your speaking turn."
            teaching_blocks = (
                _teaching_block(blueprint_id, SpeakingTeachingBlockKind.misconception_correction, target, label,
                                f"A common slip: giving an opinion without using {label}. Add it next time."),
            )
        elif kind is SpeakingMissionKind.transfer:
            title, instructions = "Transfer", f"Use {label} on a new topic to show it transfers."
            objectives = (_objective(target, label, SpeakingEvidenceIntent.transfer, prereqs),)
            tasks = (_task(kind, order, f"Use {label} to discuss a different, unfamiliar topic.",
                           context_descriptor="changed_topic_context"),)
            retry_policy = SpeakingMissionOutcome.retry_same_task
        elif kind is SpeakingMissionKind.retention_review:
            title, instructions = "Review later", f"Come back later to keep {label} strong."
            tasks = (_task(kind, order, f"Quick review: use {label} once more.",
                           context_descriptor="spaced_review"),)

        return SpeakingEducationalMission(
            mission_id=_mission_id(blueprint_id, kind, order),
            mission_kind=kind,
            execution_mode=entry.default_execution_mode,
            evidence_intent=entry.default_evidence_intent,
            order_index=order,
            title=title,
            learner_instructions=instructions,
            objectives=objectives,
            target_skill_ids=(target,),
            teaching_blocks=teaching_blocks,
            tasks=tasks,
            retry_policy=retry_policy,
        )

    return tuple(_mission(kind, order) for order, kind in enumerate(plan, start=1))


def _mode_for_reason(reason: TargetSelectionReason) -> SpeakingSessionMode:
    if reason == TargetSelectionReason.remediation_follow_up:
        return SpeakingSessionMode.remediation
    if reason in (TargetSelectionReason.pronunciation_weakness, TargetSelectionReason.delivery_weakness):
        return SpeakingSessionMode.standard
    if reason == TargetSelectionReason.reinforcement:
        return SpeakingSessionMode.reinforcement
    return SpeakingSessionMode.standard


def _alex_context(node_label: str, reason: TargetSelectionReason, goal: str) -> AlexTutoringContext:
    scenario = " everyday conversation about your week"
    if reason == TargetSelectionReason.pronunciation_weakness:
        scenario = f"a short dialogue where you naturally use words with {node_label}"
    elif reason == TargetSelectionReason.task_weakness:
        scenario = "a guided role-play where you answer clearly and stay on topic"
    elif reason == TargetSelectionReason.delivery_weakness:
        scenario = "a calm back-and-forth where you speak in full, steady phrases"

    return AlexTutoringContext(
        session_goal=f"Practice {node_label} in natural conversation",
        target_skill_label=node_label,
        communicative_scenario=scenario.strip(),
        encourage_behaviors=(
            "Keep the conversation warm and natural",
            "Give the student time to respond fully",
            "Ask follow-up questions that elicit the target skill",
        ),
        elicit_behaviors=(
            f"Elicit production related to {node_label}",
            "Use short, clear prompts",
            "Model the target briefly if the student hesitates",
        ),
        retry_focus="Stay on today's target — do not constantly interrupt to correct",
        conversation_constraints=(
            "Do not assign CEFR level or mastery",
            "Do not declare promotion or stage changes",
            "Avoid drill-sergeant correction — save evaluation for the platform pipeline",
        ),
    )


def continue_alex_from_story_spine(
    alex: AlexTutoringContext,
    *,
    title: str = "",
    setting: str = "",
    characters: list[str] | tuple[str, ...] | None = None,
    conflict: str = "",
    continuation_hook: str = "",
    case_category: str = "",
    case_archetype: str = "",
    stakeholders: list[str] | tuple[str, ...] | None = None,
    decision_point: str = "",
) -> AlexTutoringContext:
    """Bind the live speaking context to the authored educational case."""

    chars = tuple(str(c).strip() for c in (characters or ()) if str(c).strip())
    stakes = tuple(str(s).strip() for s in (stakeholders or ()) if str(s).strip())
    hook = (continuation_hook or alex.case_continuation_hook or "").strip()
    return dataclasses.replace(
        alex,
        case_title=(title or alex.case_title).strip(),
        case_setting=(setting or alex.case_setting).strip(),
        case_characters=chars or alex.case_characters,
        case_conflict=(conflict or alex.case_conflict).strip(),
        case_continuation_hook=hook,
        case_category=(case_category or alex.case_category).strip(),
        case_archetype=(case_archetype or alex.case_archetype).strip(),
        case_stakeholders=stakes or alex.case_stakeholders,
        case_decision_point=(decision_point or alex.case_decision_point).strip(),
        communicative_scenario=hook or alex.communicative_scenario,
    )


def assemble_speaking_lesson_blueprint(
    recommendation: DiagnosticRecommendation,
    *,
    graph: SpeakingSkillGraph | None = None,
    session_mode: SpeakingSessionMode | None = None,
) -> SpeakingLessonBlueprint:
    """Build deterministic session blueprint from diagnostic recommendation."""
    g = graph or SPEAKING_SKILL_GRAPH
    node = g.node_by_id(recommendation.primary_target_skill_id)
    if node is None:
        raise ValueError(f"unknown_target_skill:{recommendation.primary_target_skill_id}")

    reason = TargetSelectionReason(recommendation.selection_reason)
    mode = session_mode or _mode_for_reason(reason)
    target = recommendation.primary_target_skill_id
    label = node.label

    activities = (
        SpeakingSessionActivity(
            activity_id=_activity_id(SpeakingSessionActivityKind.warmup, target),
            kind=SpeakingSessionActivityKind.warmup,
            title="Warm-up",
            learner_instructions="Take a breath and say hello — we'll ease into today's focus.",
            target_skill_ids=(target,),
            completion_criteria=("Student acknowledged warm-up",),
            optional_render_hints=("brief_greeting",),
        ),
        SpeakingSessionActivity(
            activity_id=_activity_id(SpeakingSessionActivityKind.target_intro, target),
            kind=SpeakingSessionActivityKind.target_intro,
            title=f"Learn: {label}",
            learner_instructions=f"Today's focus is {label}. {recommendation.reason_detail}",
            target_skill_ids=(target,),
            completion_criteria=("Target introduced",),
            optional_render_hints=("target_explanation", label),
        ),
        SpeakingSessionActivity(
            activity_id=_activity_id(SpeakingSessionActivityKind.guided_practice, target),
            kind=SpeakingSessionActivityKind.guided_practice,
            title="Guided practice",
            learner_instructions=f"Repeat and try short phrases using {label}.",
            target_skill_ids=(target,),
            completion_criteria=("Completed guided prompts",),
            optional_render_hints=("guided_drill",),
        ),
        SpeakingSessionActivity(
            activity_id=_activity_id(SpeakingSessionActivityKind.communicative_task, target),
            kind=SpeakingSessionActivityKind.communicative_task,
            title="Speak with Alex",
            learner_instructions="Have a natural conversation with Alex using today's focus.",
            target_skill_ids=(target,),
            completion_criteria=("At least one live turn evaluated", "Minimum communicative exchanges"),
            optional_render_hints=("live_evi",),
        ),
        SpeakingSessionActivity(
            activity_id=_activity_id(SpeakingSessionActivityKind.reflection, target),
            kind=SpeakingSessionActivityKind.reflection,
            title="Session reflection",
            learner_instructions="Review what went well and what to try next time.",
            target_skill_ids=(target,),
            completion_criteria=("Session outcome reviewed",),
            optional_render_hints=("reflection",),
        ),
    )

    activity_ids = {a.kind: a.activity_id for a in activities}
    # Mint blueprint_id first so mission/task identity is blueprint-scoped (S10.1).
    blueprint_id = f"spk-bp-{uuid.uuid4().hex[:12]}"
    educational_missions = build_educational_missions(
        recommendation,
        label=label,
        blueprint_id=blueprint_id,
        activity_ids=activity_ids,
    )
    draft = SpeakingLessonBlueprint(
        blueprint_id=blueprint_id,
        blueprint_version=BLUEPRINT_VERSION,
        schema_version=BLUEPRINT_SCHEMA_VERSION,
        compatibility_notes=BLUEPRINT_COMPATIBILITY_NOTES,
        blueprint_hash="",
        recommendation_id=recommendation.recommendation_id,
        session_goal=f"Build confidence with {label}",
        target_skill_ids=recommendation.target_skill_ids,
        primary_target_skill_id=target,
        selection_reason=recommendation.selection_reason,
        reason_detail=recommendation.reason_detail,
        evidence_basis=recommendation.evidence_basis,
        session_mode=mode,
        official_cefr_hint=recommendation.official_cefr_hint,
        speaking_goal=recommendation.speaking_goal,
        activities=activities,
        alex_context=_alex_context(label, reason, recommendation.speaking_goal),
        completion_evidence_requirements=("communicative_turn_evaluated", "session_boundary_decision"),
        remediation_strategy="Short scenario retry on same target with clearer task framing",
        retry_strategy="Focused retry on same target with adjusted activity/scenario",
        min_communicative_turns=2,
        educational_missions=educational_missions,
    )
    bp_hash = compute_blueprint_hash(draft)
    return dataclasses.replace(draft, blueprint_hash=bp_hash)
