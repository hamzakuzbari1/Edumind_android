"""Explainability facts — structured reasoning without student-facing language (Phase 2.1)."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.services.language_learning_facts.assembler import (
    assemble_challenge_facts,
    assemble_curriculum_facts,
    assemble_goal_facts,
    assemble_level_context_facts,
    assemble_situation_facts,
    top_curriculum_factors,
)
from app.services.language_learning_facts.types import (
    ChallengeFacts,
    GoalFacts,
    LevelContextFacts,
    ObjectiveConfidenceFact,
    PromotionContextFacts,
    SelectionRationaleFacts,
    SituationFacts,
)
from app.services.language_listening_challenge.telemetry import compute_challenge_telemetry
from app.services.language_listening_challenge.types import ChallengeState
from app.services.language_listening_confidence.telemetry import compute_confidence_telemetry
from app.services.language_listening_confidence.types import ConfidenceState
from app.services.language_listening_explainability.signals import extract_signals
from app.services.language_listening_explainability.types import ExplainabilitySignals


@dataclass(frozen=True, slots=True)
class ExplainabilityFacts:
    """Language-neutral educational facts for narrative synthesis."""

    selection_rationale: SelectionRationaleFacts
    situation: SituationFacts
    curriculum_objectives: tuple[str, ...]
    skill_focus: tuple[str, ...]
    review_objectives: tuple[str, ...]
    question_types: tuple[str, ...]
    weak_objectives: tuple[ObjectiveConfidenceFact, ...]
    level_context: LevelContextFacts
    challenge: ChallengeFacts
    goal: GoalFacts
    review_active: bool
    knowledge_node: str
    next_planning_signal_codes: tuple[str, ...] = ()
    promotion_context: PromotionContextFacts | None = None
    weak_skills: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, object]:
        from app.services.language_learning_facts.types import facts_to_dict

        return facts_to_dict(self)


def _weak_objectives_from_snapshot(signals: ExplainabilitySignals) -> tuple[ObjectiveConfidenceFact, ...]:
    conf = signals.confidence_lesson
    snapshot = conf.get("objective_confidence_snapshot")
    if not isinstance(snapshot, dict):
        return ()
    ranked: list[tuple[float, ObjectiveConfidenceFact]] = []
    for oid, blob in snapshot.items():
        if not isinstance(blob, dict):
            continue
        ranked.append(
            (
                float(blob.get("confidence", 1.0)),
                ObjectiveConfidenceFact(
                    objective_id=str(oid),
                    confidence=float(blob.get("confidence", 0.0)),
                    coverage=float(blob.get("coverage", 0.0)),
                    mastery=float(blob.get("mastery", 0.0)),
                ),
            )
        )
    ranked.sort(key=lambda x: x[0])
    return tuple(fact for _, fact in ranked[:4])


def _next_planning_signal_codes(
    *,
    review_objectives: tuple[str, ...],
    weak_objectives: tuple[ObjectiveConfidenceFact, ...],
    goal_hints: tuple[str, ...],
    knowledge_node: str,
) -> tuple[str, ...]:
    codes: list[str] = []
    if review_objectives:
        codes.append(f"revisit:{review_objectives[0]}")
    if weak_objectives:
        codes.append(f"build_confidence:{weak_objectives[0].objective_id}")
    for hint in goal_hints[:2]:
        codes.append(f"goal_hint:{hint}")
    if knowledge_node:
        codes.append(f"knowledge_node:{knowledge_node}")
    if not codes:
        codes.append("balanced_coverage")
    return tuple(codes)


def build_explainability_facts(
    signals: ExplainabilitySignals,
    *,
    confidence_state: ConfidenceState | None = None,
    challenge_state: ChallengeState | None = None,
    official_level: str | None = None,
    journey_target_level: str | None = None,
    lesson_level: str | None = None,
    readiness_band: str | None = None,
    estimated_lessons_remaining: int | None = None,
    can_start_promotion_test: bool = False,
    readiness_score: float | None = None,
) -> ExplainabilityFacts:
    """Build structured explainability facts — no student-facing sentences."""
    curriculum = assemble_curriculum_facts(signals)
    goal = assemble_goal_facts(signals)
    challenge = assemble_challenge_facts(signals)
    situation = assemble_situation_facts(signals)
    level = assemble_level_context_facts(
        signals,
        official_level=official_level,
        journey_target_level=journey_target_level,
        lesson_level=lesson_level,
    )

    weak_from_snapshot = _weak_objectives_from_snapshot(signals)
    weak_objectives = weak_from_snapshot
    if confidence_state:
        conf_telemetry = compute_confidence_telemetry(confidence_state)
        if conf_telemetry.under_confident:
            existing = {w.objective_id for w in weak_objectives}
            extra: list[ObjectiveConfidenceFact] = list(weak_objectives)
            for oid in conf_telemetry.under_confident[:2]:
                if oid in existing:
                    continue
                rec = confidence_state.objectives.get(oid)
                if rec:
                    extra.append(
                        ObjectiveConfidenceFact(
                            objective_id=oid,
                            confidence=rec.confidence,
                            coverage=rec.coverage_score,
                            mastery=rec.mastery_score,
                        )
                    )
            weak_objectives = tuple(extra[:4])

    review_active = bool(curriculum.review_objectives) or curriculum.lesson_intent == "review"
    factors = top_curriculum_factors(curriculum)

    primary_engine = "curriculum"
    if goal.lesson_goal_id and goal.goal_alignment_score >= curriculum.recommendation_score * 0.15:
        primary_engine = "goal"
    if challenge.challenge_level not in ("normal", ""):
        primary_engine = "challenge"

    selection = SelectionRationaleFacts(
        primary_engine=primary_engine,
        lesson_intent=curriculum.lesson_intent,
        curriculum_stage=curriculum.curriculum_stage,
        recommendation_score=curriculum.recommendation_score,
        top_score_factors=factors,
        selection_reason_code=goal.selection_reason_code or challenge.selection_reason_code,
        goal_id=goal.lesson_goal_id,
        goal_alignment_score=goal.goal_alignment_score,
    )

    promotion: PromotionContextFacts | None = None
    if any(v is not None for v in (readiness_band, estimated_lessons_remaining, readiness_score)) or can_start_promotion_test:
        promotion = PromotionContextFacts(
            readiness_band=readiness_band,
            estimated_lessons_remaining=estimated_lessons_remaining,
            can_start_promotion_test=can_start_promotion_test,
            readiness_score=readiness_score,
        )
    elif challenge_state:
        ch_telemetry = compute_challenge_telemetry(challenge_state)
        promotion = PromotionContextFacts(
            readiness_band=None,
            estimated_lessons_remaining=None,
            can_start_promotion_test=False,
            readiness_score=ch_telemetry.challenge_score,
        )

    return ExplainabilityFacts(
        selection_rationale=selection,
        situation=situation,
        curriculum_objectives=curriculum.objectives,
        skill_focus=curriculum.skill_focus,
        review_objectives=curriculum.review_objectives,
        question_types=signals.question_types,
        weak_objectives=weak_objectives,
        level_context=level,
        challenge=challenge,
        goal=goal,
        review_active=review_active,
        knowledge_node=curriculum.knowledge_node,
        next_planning_signal_codes=_next_planning_signal_codes(
            review_objectives=curriculum.review_objectives,
            weak_objectives=weak_objectives,
            goal_hints=goal.goal_objective_hints,
            knowledge_node=curriculum.knowledge_node,
        ),
        promotion_context=promotion,
        weak_skills=signals.weak_skills,
    )


def build_explainability_facts_from_body(
    body_json: dict | None,
    *,
    confidence_state: ConfidenceState | None = None,
    challenge_state: ChallengeState | None = None,
    cefr_level: str = "",
    weak_skills: list[str] | None = None,
    official_level: str | None = None,
    journey_target_level: str | None = None,
    lesson_level: str | None = None,
) -> ExplainabilityFacts:
    signals = extract_signals(body_json, cefr_level=cefr_level, weak_skills=weak_skills)
    return build_explainability_facts(
        signals,
        confidence_state=confidence_state,
        challenge_state=challenge_state,
        official_level=official_level,
        journey_target_level=journey_target_level,
        lesson_level=lesson_level,
    )
