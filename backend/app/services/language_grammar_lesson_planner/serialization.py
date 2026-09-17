"""Serialize / deserialize frozen GrammarLessonBlueprint for replay."""

from __future__ import annotations

from typing import Any

from app.services.language_grammar.enums import (
    GrammarCEFRBand,
    GrammarLessonStepKind,
    GrammarReinforcementSkill,
)
from app.services.language_grammar_lesson_planner.types import (
    GrammarCompletionCriteria,
    GrammarEvidencePlan,
    GrammarLessonBlueprint,
    GrammarLessonStep,
    GrammarPlannerMetadata,
    GrammarPracticeSpec,
)


def blueprint_to_dict(blueprint: GrammarLessonBlueprint) -> dict[str, Any]:
    return {
        "lesson_id": blueprint.lesson_id,
        "grammar_id": blueprint.grammar_id,
        "target_cefr": blueprint.target_cefr.value,
        "lesson_goal": blueprint.lesson_goal,
        "objectives": list(blueprint.objectives),
        "estimated_duration_minutes": blueprint.estimated_duration_minutes,
        "steps": [
            {
                "kind": s.kind.value,
                "step_id": s.step_id,
                "skill": s.skill.value if s.skill else None,
                "evidence_eligible": s.evidence_eligible,
                "context_hint": s.context_hint,
                "estimated_minutes": s.estimated_minutes,
                "title": s.title,
            }
            for s in blueprint.steps
        ],
        "practice_spec": {
            "item_count": blueprint.practice_spec.item_count,
            "recommended_contexts": list(blueprint.practice_spec.recommended_contexts),
            "focus_note": blueprint.practice_spec.focus_note,
        },
        "evidence_plan": {
            "eligible_step_ids": list(blueprint.evidence_plan.eligible_step_ids),
            "min_observations": blueprint.evidence_plan.min_observations,
            "observation_types_hint": list(blueprint.evidence_plan.observation_types_hint),
        },
        "completion_criteria": {
            "require_all_steps": blueprint.completion_criteria.require_all_steps,
            "require_exit_check": blueprint.completion_criteria.require_exit_check,
            "min_evidence_eligible_steps_completed": (
                blueprint.completion_criteria.min_evidence_eligible_steps_completed
            ),
            "notes": blueprint.completion_criteria.notes,
        },
        "planner_metadata": {
            "policy_id": blueprint.planner_metadata.policy_id,
            "included_quick_review": blueprint.planner_metadata.included_quick_review,
            "review_grammar_id": blueprint.planner_metadata.review_grammar_id,
            "reinforcement_skills": [s.value for s in blueprint.planner_metadata.reinforcement_skills],
            "duration_budget_minutes": blueprint.planner_metadata.duration_budget_minutes,
            "reasons": list(blueprint.planner_metadata.reasons),
        },
        "fingerprint": blueprint.fingerprint,
        "blueprint_version": blueprint.blueprint_version,
        "planner_version": blueprint.planner_version,
        "catalog_version": blueprint.catalog_version,
        "grammar_schema_version": blueprint.grammar_schema_version,
        "frozen": blueprint.frozen,
        "enabled": blueprint.enabled,
    }


def blueprint_from_dict(raw: dict[str, Any]) -> GrammarLessonBlueprint:
    steps = tuple(
        GrammarLessonStep(
            kind=GrammarLessonStepKind(str(s["kind"])),
            step_id=str(s["step_id"]),
            skill=GrammarReinforcementSkill(s["skill"]) if s.get("skill") else None,
            evidence_eligible=bool(s.get("evidence_eligible", False)),
            context_hint=s.get("context_hint"),
            estimated_minutes=int(s.get("estimated_minutes") or 0),
            title=str(s.get("title") or ""),
        )
        for s in (raw.get("steps") or [])
    )
    ps = dict(raw.get("practice_spec") or {})
    ep = dict(raw.get("evidence_plan") or {})
    cc = dict(raw.get("completion_criteria") or {})
    pm = dict(raw.get("planner_metadata") or {})
    return GrammarLessonBlueprint(
        grammar_id=str(raw["grammar_id"]),
        target_cefr=GrammarCEFRBand(str(raw["target_cefr"])),
        objectives=tuple(raw.get("objectives") or ()),
        steps=steps,
        practice_spec=GrammarPracticeSpec(
            item_count=int(ps.get("item_count") or 4),
            recommended_contexts=tuple(ps.get("recommended_contexts") or ()),
            focus_note=str(ps.get("focus_note") or ""),
        ),
        evidence_plan=GrammarEvidencePlan(
            eligible_step_ids=tuple(ep.get("eligible_step_ids") or ()),
            min_observations=int(ep.get("min_observations") or 1),
            observation_types_hint=tuple(ep.get("observation_types_hint") or ("formative",)),
        ),
        fingerprint=str(raw.get("fingerprint") or ""),
        lesson_id=str(raw.get("lesson_id") or ""),
        lesson_goal=str(raw.get("lesson_goal") or ""),
        estimated_duration_minutes=int(raw.get("estimated_duration_minutes") or 0),
        completion_criteria=GrammarCompletionCriteria(
            require_all_steps=bool(cc.get("require_all_steps", True)),
            require_exit_check=bool(cc.get("require_exit_check", True)),
            min_evidence_eligible_steps_completed=int(
                cc.get("min_evidence_eligible_steps_completed") or 1
            ),
            notes=str(cc.get("notes") or ""),
        ),
        planner_metadata=GrammarPlannerMetadata(
            policy_id=str(pm.get("policy_id") or ""),
            included_quick_review=bool(pm.get("included_quick_review", False)),
            review_grammar_id=pm.get("review_grammar_id"),
            reinforcement_skills=tuple(
                GrammarReinforcementSkill(x) for x in (pm.get("reinforcement_skills") or [])
            ),
            duration_budget_minutes=int(pm.get("duration_budget_minutes") or 0),
            reasons=tuple(pm.get("reasons") or ()),
        ),
        blueprint_version=str(raw.get("blueprint_version") or ""),
        planner_version=str(raw.get("planner_version") or ""),
        catalog_version=str(raw.get("catalog_version") or ""),
        grammar_schema_version=int(raw.get("grammar_schema_version") or 1),
        frozen=bool(raw.get("frozen", True)),
        enabled=bool(raw.get("enabled", True)),
    )
