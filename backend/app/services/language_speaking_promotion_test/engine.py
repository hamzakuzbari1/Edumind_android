"""SPA assessment create orchestration (S18) — no pass/fail, no CEFR write."""

from __future__ import annotations

import hashlib
import uuid
from typing import Any

from app.services.language_speaking_curriculum.skill_catalog import SPEAKING_SKILL_GRAPH
from app.services.language_speaking_generation.promotion_assessment import (
    SpeakingPromotionSlotGenerationConstraint,
    SpeakingPromotionTaskGenerationRequest,
    generate_spa_task_wording,
)
from app.services.language_speaking_promotion_test.builder import build_spa_blueprint
from app.services.language_speaking_promotion_test.policy import (
    EVIDENCE_SOURCE_PROMOTION_ASSESSMENT,
    GENERATION_MAX_RETRIES,
    SPA_TASK_SLOTS,
)
from app.services.language_speaking_promotion_test.specification import (
    SpaSpecificationError,
    build_speaking_promotion_assessment_specification,
)
from app.services.language_speaking_promotion_test.types import (
    SpaCreateFailureCode,
    SpaCreateResult,
    SpaEvaluatorRequirements,
    SpaUnlockAuthority,
    SpeakingPromotionAssessmentTask,
)
from app.services.language_speaking_promotion_test.unlock import reconcile_spa_unlock
from app.services.language_speaking_promotion_test.validation import (
    validate_spa_blueprint,
    validate_spa_tasks_against_specification,
)


def _task_fingerprint(payload: dict[str, Any]) -> str:
    import json

    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


def _s7_task_type(family: str, execution_mode: str) -> str:
    if family == "controlled_response":
        return "controlled_response"
    if family == "picture_or_situation_description":
        return "picture_description"
    if family == "opinion_explanation":
        return "monologue"
    if family == "transfer_new_context":
        return "monologue"
    if family == "spontaneous_unprepared":
        return "monologue"
    return execution_mode


def _skill_labels(skill_ids: tuple[str, ...]) -> tuple[str, ...]:
    labels: list[str] = []
    for sid in skill_ids:
        node = SPEAKING_SKILL_GRAPH.node_by_id(sid)
        labels.append(node.label if node else sid)
    return tuple(labels)


def _mint_tasks_from_wordings(
    *,
    specification,
    wordings,
) -> list[SpeakingPromotionAssessmentTask]:
    by_order = {w.task_order: w for w in wordings}
    tasks: list[SpeakingPromotionAssessmentTask] = []
    for slot in specification.slots:
        w = by_order[slot.task_order]
        family = slot.task_family.value
        proves_prod = slot.spontaneous_production_required
        er = SpaEvaluatorRequirements(
            task_type=_s7_task_type(family, slot.execution_mode.value),
            success_criteria=(
                "Respond in the target language with clear entry-level control.",
                "Stay on topic and complete the prompt.",
            ),
            target_skill_ids=slot.authorized_skill_ids,
            evidence_source=EVIDENCE_SOURCE_PROMOTION_ASSESSMENT,
            proves_spontaneous_production=proves_prod,
            proves_spontaneous_interaction=False,
        )
        task_id = f"spa_task_{slot.task_order}_{uuid.uuid4().hex[:8]}"
        body = {
            "task_order": slot.task_order,
            "task_family": family,
            "target_skill_ids": list(slot.authorized_skill_ids),
            "scenario": w.scenario,
            "student_prompt": w.student_prompt,
            "follow_up_prompts": list(w.follow_up_prompts),
        }
        tasks.append(
            SpeakingPromotionAssessmentTask(
                task_id=task_id,
                task_order=slot.task_order,
                task_family=slot.task_family,
                execution_mode=slot.execution_mode,
                source_cefr=specification.source_cefr,
                target_cefr=specification.target_cefr,
                target_skill_ids=slot.authorized_skill_ids,
                scenario=w.scenario,
                student_prompt=w.student_prompt,
                follow_up_prompts=w.follow_up_prompts,
                context_descriptor=w.context_descriptor,
                spontaneous_production_required=slot.spontaneous_production_required,
                spontaneous_interaction_required=False,
                max_duration_seconds=slot.max_duration_seconds,
                preparation_seconds=slot.preparation_seconds,
                evaluator_requirements=er,
                generation_provenance=dict(w.generation_provenance),
                task_fingerprint=_task_fingerprint(body),
            )
        )
    return tasks


def create_speaking_promotion_assessment(
    authority: SpaUnlockAuthority,
    *,
    expected_official_cefr: str | None = None,
    fresh_readiness_snapshot_fingerprint: str | None = None,
    fresh_source_stage_signal_fingerprint: str | None = None,
    generation_retries: int = GENERATION_MAX_RETRIES,
) -> SpaCreateResult:
    """Reconcile unlock → build spec → generate wording → validate → freeze blueprint.

    Never scores SPA, never writes official_speaking_cefr.
    """
    decision = reconcile_spa_unlock(
        authority,
        expected_official_cefr=expected_official_cefr,
        fresh_readiness_snapshot_fingerprint=fresh_readiness_snapshot_fingerprint,
        fresh_source_stage_signal_fingerprint=fresh_source_stage_signal_fingerprint,
    )
    if not decision.allowed:
        return SpaCreateResult(
            ok=False,
            failure_code=decision.failure_code,
            student_safe_message=decision.student_safe_message
            or "The next-level speaking assessment is temporarily unavailable.",
        )

    source = authority.official_cefr.upper()
    target = (decision.resolved_target_cefr or authority.target_cefr or "").upper()

    try:
        specification = build_speaking_promotion_assessment_specification(
            source_cefr=source,
            target_cefr=target,
        )
    except SpaSpecificationError as exc:
        code_map = {
            "insufficient_production_skills": SpaCreateFailureCode.insufficient_production_skills,
            "coverage_gap_required": SpaCreateFailureCode.coverage_gap_required,
            "unsupported_target": SpaCreateFailureCode.unsupported_target,
            "cefr_mismatch": SpaCreateFailureCode.cefr_mismatch,
        }
        return SpaCreateResult(
            ok=False,
            failure_code=code_map.get(exc.code, SpaCreateFailureCode.assessment_unavailable),
            student_safe_message="The next-level speaking assessment is temporarily unavailable.",
            coverage_gaps=(),
        )

    # Explicit interaction gaps are informational; S18 does not require closing them.
    # Fail closed only when specification builder raised coverage_gap_required.

    slots_req: list[SpeakingPromotionSlotGenerationConstraint] = []
    for slot in specification.slots:
        slots_req.append(
            SpeakingPromotionSlotGenerationConstraint(
                task_order=slot.task_order,
                task_family=slot.task_family.value,
                execution_mode=slot.execution_mode.value,
                authorized_skill_ids=slot.authorized_skill_ids,
                skill_labels=_skill_labels(slot.authorized_skill_ids),
                preparation_seconds=slot.preparation_seconds,
                max_duration_seconds=slot.max_duration_seconds,
                min_follow_ups=slot.min_follow_ups,
                max_follow_ups=slot.max_follow_ups,
                spontaneous_production_required=slot.spontaneous_production_required,
                spontaneous_interaction_required=False,
                forbidden_claims=slot.forbidden_claims,
            )
        )

    last_issues: tuple = ()
    attempts = max(1, generation_retries + 1)
    for attempt_idx in range(attempts):
        gen_req = SpeakingPromotionTaskGenerationRequest(
            specification_fingerprint=specification.specification_fingerprint,
            source_cefr=source,
            target_cefr=target,
            slots=tuple(slots_req),
            request_id=f"spa_gen_{attempt_idx}_{uuid.uuid4().hex[:8]}",
        )
        gen = generate_spa_task_wording(gen_req)
        if not gen.ok:
            last_issues = ((gen.error_code, gen.error_message),)
            continue
        try:
            tasks = _mint_tasks_from_wordings(specification=specification, wordings=gen.wordings)
        except KeyError:
            last_issues = (("incomplete_wordings", "missing task wording"),)
            continue

        task_val = validate_spa_tasks_against_specification(
            specification=specification, tasks=tasks
        )
        if not task_val.ok:
            last_issues = tuple((i.code, i.message) for i in task_val.issues)
            continue

        blueprint = build_spa_blueprint(
            specification=specification,
            tasks=tasks,
            readiness_snapshot_fingerprint=authority.readiness_snapshot_fingerprint,
            unlock_fingerprint=authority.unlock_fingerprint,
            generation_provenance={
                "attempts": attempt_idx + 1,
                "generator": "language_speaking_generation.promotion_assessment",
                "slot_count": len(SPA_TASK_SLOTS),
            },
        )
        bp_val = validate_spa_blueprint(blueprint, specification=specification)
        if not bp_val.ok:
            last_issues = tuple((i.code, i.message) for i in bp_val.issues)
            continue

        return SpaCreateResult(
            ok=True,
            blueprint=blueprint,
            coverage_gaps=specification.coverage_gaps,
        )

    return SpaCreateResult(
        ok=False,
        failure_code=SpaCreateFailureCode.generation_exhausted,
        student_safe_message="The next-level speaking assessment is temporarily unavailable.",
        coverage_gaps=specification.coverage_gaps,
    )
