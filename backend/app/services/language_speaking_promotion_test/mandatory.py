"""Declare mandatory competency requirements from a frozen SPA blueprint (S19).

Declares *what* must be proven — does not invent pass thresholds.
Exact numeric product policy remains deferred; this module only binds
requirement identity to frozen task families / production / skill groups.
"""

from __future__ import annotations

from app.services.language_speaking_promotion_test.execution_types import (
    SpaMandatoryCompetencyKind,
    SpaMandatoryCompetencyRequirement,
)
from app.services.language_speaking_promotion_test.types import SpeakingPromotionAssessmentBlueprint


def declare_mandatory_competency_requirements(
    blueprint: SpeakingPromotionAssessmentBlueprint,
) -> tuple[SpaMandatoryCompetencyRequirement, ...]:
    """Build mandatory competency declarations from the frozen blueprint.

    Architecture only: every distinct task family present is a required family;
    spontaneous-production tasks form a production competency; skill ids on
    production-proving tasks form skill-group requirements.
    """
    reqs: list[SpaMandatoryCompetencyRequirement] = []

    family_to_tasks: dict[str, list[str]] = {}
    for task in blueprint.tasks:
        family = task.task_family.value
        family_to_tasks.setdefault(family, []).append(task.task_id)

    for family, task_ids in sorted(family_to_tasks.items()):
        reqs.append(
            SpaMandatoryCompetencyRequirement(
                requirement_id=f"family:{family}",
                kind=SpaMandatoryCompetencyKind.required_task_family,
                label=f"Required task family: {family}",
                target_ids=(family,),
                task_ids=tuple(task_ids),
            )
        )

    production_tasks = tuple(
        t.task_id for t in blueprint.tasks if t.spontaneous_production_required
    )
    if production_tasks:
        reqs.append(
            SpaMandatoryCompetencyRequirement(
                requirement_id="production:spontaneous",
                kind=SpaMandatoryCompetencyKind.required_production_competency,
                label="Required spontaneous production competency",
                target_ids=("spontaneous_production",),
                task_ids=production_tasks,
            )
        )

    skill_to_tasks: dict[str, list[str]] = {}
    for task in blueprint.tasks:
        if not task.evaluator_requirements.proves_spontaneous_production:
            # Skill groups from production-proving tasks only (honest SPA coverage).
            if not task.spontaneous_production_required:
                continue
        for sid in task.target_skill_ids:
            skill_to_tasks.setdefault(sid, []).append(task.task_id)
    # Also include skills from any task that selects them when no production-only set.
    if not skill_to_tasks:
        for task in blueprint.tasks:
            for sid in task.target_skill_ids:
                skill_to_tasks.setdefault(sid, []).append(task.task_id)

    # Cap skill-group mandatory set to skills that appear on ≥1 task (deterministic).
    for sid, task_ids in sorted(skill_to_tasks.items()):
        reqs.append(
            SpaMandatoryCompetencyRequirement(
                requirement_id=f"skill:{sid}",
                kind=SpaMandatoryCompetencyKind.required_skill_group,
                label=f"Required skill group: {sid}",
                target_ids=(sid,),
                task_ids=tuple(dict.fromkeys(task_ids)),
            )
        )

    return tuple(reqs)
