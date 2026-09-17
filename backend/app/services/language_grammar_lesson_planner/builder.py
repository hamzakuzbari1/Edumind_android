"""Blueprint builder (G3.1) — pure, deterministic, no engine imports."""

from __future__ import annotations

import hashlib
import json

from app.services.language_grammar.enums import GrammarLessonStepKind
from app.services.language_grammar_integration.types import GrammarLearningSnapshot
from app.services.language_grammar_lesson_planner.policies import (
    DEFAULT_POLICY_ID,
    STEP_DURATION,
    context_hint_for,
    duration_budget,
    lesson_goal_for,
    needs_warmup,
    practice_item_count,
    select_quick_review_id,
    select_reinforcement_skills,
    skill_to_reinforcement_kind,
)
from app.services.language_grammar_lesson_planner.types import (
    GRAMMAR_BLUEPRINT_VERSION,
    GRAMMAR_PLANNER_VERSION,
    GRAMMAR_SCHEMA_VERSION,
    GrammarCompletionCriteria,
    GrammarEvidencePlan,
    GrammarLessonBlueprint,
    GrammarLessonStep,
    GrammarPlannerMetadata,
    GrammarPracticeSpec,
)
from app.services.language_grammar_lesson_planner.validation import (
    GrammarPlannerError,
    validate_blueprint,
    validate_snapshot_for_planning,
)


def _fingerprint(payload: dict) -> str:
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:32]


def _step(
    kind: GrammarLessonStepKind,
    step_id: str,
    *,
    skill=None,
    evidence_eligible: bool = False,
    context_hint: str | None = None,
    title: str = "",
) -> GrammarLessonStep:
    return GrammarLessonStep(
        kind=kind,
        step_id=step_id,
        skill=skill,
        evidence_eligible=evidence_eligible,
        context_hint=context_hint,
        estimated_minutes=STEP_DURATION[kind],
        title=title or kind.value.replace("_", " ").title(),
    )


def build_blueprint(snapshot: GrammarLearningSnapshot) -> GrammarLessonBlueprint:
    """Build a frozen GrammarLessonBlueprint from GrammarLearningSnapshot only."""
    validate_snapshot_for_planning(snapshot)
    topic = snapshot.current_topic
    if topic is None:
        raise GrammarPlannerError("Missing current topic metadata")

    focus_id = snapshot.current_grammar_id
    assert focus_id is not None
    mastery = snapshot.mastery_for(focus_id)
    budget = duration_budget(snapshot)
    reasons: list[str] = [f"policy:{DEFAULT_POLICY_ID}", f"focus:{focus_id}", f"budget:{budget}"]

    steps: list[GrammarLessonStep] = []
    used = 0

    def can_add(kind: GrammarLessonStepKind) -> bool:
        return used + STEP_DURATION[kind] <= budget or kind in (
            GrammarLessonStepKind.explanation,
            GrammarLessonStepKind.practice,
            GrammarLessonStepKind.exit_check,
        )

    def add(step: GrammarLessonStep) -> None:
        nonlocal used
        steps.append(step)
        used += step.estimated_minutes

    # Optional warmup
    if needs_warmup(mastery) and can_add(GrammarLessonStepKind.warmup):
        add(_step(GrammarLessonStepKind.warmup, "warmup", title="Warmup"))
        reasons.append("warmup:low_mastery_or_new")

    # Quick review NEVER blocks today's lesson — insert before core grammar when useful
    review_id = select_quick_review_id(snapshot, focus_id)
    included_review = False
    if review_id and can_add(GrammarLessonStepKind.quick_review):
        add(
            _step(
                GrammarLessonStepKind.quick_review,
                "quick_review",
                evidence_eligible=True,
                context_hint=context_hint_for(snapshot.topic_meta(review_id) or topic, 0),
                title="Quick Review",
            )
        )
        included_review = True
        reasons.append(f"quick_review:{review_id}")

    # Core today
    add(_step(GrammarLessonStepKind.explanation, "explanation", title="Explanation"))
    add(
        _step(
            GrammarLessonStepKind.practice,
            "practice",
            evidence_eligible=True,
            context_hint=context_hint_for(topic, 0),
            title="Practice",
        )
    )
    reasons.append("core:explanation+practice")

    # Dynamic reinforcements from catalog best_reinforcement_skills
    remaining = budget - used - STEP_DURATION[GrammarLessonStepKind.exit_check] - STEP_DURATION[
        GrammarLessonStepKind.summary
    ]
    skills = select_reinforcement_skills(topic, mastery, budget_remaining=max(0, remaining))
    for idx, skill in enumerate(skills):
        kind = skill_to_reinforcement_kind(skill)
        add(
            _step(
                kind,
                f"reinforce_{skill.value}",
                skill=skill,
                evidence_eligible=True,
                context_hint=context_hint_for(topic, idx + 1),
                title=f"{skill.value.title()} Reinforcement",
            )
        )
    if skills:
        reasons.append("reinforce:" + ",".join(s.value for s in skills))

    add(_step(GrammarLessonStepKind.exit_check, "exit_check", evidence_eligible=True, title="Exit Check"))
    add(_step(GrammarLessonStepKind.summary, "summary", title="Summary"))

    # Homework when budget still has room and next topic exists
    if snapshot.next_grammar_id and (used + STEP_DURATION[GrammarLessonStepKind.homework]) <= budget:
        add(_step(GrammarLessonStepKind.homework, "homework", title="Homework"))
        reasons.append(f"homework:next:{snapshot.next_grammar_id}")

    goal = lesson_goal_for(topic)
    objectives = tuple(topic.learning_objectives) or (goal,)
    eligible_ids = tuple(s.step_id for s in steps if s.evidence_eligible)
    duration = sum(s.estimated_minutes for s in steps)
    lesson_id = f"gless_{focus_id}_{snapshot.student_id}_{snapshot.as_of}"

    meta = GrammarPlannerMetadata(
        policy_id=DEFAULT_POLICY_ID,
        included_quick_review=included_review,
        review_grammar_id=review_id if included_review else None,
        reinforcement_skills=skills,
        duration_budget_minutes=budget,
        reasons=tuple(reasons),
    )
    practice = GrammarPracticeSpec(
        item_count=practice_item_count(mastery),
        recommended_contexts=tuple(topic.recommended_contexts),
        focus_note=topic.focus_note,
    )
    evidence = GrammarEvidencePlan(
        eligible_step_ids=eligible_ids,
        min_observations=max(1, min(3, topic.evidence_min_observations)),
        observation_types_hint=("formative", "summative"),
    )
    completion = GrammarCompletionCriteria(
        require_all_steps=True,
        require_exit_check=True,
        min_evidence_eligible_steps_completed=1,
        notes="Complete all steps; exit check required",
    )

    fp_payload = {
        "lesson_id": lesson_id,
        "grammar_id": focus_id,
        "steps": [(s.kind.value, s.step_id, s.skill.value if s.skill else None) for s in steps],
        "catalog_version": snapshot.catalog_version,
        "planner_version": GRAMMAR_PLANNER_VERSION,
        "blueprint_version": GRAMMAR_BLUEPRINT_VERSION,
        "policy": DEFAULT_POLICY_ID,
    }
    blueprint = GrammarLessonBlueprint(
        grammar_id=focus_id,
        target_cefr=topic.cefr_band,
        objectives=objectives,
        steps=tuple(steps),
        practice_spec=practice,
        evidence_plan=evidence,
        fingerprint=_fingerprint(fp_payload),
        lesson_id=lesson_id,
        lesson_goal=goal,
        estimated_duration_minutes=duration,
        completion_criteria=completion,
        planner_metadata=meta,
        blueprint_version=GRAMMAR_BLUEPRINT_VERSION,
        planner_version=GRAMMAR_PLANNER_VERSION,
        catalog_version=snapshot.catalog_version,
        grammar_schema_version=GRAMMAR_SCHEMA_VERSION,
        frozen=True,
        enabled=True,
    )
    validate_blueprint(blueprint, snapshot=snapshot)
    return blueprint


def disabled_blueprint(*, grammar_id: str = "", reason: str = "flag:disabled") -> GrammarLessonBlueprint:
    """Empty disabled blueprint when engine flags are off."""
    from app.services.language_grammar.enums import GrammarCEFRBand

    return GrammarLessonBlueprint(
        grammar_id=grammar_id or "gram_disabled",
        target_cefr=GrammarCEFRBand.A1,
        objectives=(),
        steps=(),
        lesson_goal="",
        estimated_duration_minutes=0,
        fingerprint="",
        planner_metadata=GrammarPlannerMetadata(policy_id=DEFAULT_POLICY_ID, reasons=(reason,)),
        frozen=True,
        enabled=False,
        catalog_version="disabled",
    )
