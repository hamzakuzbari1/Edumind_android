"""S19 SPA execution identity, session, attempt, result, and pass-gate contracts.

Identity hierarchy (distinct — never collapse):
  blueprint_id  → frozen assessment definition (S18)
  assessment_id → logical SPA instance (lifecycle, result, bridge, resume)
  attempt_id    → one execution run (minted on start; never reused)

PASS requires BOTH:
  1) aggregate assessment performance gate
  2) mandatory competency requirements gate
A mandatory competency failure blocks PASS even when aggregate would pass.
Thresholds remain product-policy (not invented here); gates are architectural.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from app.services.language_speaking_promotion_test.policy import (
    EVIDENCE_SOURCE_PROMOTION_ASSESSMENT,
)
from app.services.language_speaking_promotion_test.types import (
    SpaBlueprintStatus,
    SpeakingPromotionAssessmentBlueprint,
)

LANGUAGE_SPEAKING_PROMOTION_EXECUTION_VERSION = "19.0.0"
MAX_ATTEMPT_HISTORY = 5


class SpaAssessmentOutcome(StrEnum):
    """Terminal assessment outcomes produced by S19 (never official CEFR)."""

    PASS = "PASS"
    FAIL = "FAIL"
    INCOMPLETE = "INCOMPLETE"
    ABANDONED = "ABANDONED"
    TIMEOUT = "TIMEOUT"


class SpaTaskAttemptStatus(StrEnum):
    pending = "pending"
    in_progress = "in_progress"
    submitted = "submitted"
    evaluated = "evaluated"
    skipped = "skipped"
    timed_out = "timed_out"


class SpaMandatoryCompetencyKind(StrEnum):
    """Kinds of mandatory competencies the architecture can enforce."""

    required_task_family = "required_task_family"
    required_production_competency = "required_production_competency"
    required_skill_group = "required_skill_group"


class SpaExecutionFailureCode(StrEnum):
    assessment_not_found = "assessment_not_found"
    assessment_not_startable = "assessment_not_startable"
    assessment_not_in_progress = "assessment_not_in_progress"
    attempt_mismatch = "attempt_mismatch"
    task_not_current = "task_not_current"
    task_already_terminal = "task_already_terminal"
    invalid_execution_mode = "invalid_execution_mode"
    evaluation_failed = "evaluation_failed"
    retry_not_eligible = "retry_not_eligible"
    blueprint_not_frozen = "blueprint_not_frozen"
    validation_failed = "validation_failed"


@dataclass(frozen=True, slots=True)
class SpaTaskScoreSummary:
    """Student-safe / aggregate-facing per-task score facts derived from S7."""

    task_id: str
    task_order: int
    task_family: str
    evaluation_id: str
    overall_readiness: float
    completion_eligible: bool
    semantic_task_met: bool
    target_skill_ids: tuple[str, ...]
    # Interaction is never authoritative for recorded SPA.
    interaction_claim_allowed: bool = False
    evidence_source: str = EVIDENCE_SOURCE_PROMOTION_ASSESSMENT
    media_object_id: str | None = None
    student_safe_summary: str = ""
    priority_issue: str = ""
    weak_skills: tuple[str, ...] = ()
    strong_skills: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "task_order": self.task_order,
            "task_family": self.task_family,
            "evaluation_id": self.evaluation_id,
            "overall_readiness": round(float(self.overall_readiness), 4),
            "completion_eligible": self.completion_eligible,
            "semantic_task_met": self.semantic_task_met,
            "target_skill_ids": list(self.target_skill_ids),
            "interaction_claim_allowed": self.interaction_claim_allowed,
            "evidence_source": self.evidence_source,
            "media_object_id": self.media_object_id,
            "student_safe_summary": self.student_safe_summary,
            "priority_issue": self.priority_issue,
            "weak_skills": list(self.weak_skills),
            "strong_skills": list(self.strong_skills),
        }

    @staticmethod
    def from_dict(raw: dict[str, Any]) -> SpaTaskScoreSummary:
        return SpaTaskScoreSummary(
            task_id=str(raw["task_id"]),
            task_order=int(raw.get("task_order") or 0),
            task_family=str(raw.get("task_family", "")),
            evaluation_id=str(raw.get("evaluation_id", "")),
            overall_readiness=float(raw.get("overall_readiness") or 0.0),
            completion_eligible=bool(raw.get("completion_eligible", False)),
            semantic_task_met=bool(raw.get("semantic_task_met", False)),
            target_skill_ids=tuple(str(x) for x in (raw.get("target_skill_ids") or ())),
            interaction_claim_allowed=bool(raw.get("interaction_claim_allowed", False)),
            evidence_source=str(raw.get("evidence_source") or EVIDENCE_SOURCE_PROMOTION_ASSESSMENT),
            media_object_id=(str(raw["media_object_id"]) if raw.get("media_object_id") else None),
            student_safe_summary=str(raw.get("student_safe_summary", "")),
            priority_issue=str(raw.get("priority_issue", "")),
            weak_skills=tuple(str(x) for x in (raw.get("weak_skills") or ())),
            strong_skills=tuple(str(x) for x in (raw.get("strong_skills") or ())),
        )


@dataclass(frozen=True, slots=True)
class SpaTaskAttempt:
    task_attempt_id: str
    task_id: str
    task_order: int
    attempt_id: str
    status: SpaTaskAttemptStatus
    score: SpaTaskScoreSummary | None = None
    started_at: str | None = None
    completed_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_attempt_id": self.task_attempt_id,
            "task_id": self.task_id,
            "task_order": self.task_order,
            "attempt_id": self.attempt_id,
            "status": self.status.value,
            "score": self.score.to_dict() if self.score else None,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }

    @staticmethod
    def from_dict(raw: dict[str, Any]) -> SpaTaskAttempt:
        score_raw = raw.get("score")
        return SpaTaskAttempt(
            task_attempt_id=str(raw["task_attempt_id"]),
            task_id=str(raw["task_id"]),
            task_order=int(raw.get("task_order") or 0),
            attempt_id=str(raw["attempt_id"]),
            status=SpaTaskAttemptStatus(str(raw.get("status") or SpaTaskAttemptStatus.pending.value)),
            score=SpaTaskScoreSummary.from_dict(score_raw) if isinstance(score_raw, dict) else None,
            started_at=(str(raw["started_at"]) if raw.get("started_at") else None),
            completed_at=(str(raw["completed_at"]) if raw.get("completed_at") else None),
        )


@dataclass(frozen=True, slots=True)
class SpaAssessmentSession:
    """Dedicated SPA runtime session — never reuse SpeakingLearningSession."""

    session_id: str
    assessment_id: str
    attempt_id: str
    blueprint_id: str
    current_task_index: int  # 0-based cursor into frozen task order
    started_at: str
    updated_at: str
    expires_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "assessment_id": self.assessment_id,
            "attempt_id": self.attempt_id,
            "blueprint_id": self.blueprint_id,
            "current_task_index": self.current_task_index,
            "started_at": self.started_at,
            "updated_at": self.updated_at,
            "expires_at": self.expires_at,
        }

    @staticmethod
    def from_dict(raw: dict[str, Any]) -> SpaAssessmentSession:
        return SpaAssessmentSession(
            session_id=str(raw["session_id"]),
            assessment_id=str(raw["assessment_id"]),
            attempt_id=str(raw["attempt_id"]),
            blueprint_id=str(raw["blueprint_id"]),
            current_task_index=int(raw.get("current_task_index") or 0),
            started_at=str(raw.get("started_at", "")),
            updated_at=str(raw.get("updated_at", "")),
            expires_at=(str(raw["expires_at"]) if raw.get("expires_at") else None),
        )


@dataclass(frozen=True, slots=True)
class SpaAssessmentAttempt:
    attempt_id: str
    assessment_id: str
    blueprint_id: str
    started_at: str
    updated_at: str
    status: SpaBlueprintStatus
    task_attempts: tuple[SpaTaskAttempt, ...] = ()
    outcome: SpaAssessmentOutcome | None = None
    completed_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "attempt_id": self.attempt_id,
            "assessment_id": self.assessment_id,
            "blueprint_id": self.blueprint_id,
            "started_at": self.started_at,
            "updated_at": self.updated_at,
            "status": self.status.value,
            "task_attempts": [t.to_dict() for t in self.task_attempts],
            "outcome": self.outcome.value if self.outcome else None,
            "completed_at": self.completed_at,
        }

    @staticmethod
    def from_dict(raw: dict[str, Any]) -> SpaAssessmentAttempt:
        tasks = tuple(
            SpaTaskAttempt.from_dict(t)
            for t in (raw.get("task_attempts") or [])
            if isinstance(t, dict)
        )
        outcome_raw = raw.get("outcome")
        return SpaAssessmentAttempt(
            attempt_id=str(raw["attempt_id"]),
            assessment_id=str(raw["assessment_id"]),
            blueprint_id=str(raw["blueprint_id"]),
            started_at=str(raw.get("started_at", "")),
            updated_at=str(raw.get("updated_at", "")),
            status=SpaBlueprintStatus(str(raw.get("status") or SpaBlueprintStatus.in_progress.value)),
            task_attempts=tasks,
            outcome=SpaAssessmentOutcome(str(outcome_raw)) if outcome_raw else None,
            completed_at=(str(raw["completed_at"]) if raw.get("completed_at") else None),
        )


@dataclass(frozen=True, slots=True)
class SpaMandatoryCompetencyRequirement:
    """Declarative mandatory competency — no numeric thresholds invented here."""

    requirement_id: str
    kind: SpaMandatoryCompetencyKind
    label: str
    target_ids: tuple[str, ...]
    # Linked task ids that evidence this competency (from frozen blueprint).
    task_ids: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "requirement_id": self.requirement_id,
            "kind": self.kind.value,
            "label": self.label,
            "target_ids": list(self.target_ids),
            "task_ids": list(self.task_ids),
        }

    @staticmethod
    def from_dict(raw: dict[str, Any]) -> SpaMandatoryCompetencyRequirement:
        return SpaMandatoryCompetencyRequirement(
            requirement_id=str(raw["requirement_id"]),
            kind=SpaMandatoryCompetencyKind(str(raw["kind"])),
            label=str(raw.get("label", "")),
            target_ids=tuple(str(x) for x in (raw.get("target_ids") or ())),
            task_ids=tuple(str(x) for x in (raw.get("task_ids") or ())),
        )


@dataclass(frozen=True, slots=True)
class SpaMandatoryCompetencyOutcome:
    requirement_id: str
    kind: SpaMandatoryCompetencyKind
    met: bool
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "requirement_id": self.requirement_id,
            "kind": self.kind.value,
            "met": self.met,
            "reason": self.reason,
        }

    @staticmethod
    def from_dict(raw: dict[str, Any]) -> SpaMandatoryCompetencyOutcome:
        return SpaMandatoryCompetencyOutcome(
            requirement_id=str(raw["requirement_id"]),
            kind=SpaMandatoryCompetencyKind(str(raw["kind"])),
            met=bool(raw.get("met", False)),
            reason=str(raw.get("reason", "")),
        )


@dataclass(frozen=True, slots=True)
class SpaAggregatePerformance:
    """Aggregate performance gate — thresholds belong to future product policy."""

    tasks_scored: int
    tasks_total: int
    mean_overall_readiness: float | None
    tasks_completion_eligible: int
    # Architectural gate flag supplied by outcome engine (not a product threshold constant).
    passed: bool
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "tasks_scored": self.tasks_scored,
            "tasks_total": self.tasks_total,
            "mean_overall_readiness": (
                round(self.mean_overall_readiness, 4) if self.mean_overall_readiness is not None else None
            ),
            "tasks_completion_eligible": self.tasks_completion_eligible,
            "passed": self.passed,
            "reason": self.reason,
        }

    @staticmethod
    def from_dict(raw: dict[str, Any]) -> SpaAggregatePerformance:
        mean = raw.get("mean_overall_readiness")
        return SpaAggregatePerformance(
            tasks_scored=int(raw.get("tasks_scored") or 0),
            tasks_total=int(raw.get("tasks_total") or 0),
            mean_overall_readiness=(float(mean) if mean is not None else None),
            tasks_completion_eligible=int(raw.get("tasks_completion_eligible") or 0),
            passed=bool(raw.get("passed", False)),
            reason=str(raw.get("reason", "")),
        )


@dataclass(frozen=True, slots=True)
class SpaPassGateDecision:
    """PASS iff aggregate.passed AND mandatory_all_met. Never CEFR-authoritative."""

    aggregate: SpaAggregatePerformance
    mandatory_requirements: tuple[SpaMandatoryCompetencyRequirement, ...]
    mandatory_outcomes: tuple[SpaMandatoryCompetencyOutcome, ...]
    mandatory_all_met: bool
    would_pass_on_aggregate_alone: bool
    blocked_by_mandatory_competency: bool
    outcome: SpaAssessmentOutcome

    def to_dict(self) -> dict[str, Any]:
        return {
            "aggregate": self.aggregate.to_dict(),
            "mandatory_requirements": [r.to_dict() for r in self.mandatory_requirements],
            "mandatory_outcomes": [o.to_dict() for o in self.mandatory_outcomes],
            "mandatory_all_met": self.mandatory_all_met,
            "would_pass_on_aggregate_alone": self.would_pass_on_aggregate_alone,
            "blocked_by_mandatory_competency": self.blocked_by_mandatory_competency,
            "outcome": self.outcome.value,
        }

    @staticmethod
    def from_dict(raw: dict[str, Any]) -> SpaPassGateDecision:
        agg_raw = raw.get("aggregate") if isinstance(raw.get("aggregate"), dict) else {}
        return SpaPassGateDecision(
            aggregate=SpaAggregatePerformance.from_dict(agg_raw),
            mandatory_requirements=tuple(
                SpaMandatoryCompetencyRequirement.from_dict(r)
                for r in (raw.get("mandatory_requirements") or [])
                if isinstance(r, dict)
            ),
            mandatory_outcomes=tuple(
                SpaMandatoryCompetencyOutcome.from_dict(o)
                for o in (raw.get("mandatory_outcomes") or [])
                if isinstance(o, dict)
            ),
            mandatory_all_met=bool(raw.get("mandatory_all_met", False)),
            would_pass_on_aggregate_alone=bool(raw.get("would_pass_on_aggregate_alone", False)),
            blocked_by_mandatory_competency=bool(raw.get("blocked_by_mandatory_competency", False)),
            outcome=SpaAssessmentOutcome(str(raw.get("outcome") or SpaAssessmentOutcome.FAIL.value)),
        )


@dataclass(frozen=True, slots=True)
class SpaBridgeRecommendation:
    """Student-safe FAIL bridge projection — not lesson planner authority."""

    focus_skill_ids: tuple[str, ...]
    focus_labels: tuple[str, ...]
    summary: str
    suggested_practice: tuple[str, ...]
    failed_competency_ids: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "focus_skill_ids": list(self.focus_skill_ids),
            "focus_labels": list(self.focus_labels),
            "summary": self.summary,
            "suggested_practice": list(self.suggested_practice),
            "failed_competency_ids": list(self.failed_competency_ids),
        }

    def to_student_safe_dict(self) -> dict[str, Any]:
        return {
            "focus_skill_ids": list(self.focus_skill_ids),
            "focus_labels": list(self.focus_labels),
            "summary": self.summary,
            "suggested_practice": list(self.suggested_practice),
        }

    @staticmethod
    def from_dict(raw: dict[str, Any]) -> SpaBridgeRecommendation:
        return SpaBridgeRecommendation(
            focus_skill_ids=tuple(str(x) for x in (raw.get("focus_skill_ids") or ())),
            focus_labels=tuple(str(x) for x in (raw.get("focus_labels") or ())),
            summary=str(raw.get("summary", "")),
            suggested_practice=tuple(str(x) for x in (raw.get("suggested_practice") or ())),
            failed_competency_ids=tuple(str(x) for x in (raw.get("failed_competency_ids") or ())),
        )


@dataclass(frozen=True, slots=True)
class SpaAssessmentResult:
    assessment_id: str
    attempt_id: str
    blueprint_id: str
    outcome: SpaAssessmentOutcome
    pass_gate: SpaPassGateDecision | None
    bridge_recommendation: SpaBridgeRecommendation | None
    ready_for_official_promotion: bool
    completed_at: str
    evidence_source: str = EVIDENCE_SOURCE_PROMOTION_ASSESSMENT

    def to_dict(self) -> dict[str, Any]:
        return {
            "assessment_id": self.assessment_id,
            "attempt_id": self.attempt_id,
            "blueprint_id": self.blueprint_id,
            "outcome": self.outcome.value,
            "pass_gate": self.pass_gate.to_dict() if self.pass_gate else None,
            "bridge_recommendation": (
                self.bridge_recommendation.to_dict() if self.bridge_recommendation else None
            ),
            "ready_for_official_promotion": self.ready_for_official_promotion,
            "completed_at": self.completed_at,
            "evidence_source": self.evidence_source,
        }

    def to_student_safe_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "assessment_id": self.assessment_id,
            "attempt_id": self.attempt_id,
            "blueprint_id": self.blueprint_id,
            "outcome": self.outcome.value,
            "ready_for_official_promotion": self.ready_for_official_promotion,
            "completed_at": self.completed_at,
        }
        if self.outcome == SpaAssessmentOutcome.PASS:
            out["message"] = "You passed the speaking promotion assessment. Official level update is pending."
        elif self.outcome == SpaAssessmentOutcome.FAIL:
            out["message"] = "Keep practicing — a focused bridge is ready for you."
            if self.bridge_recommendation is not None:
                out["bridge_recommendation"] = self.bridge_recommendation.to_student_safe_dict()
        elif self.outcome == SpaAssessmentOutcome.ABANDONED:
            out["message"] = "This assessment attempt was abandoned."
        elif self.outcome == SpaAssessmentOutcome.TIMEOUT:
            out["message"] = "This assessment attempt timed out."
        else:
            out["message"] = "This assessment could not be completed."
        # Student-safe: expose whether mandatory competencies blocked PASS, not internals.
        if self.pass_gate is not None and self.outcome == SpaAssessmentOutcome.FAIL:
            out["blocked_by_required_competency"] = self.pass_gate.blocked_by_mandatory_competency
        return out

    @staticmethod
    def from_dict(raw: dict[str, Any]) -> SpaAssessmentResult:
        gate_raw = raw.get("pass_gate")
        bridge_raw = raw.get("bridge_recommendation")
        return SpaAssessmentResult(
            assessment_id=str(raw["assessment_id"]),
            attempt_id=str(raw["attempt_id"]),
            blueprint_id=str(raw["blueprint_id"]),
            outcome=SpaAssessmentOutcome(str(raw["outcome"])),
            pass_gate=SpaPassGateDecision.from_dict(gate_raw) if isinstance(gate_raw, dict) else None,
            bridge_recommendation=(
                SpaBridgeRecommendation.from_dict(bridge_raw) if isinstance(bridge_raw, dict) else None
            ),
            ready_for_official_promotion=bool(raw.get("ready_for_official_promotion", False)),
            completed_at=str(raw.get("completed_at", "")),
            evidence_source=str(raw.get("evidence_source") or EVIDENCE_SOURCE_PROMOTION_ASSESSMENT),
        )


@dataclass(frozen=True, slots=True)
class SpeakingPromotionAssessment:
    """Logical SPA assessment — owns lifecycle, session, attempts, result, bridge.

    Distinct from blueprint_id (definition) and attempt_id (execution run).
    """

    assessment_id: str
    blueprint_id: str
    blueprint: SpeakingPromotionAssessmentBlueprint
    status: SpaBlueprintStatus
    created_at: str
    updated_at: str
    session: SpaAssessmentSession | None = None
    current_attempt: SpaAssessmentAttempt | None = None
    attempt_history: tuple[SpaAssessmentAttempt, ...] = ()
    result: SpaAssessmentResult | None = None
    mandatory_requirements: tuple[SpaMandatoryCompetencyRequirement, ...] = ()
    evidence_source: str = EVIDENCE_SOURCE_PROMOTION_ASSESSMENT
    schema_version: str = LANGUAGE_SPEAKING_PROMOTION_EXECUTION_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "assessment_id": self.assessment_id,
            "blueprint_id": self.blueprint_id,
            "blueprint": self.blueprint.to_dict(),
            "status": self.status.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "session": self.session.to_dict() if self.session else None,
            "current_attempt": self.current_attempt.to_dict() if self.current_attempt else None,
            "attempt_history": [a.to_dict() for a in self.attempt_history],
            "result": self.result.to_dict() if self.result else None,
            "mandatory_requirements": [r.to_dict() for r in self.mandatory_requirements],
            "evidence_source": self.evidence_source,
            "schema_version": self.schema_version,
        }

    def to_student_safe_dict(self, *, include_tasks: bool = True) -> dict[str, Any]:
        bp_safe = self.blueprint.to_student_safe_dict(include_tasks=include_tasks)
        out: dict[str, Any] = {
            "assessment_id": self.assessment_id,
            "blueprint_id": self.blueprint_id,
            "status": self.status.value,
            "source_cefr": self.blueprint.source_cefr,
            "target_cefr": self.blueprint.target_cefr,
            "task_count": len(self.blueprint.tasks),
            "frozen": self.blueprint.frozen,
            "created_at": self.created_at,
            "has_interaction_coverage_gaps": bool(bp_safe.get("has_interaction_coverage_gaps")),
            "attempt_id": self.current_attempt.attempt_id if self.current_attempt else None,
            "current_task_index": self.session.current_task_index if self.session else None,
            "ready_for_official_promotion": bool(
                self.result.ready_for_official_promotion if self.result else False
            ),
        }
        if include_tasks:
            out["tasks"] = bp_safe.get("tasks") or []
        if self.result is not None:
            out["result"] = self.result.to_student_safe_dict()
        return out

    @staticmethod
    def from_dict(raw: dict[str, Any]) -> SpeakingPromotionAssessment:
        bp_raw = raw.get("blueprint")
        if not isinstance(bp_raw, dict):
            raise ValueError("SpeakingPromotionAssessment requires embedded blueprint")
        session_raw = raw.get("session")
        attempt_raw = raw.get("current_attempt")
        result_raw = raw.get("result")
        history = tuple(
            SpaAssessmentAttempt.from_dict(a)
            for a in (raw.get("attempt_history") or [])
            if isinstance(a, dict)
        )
        reqs = tuple(
            SpaMandatoryCompetencyRequirement.from_dict(r)
            for r in (raw.get("mandatory_requirements") or [])
            if isinstance(r, dict)
        )
        return SpeakingPromotionAssessment(
            assessment_id=str(raw["assessment_id"]),
            blueprint_id=str(raw.get("blueprint_id") or bp_raw.get("blueprint_id") or ""),
            blueprint=SpeakingPromotionAssessmentBlueprint.from_dict(bp_raw),
            status=SpaBlueprintStatus(str(raw.get("status") or SpaBlueprintStatus.not_started.value)),
            created_at=str(raw.get("created_at", "")),
            updated_at=str(raw.get("updated_at", "")),
            session=SpaAssessmentSession.from_dict(session_raw) if isinstance(session_raw, dict) else None,
            current_attempt=(
                SpaAssessmentAttempt.from_dict(attempt_raw) if isinstance(attempt_raw, dict) else None
            ),
            attempt_history=history,
            result=SpaAssessmentResult.from_dict(result_raw) if isinstance(result_raw, dict) else None,
            mandatory_requirements=reqs,
            evidence_source=str(raw.get("evidence_source") or EVIDENCE_SOURCE_PROMOTION_ASSESSMENT),
            schema_version=str(raw.get("schema_version") or LANGUAGE_SPEAKING_PROMOTION_EXECUTION_VERSION),
        )


@dataclass(frozen=True, slots=True)
class SpaExecutionResult:
    ok: bool
    assessment: SpeakingPromotionAssessment | None = None
    failure_code: SpaExecutionFailureCode | None = None
    student_safe_message: str = ""
    idempotent: bool = False
