"""Speaking SPA blueprint / session contracts (S18).

S18 owns specification, constrained wording freeze, and bounded persistence.
Does NOT score SPA, write official_speaking_cefr, or apply S8 mastery.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from app.services.language_speaking_promotion_test.policy import (
    EVIDENCE_SOURCE_PROMOTION_ASSESSMENT,
    SPA_POLICY_VERSION,
    SPA_SCHEMA_VERSION,
    SpaCapabilityKind,
    SpaExecutionMode,
    SpaSkillEvaluatorCompatibility,
    SpaTaskFamily,
)

LANGUAGE_SPEAKING_PROMOTION_TEST_VERSION = "18.0.0"


class SpaBlueprintStatus(StrEnum):
    available = "available"
    not_started = "not_started"
    # S19 transitions — listed for identity contracts only; S18 does not execute them.
    in_progress = "in_progress"
    completed = "completed"
    abandoned = "abandoned"
    unavailable = "unavailable"


class SpaCreateFailureCode(StrEnum):
    unlock_not_granted = "unlock_not_granted"
    stale_fingerprint = "stale_fingerprint"
    cefr_mismatch = "cefr_mismatch"
    unsupported_target = "unsupported_target"
    coverage_gap_required = "coverage_gap_required"
    insufficient_production_skills = "insufficient_production_skills"
    generation_exhausted = "generation_exhausted"
    validation_failed = "validation_failed"
    assessment_unavailable = "assessment_unavailable"


@dataclass(frozen=True, slots=True)
class SpaSkillCoverageItem:
    skill_id: str
    skill_type: str
    label: str
    evaluator_compatibility: SpaSkillEvaluatorCompatibility
    selected_for_tasks: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "skill_id": self.skill_id,
            "skill_type": self.skill_type,
            "label": self.label,
            "evaluator_compatibility": self.evaluator_compatibility.value,
            "selected_for_tasks": self.selected_for_tasks,
        }

    @staticmethod
    def from_dict(raw: dict[str, Any]) -> SpaSkillCoverageItem:
        return SpaSkillCoverageItem(
            skill_id=str(raw["skill_id"]),
            skill_type=str(raw.get("skill_type", "")),
            label=str(raw.get("label", "")),
            evaluator_compatibility=SpaSkillEvaluatorCompatibility(
                str(raw["evaluator_compatibility"])
            ),
            selected_for_tasks=bool(raw.get("selected_for_tasks", False)),
        )


@dataclass(frozen=True, slots=True)
class SpaAssessmentCoverageGap:
    """Explicit gap when a target skill cannot be truthfully evaluated by S18 task families."""

    skill_id: str
    skill_type: str
    label: str
    gap_kind: str
    reason: str
    required_capability: SpaCapabilityKind

    def to_dict(self) -> dict[str, Any]:
        return {
            "skill_id": self.skill_id,
            "skill_type": self.skill_type,
            "label": self.label,
            "gap_kind": self.gap_kind,
            "reason": self.reason,
            "required_capability": self.required_capability.value,
        }

    @staticmethod
    def from_dict(raw: dict[str, Any]) -> SpaAssessmentCoverageGap:
        return SpaAssessmentCoverageGap(
            skill_id=str(raw["skill_id"]),
            skill_type=str(raw.get("skill_type", "")),
            label=str(raw.get("label", "")),
            gap_kind=str(raw.get("gap_kind", "")),
            reason=str(raw.get("reason", "")),
            required_capability=SpaCapabilityKind(str(raw["required_capability"])),
        )


@dataclass(frozen=True, slots=True)
class SpaSlotSpecification:
    task_order: int
    task_family: SpaTaskFamily
    execution_mode: SpaExecutionMode
    authorized_skill_ids: tuple[str, ...]
    preparation_seconds: int
    max_duration_seconds: int
    min_follow_ups: int
    max_follow_ups: int
    spontaneous_production_required: bool
    spontaneous_interaction_required: bool
    proves_capabilities: tuple[SpaCapabilityKind, ...]
    forbidden_claims: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_order": self.task_order,
            "task_family": self.task_family.value,
            "execution_mode": self.execution_mode.value,
            "authorized_skill_ids": list(self.authorized_skill_ids),
            "preparation_seconds": self.preparation_seconds,
            "max_duration_seconds": self.max_duration_seconds,
            "min_follow_ups": self.min_follow_ups,
            "max_follow_ups": self.max_follow_ups,
            "spontaneous_production_required": self.spontaneous_production_required,
            "spontaneous_interaction_required": self.spontaneous_interaction_required,
            "proves_capabilities": [c.value for c in self.proves_capabilities],
            "forbidden_claims": list(self.forbidden_claims),
        }


@dataclass(frozen=True, slots=True)
class SpeakingPromotionAssessmentSpecification:
    """Deterministic SPA specification — AI never builds this."""

    schema_version: str
    policy_version: str
    composition_version: str
    curriculum_version: str
    source_cefr: str
    target_cefr: str
    specification_fingerprint: str
    slots: tuple[SpaSlotSpecification, ...]
    authorized_skill_ids: tuple[str, ...]
    coverage_items: tuple[SpaSkillCoverageItem, ...]
    coverage_gaps: tuple[SpaAssessmentCoverageGap, ...]
    requires_interaction_evidence: bool
    interaction_coverage_required: bool
    fail_closed_on_interaction_gap: bool
    evidence_source: str = EVIDENCE_SOURCE_PROMOTION_ASSESSMENT

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "policy_version": self.policy_version,
            "composition_version": self.composition_version,
            "curriculum_version": self.curriculum_version,
            "source_cefr": self.source_cefr,
            "target_cefr": self.target_cefr,
            "specification_fingerprint": self.specification_fingerprint,
            "slots": [s.to_dict() for s in self.slots],
            "authorized_skill_ids": list(self.authorized_skill_ids),
            "coverage_items": [c.to_dict() for c in self.coverage_items],
            "coverage_gaps": [g.to_dict() for g in self.coverage_gaps],
            "requires_interaction_evidence": self.requires_interaction_evidence,
            "interaction_coverage_required": self.interaction_coverage_required,
            "fail_closed_on_interaction_gap": self.fail_closed_on_interaction_gap,
            "evidence_source": self.evidence_source,
        }


@dataclass(frozen=True, slots=True)
class SpaEvaluatorRequirements:
    """S7-compatible evaluator mapping — hidden from student surfaces."""

    task_type: str
    success_criteria: tuple[str, ...]
    target_skill_ids: tuple[str, ...]
    evidence_source: str = EVIDENCE_SOURCE_PROMOTION_ASSESSMENT
    proves_spontaneous_production: bool = False
    proves_spontaneous_interaction: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_type": self.task_type,
            "success_criteria": list(self.success_criteria),
            "target_skill_ids": list(self.target_skill_ids),
            "evidence_source": self.evidence_source,
            "proves_spontaneous_production": self.proves_spontaneous_production,
            "proves_spontaneous_interaction": self.proves_spontaneous_interaction,
        }

    @staticmethod
    def from_dict(raw: dict[str, Any]) -> SpaEvaluatorRequirements:
        return SpaEvaluatorRequirements(
            task_type=str(raw.get("task_type", "")),
            success_criteria=tuple(str(x) for x in (raw.get("success_criteria") or ())),
            target_skill_ids=tuple(str(x) for x in (raw.get("target_skill_ids") or ())),
            evidence_source=str(raw.get("evidence_source") or EVIDENCE_SOURCE_PROMOTION_ASSESSMENT),
            proves_spontaneous_production=bool(raw.get("proves_spontaneous_production", False)),
            proves_spontaneous_interaction=bool(raw.get("proves_spontaneous_interaction", False)),
        )


@dataclass(frozen=True, slots=True)
class SpeakingPromotionAssessmentTask:
    task_id: str
    task_order: int
    task_family: SpaTaskFamily
    execution_mode: SpaExecutionMode
    source_cefr: str
    target_cefr: str
    target_skill_ids: tuple[str, ...]
    scenario: str
    student_prompt: str
    follow_up_prompts: tuple[str, ...]
    context_descriptor: str
    spontaneous_production_required: bool
    spontaneous_interaction_required: bool
    max_duration_seconds: int
    preparation_seconds: int
    evaluator_requirements: SpaEvaluatorRequirements
    generation_provenance: dict[str, Any]
    task_fingerprint: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "task_order": self.task_order,
            "task_family": self.task_family.value,
            "execution_mode": self.execution_mode.value,
            "source_cefr": self.source_cefr,
            "target_cefr": self.target_cefr,
            "target_skill_ids": list(self.target_skill_ids),
            "scenario": self.scenario,
            "student_prompt": self.student_prompt,
            "follow_up_prompts": list(self.follow_up_prompts),
            "context_descriptor": self.context_descriptor,
            "spontaneous_production_required": self.spontaneous_production_required,
            "spontaneous_interaction_required": self.spontaneous_interaction_required,
            "max_duration_seconds": self.max_duration_seconds,
            "preparation_seconds": self.preparation_seconds,
            "evaluator_requirements": self.evaluator_requirements.to_dict(),
            "generation_provenance": dict(self.generation_provenance),
            "task_fingerprint": self.task_fingerprint,
        }

    def to_student_safe_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "task_order": self.task_order,
            "task_family": self.task_family.value,
            "execution_mode": self.execution_mode.value,
            "scenario": self.scenario,
            "student_prompt": self.student_prompt,
            "follow_up_prompts": list(self.follow_up_prompts),
            "context_descriptor": self.context_descriptor,
            "max_duration_seconds": self.max_duration_seconds,
            "preparation_seconds": self.preparation_seconds,
            "spontaneous_production_required": self.spontaneous_production_required,
            # Never claim spontaneous interaction from recorded monologue.
            "spontaneous_interaction_required": False,
        }

    @staticmethod
    def from_dict(raw: dict[str, Any]) -> SpeakingPromotionAssessmentTask:
        eval_raw = raw.get("evaluator_requirements") or {}
        return SpeakingPromotionAssessmentTask(
            task_id=str(raw["task_id"]),
            task_order=int(raw["task_order"]),
            task_family=SpaTaskFamily(str(raw["task_family"])),
            execution_mode=SpaExecutionMode(str(raw["execution_mode"])),
            source_cefr=str(raw["source_cefr"]),
            target_cefr=str(raw["target_cefr"]),
            target_skill_ids=tuple(str(x) for x in (raw.get("target_skill_ids") or ())),
            scenario=str(raw.get("scenario", "")),
            student_prompt=str(raw.get("student_prompt", "")),
            follow_up_prompts=tuple(str(x) for x in (raw.get("follow_up_prompts") or ())),
            context_descriptor=str(raw.get("context_descriptor", "")),
            spontaneous_production_required=bool(raw.get("spontaneous_production_required", False)),
            spontaneous_interaction_required=bool(raw.get("spontaneous_interaction_required", False)),
            max_duration_seconds=int(raw.get("max_duration_seconds") or 0),
            preparation_seconds=int(raw.get("preparation_seconds") or 0),
            evaluator_requirements=SpaEvaluatorRequirements.from_dict(
                eval_raw if isinstance(eval_raw, dict) else {}
            ),
            generation_provenance=dict(raw.get("generation_provenance") or {}),
            task_fingerprint=str(raw.get("task_fingerprint", "")),
        )


@dataclass(frozen=True, slots=True)
class SpeakingPromotionAssessmentBlueprint:
    blueprint_id: str
    schema_version: str
    policy_version: str
    specification_fingerprint: str
    blueprint_fingerprint: str
    source_cefr: str
    target_cefr: str
    tasks: tuple[SpeakingPromotionAssessmentTask, ...]
    coverage_gaps: tuple[SpaAssessmentCoverageGap, ...]
    generation_provenance: dict[str, Any]
    readiness_snapshot_fingerprint: str
    unlock_fingerprint: str
    frozen: bool
    status: SpaBlueprintStatus
    created_at: str
    evidence_source: str = EVIDENCE_SOURCE_PROMOTION_ASSESSMENT
    # Session identity stubs for S19 — not executed in S18.
    assessment_id: str = ""
    attempt_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "blueprint_id": self.blueprint_id,
            "schema_version": self.schema_version,
            "policy_version": self.policy_version,
            "specification_fingerprint": self.specification_fingerprint,
            "blueprint_fingerprint": self.blueprint_fingerprint,
            "source_cefr": self.source_cefr,
            "target_cefr": self.target_cefr,
            "tasks": [t.to_dict() for t in self.tasks],
            "coverage_gaps": [g.to_dict() for g in self.coverage_gaps],
            "generation_provenance": dict(self.generation_provenance),
            "readiness_snapshot_fingerprint": self.readiness_snapshot_fingerprint,
            "unlock_fingerprint": self.unlock_fingerprint,
            "frozen": self.frozen,
            "status": self.status.value,
            "created_at": self.created_at,
            "evidence_source": self.evidence_source,
            "assessment_id": self.assessment_id or self.blueprint_id,
            "attempt_id": self.attempt_id,
        }

    def to_student_safe_dict(self, *, include_tasks: bool = True) -> dict[str, Any]:
        out: dict[str, Any] = {
            "assessment_id": self.assessment_id or self.blueprint_id,
            "blueprint_id": self.blueprint_id,
            "status": self.status.value,
            "source_cefr": self.source_cefr,
            "target_cefr": self.target_cefr,
            "task_count": len(self.tasks),
            "frozen": self.frozen,
            "created_at": self.created_at,
            # Student-safe gap notice: interaction is not claimed; no thresholds.
            "has_interaction_coverage_gaps": any(
                g.required_capability == SpaCapabilityKind.spontaneous_interaction
                or g.gap_kind == "interaction_required"
                for g in self.coverage_gaps
            ),
        }
        if include_tasks:
            out["tasks"] = [t.to_student_safe_dict() for t in self.tasks]
        return out

    @staticmethod
    def from_dict(raw: dict[str, Any]) -> SpeakingPromotionAssessmentBlueprint:
        tasks = tuple(
            SpeakingPromotionAssessmentTask.from_dict(t)
            for t in (raw.get("tasks") or [])
            if isinstance(t, dict)
        )
        gaps = tuple(
            SpaAssessmentCoverageGap.from_dict(g)
            for g in (raw.get("coverage_gaps") or [])
            if isinstance(g, dict)
        )
        return SpeakingPromotionAssessmentBlueprint(
            blueprint_id=str(raw["blueprint_id"]),
            schema_version=str(raw.get("schema_version") or SPA_SCHEMA_VERSION),
            policy_version=str(raw.get("policy_version") or SPA_POLICY_VERSION),
            specification_fingerprint=str(raw.get("specification_fingerprint", "")),
            blueprint_fingerprint=str(raw.get("blueprint_fingerprint", "")),
            source_cefr=str(raw["source_cefr"]),
            target_cefr=str(raw["target_cefr"]),
            tasks=tasks,
            coverage_gaps=gaps,
            generation_provenance=dict(raw.get("generation_provenance") or {}),
            readiness_snapshot_fingerprint=str(raw.get("readiness_snapshot_fingerprint", "")),
            unlock_fingerprint=str(raw.get("unlock_fingerprint", "")),
            frozen=bool(raw.get("frozen", True)),
            status=SpaBlueprintStatus(str(raw.get("status") or SpaBlueprintStatus.not_started.value)),
            created_at=str(raw.get("created_at", "")),
            evidence_source=str(raw.get("evidence_source") or EVIDENCE_SOURCE_PROMOTION_ASSESSMENT),
            assessment_id=str(raw.get("assessment_id") or raw.get("blueprint_id") or ""),
            attempt_id=(str(raw["attempt_id"]) if raw.get("attempt_id") else None),
        )


@dataclass(frozen=True, slots=True)
class SpaUnlockAuthority:
    """Reconciled unlock snapshot passed into promotion_test (never trust stale flag alone)."""

    spa_unlocked: bool
    official_cefr: str
    target_cefr: str | None
    readiness_snapshot_fingerprint: str
    source_stage_signal_fingerprint: str
    unlock_fingerprint: str
    hard_blockers_empty: bool
    stability_requirements_passed: bool
    current_stage_advanced: bool


@dataclass(frozen=True, slots=True)
class SpaCreateResult:
    ok: bool
    blueprint: SpeakingPromotionAssessmentBlueprint | None = None
    failure_code: SpaCreateFailureCode | None = None
    student_safe_message: str = ""
    coverage_gaps: tuple[SpaAssessmentCoverageGap, ...] = ()


# Legacy S0 placeholder kept for import compatibility; no longer a stub authority.
@dataclass(frozen=True, slots=True)
class SpeakingPromotionTestBundle:
    """Deprecated alias surface — prefer SpeakingPromotionAssessmentBlueprint."""

    stub: bool = False
    version: str = LANGUAGE_SPEAKING_PROMOTION_TEST_VERSION
    blueprint: SpeakingPromotionAssessmentBlueprint | None = None
