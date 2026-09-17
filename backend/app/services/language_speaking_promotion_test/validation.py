"""Deterministic SPA blueprint validation + safety checks (S18).

AI must not self-validate as authority.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.services.language_speaking_promotion_test.policy import (
    MAX_DURATION_SECONDS,
    MAX_FOLLOW_UP_PROMPTS,
    MAX_PREPARATION_SECONDS,
    MIN_DURATION_SECONDS,
    MIN_DISTINCT_SKILL_IDS,
    PROHIBITED_SUPPORT_MARKERS,
    SPA_TASK_COUNT,
    SPA_TASK_SLOTS,
    SpaCapabilityKind,
    skill_requires_interactive_evaluation,
    curriculum_skills_for_official_cefr,
)
from app.services.language_speaking_promotion_test.types import (
    SpeakingPromotionAssessmentBlueprint,
    SpeakingPromotionAssessmentSpecification,
    SpeakingPromotionAssessmentTask,
)


@dataclass(frozen=True, slots=True)
class SpaValidationIssue:
    code: str
    message: str


@dataclass(frozen=True, slots=True)
class SpaValidationResult:
    ok: bool
    issues: tuple[SpaValidationIssue, ...] = ()

    @property
    def errors(self) -> tuple[SpaValidationIssue, ...]:
        return self.issues


def _text_blob(task: SpeakingPromotionAssessmentTask) -> str:
    parts = [
        task.scenario,
        task.student_prompt,
        task.context_descriptor,
        " ".join(task.follow_up_prompts),
        json_safe_provenance(task.generation_provenance),
    ]
    return " ".join(parts).lower()


def json_safe_provenance(prov: dict) -> str:
    try:
        import json

        return json.dumps(prov, sort_keys=True).lower()
    except (TypeError, ValueError):
        return str(prov).lower()


def validate_spa_tasks_against_specification(
    *,
    specification: SpeakingPromotionAssessmentSpecification,
    tasks: tuple[SpeakingPromotionAssessmentTask, ...] | list[SpeakingPromotionAssessmentTask],
) -> SpaValidationResult:
    issues: list[SpaValidationIssue] = []
    task_list = list(tasks)

    if len(task_list) != SPA_TASK_COUNT:
        issues.append(
            SpaValidationIssue("task_count", f"expected {SPA_TASK_COUNT} tasks, got {len(task_list)}")
        )

    authorized = set(specification.authorized_skill_ids)
    node_by_id = {
        n.skill_id: n for n in curriculum_skills_for_official_cefr(specification.target_cefr)
    }

    orders = [t.task_order for t in task_list]
    if sorted(orders) != list(range(1, SPA_TASK_COUNT + 1)):
        issues.append(SpaValidationIssue("task_order", f"invalid task_order sequence: {orders}"))

    skill_freq: dict[str, int] = {}
    for task, slot in zip(sorted(task_list, key=lambda t: t.task_order), SPA_TASK_SLOTS):
        if task.task_family != slot.task_family:
            issues.append(
                SpaValidationIssue(
                    "task_family",
                    f"slot {slot.task_order}: expected {slot.task_family}, got {task.task_family}",
                )
            )
        if task.execution_mode != slot.execution_mode:
            issues.append(
                SpaValidationIssue(
                    "execution_mode",
                    f"slot {slot.task_order}: expected {slot.execution_mode}, got {task.execution_mode}",
                )
            )
        if task.source_cefr != specification.source_cefr or task.target_cefr != specification.target_cefr:
            issues.append(SpaValidationIssue("cefr_mismatch", f"task {task.task_order} CEFR mismatch"))

        if not task.scenario.strip() or not task.student_prompt.strip():
            issues.append(SpaValidationIssue("empty_wording", f"task {task.task_order} missing wording"))

        if task.preparation_seconds != slot.preparation_seconds:
            issues.append(
                SpaValidationIssue(
                    "preparation_seconds",
                    f"task {task.task_order}: prep must be {slot.preparation_seconds}",
                )
            )
        if not (MIN_DURATION_SECONDS <= task.max_duration_seconds <= MAX_DURATION_SECONDS):
            issues.append(
                SpaValidationIssue("duration_bounds", f"task {task.task_order}: duration out of bounds")
            )
        if task.max_duration_seconds > slot.max_duration_seconds:
            issues.append(
                SpaValidationIssue("duration_slot", f"task {task.task_order}: exceeds slot max duration")
            )
        if task.preparation_seconds > MAX_PREPARATION_SECONDS:
            issues.append(SpaValidationIssue("prep_bounds", f"task {task.task_order}: prep too long"))

        fu = task.follow_up_prompts
        if len(fu) < slot.min_follow_ups or len(fu) > slot.max_follow_ups:
            issues.append(
                SpaValidationIssue("follow_up_bounds", f"task {task.task_order}: follow-up count invalid")
            )
        if len(fu) > MAX_FOLLOW_UP_PROMPTS:
            issues.append(SpaValidationIssue("follow_up_max", f"task {task.task_order}: too many follow-ups"))

        # Spontaneous production vs interaction — CORRECTION 2
        if task.spontaneous_production_required != slot.spontaneous_production_required:
            issues.append(
                SpaValidationIssue(
                    "spontaneous_production_flag",
                    f"task {task.task_order}: spontaneous_production_required mismatch",
                )
            )
        if task.spontaneous_interaction_required:
            issues.append(
                SpaValidationIssue(
                    "spontaneous_interaction_claim",
                    f"task {task.task_order}: recorded SPA must not require spontaneous interaction",
                )
            )
        if task.evaluator_requirements.proves_spontaneous_interaction:
            issues.append(
                SpaValidationIssue(
                    "false_interaction_evidence",
                    f"task {task.task_order}: must not claim proves_spontaneous_interaction",
                )
            )
        if slot.task_family.value == "spontaneous_unprepared":
            if not task.evaluator_requirements.proves_spontaneous_production:
                issues.append(
                    SpaValidationIssue(
                        "spontaneous_production_missing",
                        "spontaneous_unprepared must prove spontaneous production",
                    )
                )
            if SpaCapabilityKind.spontaneous_interaction in slot.proves_capabilities:
                issues.append(
                    SpaValidationIssue(
                        "interaction_in_production_slot",
                        "spontaneous_unprepared slot must not prove spontaneous_interaction",
                    )
                )

        for sid in task.target_skill_ids:
            skill_freq[sid] = skill_freq.get(sid, 0) + 1
            if sid not in authorized:
                issues.append(
                    SpaValidationIssue("unauthorized_skill", f"task {task.task_order}: skill {sid} not authorized")
                )
            node = node_by_id.get(sid)
            if node is not None and skill_requires_interactive_evaluation(node):
                issues.append(
                    SpaValidationIssue(
                        "interaction_skill_on_recorded_task",
                        f"task {task.task_order}: interaction-required skill {sid} cannot be covered by recorded SPA",
                    )
                )

        # Slot-authorized skills must be subset of task skills? Prefer exact intersection.
        slot_auth = set(
            next(s.authorized_skill_ids for s in specification.slots if s.task_order == slot.task_order)
        )
        if not set(task.target_skill_ids).issubset(authorized):
            issues.append(SpaValidationIssue("skill_subset", f"task {task.task_order}: skills outside authorized set"))
        if not set(task.target_skill_ids).intersection(slot_auth):
            issues.append(
                SpaValidationIssue(
                    "slot_skill_mismatch",
                    f"task {task.task_order}: no overlap with slot authorized skills",
                )
            )

        # Evaluator S7 compatibility fields
        er = task.evaluator_requirements
        if not er.task_type or not er.target_skill_ids:
            issues.append(SpaValidationIssue("evaluator_compat", f"task {task.task_order}: incomplete evaluator_requirements"))
        if er.evidence_source != "promotion_assessment":
            issues.append(
                SpaValidationIssue("evidence_source", f"task {task.task_order}: evidence_source must be promotion_assessment")
            )

        blob = _text_blob(task)
        for marker in PROHIBITED_SUPPORT_MARKERS:
            if marker in blob:
                issues.append(
                    SpaValidationIssue(
                        "prohibited_content",
                        f"task {task.task_order}: prohibited marker '{marker}'",
                    )
                )

        # Reject AI-created pass thresholds / promotion outcomes as decision values.
        prov_obj = task.generation_provenance if isinstance(task.generation_provenance, dict) else {}
        for bad_key in ("pass_threshold", "overall_passed", "official_speaking_cefr", "spa_score", "promotion_passed"):
            if bad_key in prov_obj:
                issues.append(
                    SpaValidationIssue("ai_threshold", f"task {task.task_order}: forbidden decision '{bad_key}'")
                )
        blob_extra = _text_blob(task)
        for phrase in ("pass threshold:", "overall_passed=", "mark as b1", "promote to b1"):
            if phrase in blob_extra:
                issues.append(
                    SpaValidationIssue("ai_threshold", f"task {task.task_order}: forbidden threshold/promotion language")
                )

    distinct = set(skill_freq)
    if len(distinct) < MIN_DISTINCT_SKILL_IDS:
        issues.append(
            SpaValidationIssue(
                "coverage_diversity",
                f"need ≥{MIN_DISTINCT_SKILL_IDS} distinct skills, got {len(distinct)}",
            )
        )

    # Never claim interaction coverage gaps are closed by monologue tasks
    for gap in specification.coverage_gaps:
        if gap.gap_kind == "interaction_required":
            for task in task_list:
                if gap.skill_id in task.target_skill_ids:
                    issues.append(
                        SpaValidationIssue(
                            "gap_falsely_covered",
                            f"interaction gap skill {gap.skill_id} must not appear on recorded tasks",
                        )
                    )
                if task.evaluator_requirements.proves_spontaneous_interaction:
                    issues.append(
                        SpaValidationIssue(
                            "gap_interaction_claim",
                            "cannot claim spontaneous interaction while interaction gaps exist",
                        )
                    )

    return SpaValidationResult(ok=len(issues) == 0, issues=tuple(issues))


def validate_spa_blueprint(
    blueprint: SpeakingPromotionAssessmentBlueprint,
    *,
    specification: SpeakingPromotionAssessmentSpecification,
) -> SpaValidationResult:
    base = validate_spa_tasks_against_specification(
        specification=specification, tasks=blueprint.tasks
    )
    issues = list(base.issues)
    if blueprint.specification_fingerprint != specification.specification_fingerprint:
        issues.append(SpaValidationIssue("spec_fingerprint", "blueprint specification_fingerprint mismatch"))
    if not blueprint.frozen:
        issues.append(SpaValidationIssue("not_frozen", "validated blueprint must be frozen"))
    if blueprint.source_cefr != specification.source_cefr or blueprint.target_cefr != specification.target_cefr:
        issues.append(SpaValidationIssue("blueprint_cefr", "blueprint CEFR mismatch vs specification"))
    if any(t.evaluator_requirements.proves_spontaneous_interaction for t in blueprint.tasks):
        issues.append(
            SpaValidationIssue(
                "blueprint_interaction_claim",
                "blueprint must not claim spontaneous interaction evidence",
            )
        )
    return SpaValidationResult(ok=len(issues) == 0, issues=tuple(issues))
