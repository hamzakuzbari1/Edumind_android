"""Deterministic speaking target selection (S9 diagnostic)."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone

from app.services.language_speaking.enums import SpeakingGoal
from app.services.language_speaking_curriculum.skill_catalog import SPEAKING_SKILL_GRAPH
from app.services.language_speaking_curriculum.types import SpeakingSkillGraph, SpeakingSkillNode
from app.services.language_speaking_diagnostic.prerequisites import eligible_skills, prerequisite_state
from app.services.language_speaking_diagnostic.types import (
    LANGUAGE_SPEAKING_DIAGNOSTIC_VERSION,
    DiagnosticRecommendation,
    TargetSelectionReason,
)
from app.services.language_speaking_knowledge_model.summaries import at_risk_skill_ids, developing_skill_ids
from app.services.language_speaking_knowledge_model.types import StudentSpeakingKnowledgeModel

WEAK_MASTERY_THRESHOLD = 0.45
RETENTION_RISK_THRESHOLD = 0.62
SPARSE_OBSERVATION_MAX = 3
PRONUNCIATION_AREA = "area:pronunciation"
PROSODY_AREA = "area:prosody"
FLUENCY_AREA = "area:fluency"


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _mint_recommendation_id(*, student_id: int, primary_skill: str, generated_at: str) -> str:
    raw = f"s9-diag:{student_id}:{primary_skill}:{generated_at}"
    return f"diag-{hashlib.sha256(raw.encode()).hexdigest()[:16]}"


def _parse_goal(speaking_goal: str) -> SpeakingGoal:
    try:
        return SpeakingGoal(speaking_goal)
    except ValueError:
        return SpeakingGoal.general_english


def _goal_weight(node: SpeakingSkillNode, goal: SpeakingGoal) -> float:
    if goal in node.goal_relevance:
        return 1.0
    if SpeakingGoal.general_english in node.goal_relevance:
        return 0.6
    return 0.3


def _cefr_rank(level: str) -> int:
    order = ("A1", "A2", "B1", "B2", "C1", "C2")
    try:
        return order.index(level.upper()[:2] if len(level) > 2 else level.upper())
    except ValueError:
        return 2


def _within_cefr(node: SpeakingSkillNode, official_cefr: str) -> bool:
    rank = _cefr_rank(official_cefr)
    return _cefr_rank(node.cefr_min.value) <= rank <= _cefr_rank(node.cefr_max.value)


def _safe_start_target(
    graph: SpeakingSkillGraph,
    model: StudentSpeakingKnowledgeModel,
    *,
    official_cefr: str,
    goal: SpeakingGoal,
) -> tuple[SpeakingSkillNode, TargetSelectionReason, str, tuple[str, ...]]:
    roots = sorted(
        (n for n in graph.roots if _within_cefr(n, official_cefr)),
        key=lambda n: (-_goal_weight(n, goal), n.difficulty, n.skill_id),
    )
    if not roots:
        roots = sorted(graph.roots, key=lambda n: (n.difficulty, n.skill_id))
    node = roots[0]
    basis = ("sparse_speaking_evidence", f"safe_root:{node.skill_id}")
    return (
        node,
        TargetSelectionReason.sparse_evidence_safe_start,
        "Starting with a foundational speaking skill because evidence is still limited.",
        basis,
    )


def _weakness_reason(node: SpeakingSkillNode, model: StudentSpeakingKnowledgeModel) -> tuple[TargetSelectionReason, str, tuple[str, ...]] | None:
    state = model.skill_states.get(node.skill_id)
    if state is None:
        return None
    tags = set(node.diagnostic_tags)
    basis: list[str] = [f"skill:{node.skill_id}", f"mastery:{state.mastery:.2f}"]

    if PRONUNCIATION_AREA in tags and state.mastery < WEAK_MASTERY_THRESHOLD:
        return (
            TargetSelectionReason.pronunciation_weakness,
            f"Pronunciation practice needed for {node.label}.",
            tuple(basis + ["area:pronunciation"]),
        )
    if (PROSODY_AREA in tags or FLUENCY_AREA in tags) and state.mastery < WEAK_MASTERY_THRESHOLD:
        return (
            TargetSelectionReason.delivery_weakness,
            f"Delivery and fluency focus for {node.label}.",
            tuple(basis + ["area:delivery"]),
        )
    if "area:task" in tags or "area:interaction" in tags:
        if state.recent_performance < WEAK_MASTERY_THRESHOLD:
            return (
                TargetSelectionReason.task_weakness,
                f"Communicative task practice for {node.label}.",
                tuple(basis + ["area:task"]),
            )
    if state.retention_risk >= RETENTION_RISK_THRESHOLD:
        return (
            TargetSelectionReason.at_risk_retention,
            f"Review needed — retention risk for {node.label}.",
            tuple(basis + [f"retention_risk:{state.retention_risk:.2f}"]),
        )
    if state.mastery < WEAK_MASTERY_THRESHOLD and state.evidence_count > 0:
        return (
            TargetSelectionReason.weak_mastery,
            f"Continued practice on {node.label}.",
            tuple(basis),
        )
    return None


def select_speaking_target(
    model: StudentSpeakingKnowledgeModel,
    *,
    official_cefr: str = "A2",
    speaking_goal: str = "general_english",
    graph: SpeakingSkillGraph | None = None,
) -> DiagnosticRecommendation:
    """Deterministic primary target selection — no LLM."""
    g = graph or SPEAKING_SKILL_GRAPH
    goal = _parse_goal(speaking_goal)
    generated_at = _now_iso()
    blocked_all: list[str] = []
    candidates: list[tuple[SpeakingSkillNode, TargetSelectionReason, str, tuple[str, ...], float]] = []

    if model.total_observations <= SPARSE_OBSERVATION_MAX:
        node, reason, detail, basis = _safe_start_target(g, model, official_cefr=official_cefr, goal=goal)
        for n, blocked in eligible_skills(g, model):
            if blocked:
                blocked_all.extend(blocked)
        alts = tuple(
            n.skill_id
            for n, b in eligible_skills(g, model)
            if not b and n.skill_id != node.skill_id
        )[:5]
        return DiagnosticRecommendation(
            recommendation_id=_mint_recommendation_id(
                student_id=model.student_id,
                primary_skill=node.skill_id,
                generated_at=generated_at,
            ),
            version=LANGUAGE_SPEAKING_DIAGNOSTIC_VERSION,
            primary_target_skill_id=node.skill_id,
            target_skill_ids=(node.skill_id,),
            selection_reason=reason,
            reason_detail=detail,
            evidence_basis=basis,
            blocked_skill_ids=tuple(sorted(set(blocked_all))),
            eligible_alternatives=alts,
            official_cefr_hint=official_cefr,
            speaking_goal=speaking_goal,
            generated_at=generated_at,
        )

    at_risk = set(at_risk_skill_ids(model))
    developing = set(developing_skill_ids(model))

    for node, blocked in eligible_skills(g, model):
        if blocked:
            blocked_all.extend(blocked)
            continue
        wr = _weakness_reason(node, model)
        if wr:
            reason, detail, basis = wr
            score = 1.0 - (model.skill_states[node.skill_id].mastery if node.skill_id in model.skill_states else 0.0)
            if node.skill_id in at_risk:
                score += 0.25
            candidates.append((node, reason, detail, basis, score + _goal_weight(node, goal) * 0.1))

    if not candidates:
        for node, blocked in eligible_skills(g, model):
            if blocked:
                continue
            if node.skill_id in developing:
                continue
            ok, _ = prerequisite_state(node, model)
            if ok and _within_cefr(node, official_cefr):
                candidates.append(
                    (
                        node,
                        TargetSelectionReason.progression_next,
                        f"Next skill in your path: {node.label}.",
                        (f"progression:{node.skill_id}",),
                        _goal_weight(node, goal) - node.difficulty * 0.01,
                    )
                )

    if not candidates:
        node, reason, detail, basis = _safe_start_target(g, model, official_cefr=official_cefr, goal=goal)
    else:
        candidates.sort(key=lambda c: (-c[4], c[0].skill_id))
        node, reason, detail, basis, _ = candidates[0]

    alts = tuple(
        n.skill_id
        for n, b in eligible_skills(g, model)
        if not b and n.skill_id != node.skill_id
    )[:5]

    return DiagnosticRecommendation(
        recommendation_id=_mint_recommendation_id(
            student_id=model.student_id,
            primary_skill=node.skill_id,
            generated_at=generated_at,
        ),
        version=LANGUAGE_SPEAKING_DIAGNOSTIC_VERSION,
        primary_target_skill_id=node.skill_id,
        target_skill_ids=(node.skill_id,),
        selection_reason=reason,
        reason_detail=detail,
        evidence_basis=basis,
        blocked_skill_ids=tuple(sorted(set(blocked_all))),
        eligible_alternatives=alts,
        official_cefr_hint=official_cefr,
        speaking_goal=speaking_goal,
        generated_at=generated_at,
    )
