"""Pure assembler for StudentSpeakingLiveContext (S7.6 — read-only)."""

from __future__ import annotations

from datetime import datetime, timezone

from app.services.language_speaking_curriculum.types import SpeakingSkillGraph
from app.services.language_speaking_evaluator.evaluation_result import SpeakingEvaluationEngineResult
from app.services.language_speaking_knowledge_model.summaries import at_risk_skill_ids, mastered_skill_ids
from app.services.language_speaking_knowledge_model.types import (
    SpeakingSkillStatus,
    StudentSpeakingKnowledgeModel,
)
from app.services.language_speaking_coach.types import (
    PrioritySkillTarget,
    STUDENT_SPEAKING_LIVE_CONTEXT_VERSION,
    StudentSpeakingLiveContext,
)

RETENTION_RISK_THRESHOLD = 0.55
WEAK_MASTERY_THRESHOLD = 0.45
MAX_PRIORITY_TARGETS = 5
MAX_MISTAKE_TAGS = 5
MAX_RETENTION_TARGETS = 5
MAX_GUIDANCE_LINES = 6


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _skill_label(graph: SpeakingSkillGraph, skill_id: str) -> tuple[str, str]:
    node = graph.node_by_id(skill_id)
    if node is None:
        return skill_id, "unknown"
    return node.label, str(node.skill_type.value if hasattr(node.skill_type, "value") else node.skill_type)


def _mastery_band(mastery: float) -> str:
    if mastery >= 0.75:
        return "strong"
    if mastery >= 0.55:
        return "stable"
    if mastery >= 0.35:
        return "developing"
    return "needs_work"


def _priority_targets(
    model: StudentSpeakingKnowledgeModel,
    graph: SpeakingSkillGraph,
    evaluation: SpeakingEvaluationEngineResult | None,
) -> tuple[PrioritySkillTarget, ...]:
    candidates: dict[str, tuple[float, float, float, str]] = {}

    for sid in at_risk_skill_ids(model):
        st = model.skill_states[sid]
        candidates[sid] = (st.retention_risk, st.mastery, st.confidence, "at_risk")

    for sid, st in model.skill_states.items():
        if st.current_status in (SpeakingSkillStatus.developing, SpeakingSkillStatus.observed):
            if st.mastery < WEAK_MASTERY_THRESHOLD and sid not in candidates:
                candidates[sid] = (st.retention_risk, st.mastery, st.confidence, "weak_mastery")

    if evaluation is not None:
        for ev in evaluation.candidate_skill_evidence:
            if not ev.success and ev.skill_id not in candidates:
                candidates[ev.skill_id] = (0.0, ev.performance, ev.confidence, "recent_evaluation_gap")

    ranked = sorted(
        candidates.items(),
        key=lambda item: (-item[1][0], item[1][1], item[1][2]),
    )[:MAX_PRIORITY_TARGETS]

    out: list[PrioritySkillTarget] = []
    for sid, (_, _m, _c, reason) in ranked:
        label, skill_type = _skill_label(graph, sid)
        out.append(PrioritySkillTarget(skill_id=sid, label=label, skill_type=skill_type, reason=reason))
    return tuple(out)


def _recurring_mistakes(model: StudentSpeakingKnowledgeModel) -> tuple[str, ...]:
    patterns = sorted(
        model.mistake_patterns.values(),
        key=lambda mp: (-mp.occurrence_count, -mp.recent_occurrence_count),
    )
    return tuple(mp.mistake_tag for mp in patterns[:MAX_MISTAKE_TAGS] if mp.occurrence_count > 0)


def _retention_targets(model: StudentSpeakingKnowledgeModel, graph: SpeakingSkillGraph) -> tuple[str, ...]:
    ranked: list[tuple[float, str, str]] = []
    for sid, st in model.skill_states.items():
        if st.retention_risk >= RETENTION_RISK_THRESHOLD:
            label, _ = _skill_label(graph, sid)
            ranked.append((st.retention_risk, sid, label))
    ranked.sort(key=lambda x: -x[0])
    return tuple(label for _, _, label in ranked[:MAX_RETENTION_TARGETS])


def _recent_strengths(
    model: StudentSpeakingKnowledgeModel,
    graph: SpeakingSkillGraph,
    evaluation: SpeakingEvaluationEngineResult | None,
) -> tuple[str, ...]:
    strengths: list[str] = []
    if evaluation is not None:
        strengths.extend(list(evaluation.strengths)[:3])
    for sid in mastered_skill_ids(model)[:2]:
        label, _ = _skill_label(graph, sid)
        if label not in strengths:
            strengths.append(label)
    return tuple(strengths[:4])


def _revision_needs(evaluation: SpeakingEvaluationEngineResult | None) -> tuple[str, ...]:
    if evaluation is None:
        return ()
    needs: list[str] = list(evaluation.revision_readiness.blockers)
    for dim in (
        evaluation.task_response,
        evaluation.pronunciation,
        evaluation.fluency_delivery,
        evaluation.grammar,
        evaluation.vocabulary,
        evaluation.coherence,
    ):
        if not dim.passed and dim.reason:
            needs.append(f"{dim.dimension}: {dim.reason}")
    if evaluation.priority_issue:
        needs.append(evaluation.priority_issue)
    return tuple(list(dict.fromkeys(needs))[:5])


def _conversation_guidance(
    *,
    learner_state: str,
    priority_targets: tuple[PrioritySkillTarget, ...],
    mistakes: tuple[str, ...],
    revision_needs: tuple[str, ...],
) -> tuple[str, ...]:
    guidance: list[str] = []
    if learner_state == "new_learner":
        guidance.append("Use warm, simple prompts and short turns to build confidence.")
        guidance.append("Encourage full-sentence answers without over-correction.")
    else:
        guidance.append("Stay a natural conversation partner — do not read scores aloud.")
        if priority_targets:
            labels = ", ".join(t.label for t in priority_targets[:3])
            guidance.append(f"Create natural opportunities to practice: {labels}.")
        if mistakes:
            guidance.append("Avoid repeating the same mid-sentence correction; revisit patterns gently later.")
        if revision_needs:
            guidance.append("Allow slightly longer responses before interrupting when the learner is thinking.")
        guidance.append("Ask occasional clarification questions to keep dialogue interactive.")
    return tuple(guidance[:MAX_GUIDANCE_LINES])


def assemble_student_speaking_live_context(
    *,
    student_reference: str,
    speaking_goal: str,
    knowledge_model: StudentSpeakingKnowledgeModel,
    skill_graph: SpeakingSkillGraph,
    latest_evaluation: SpeakingEvaluationEngineResult | None = None,
) -> StudentSpeakingLiveContext:
    """Deterministic read-only summarization — no S8 diagnostic logic."""
    unavailable: list[str] = []
    has_s2 = knowledge_model.total_observations > 0 or bool(knowledge_model.skill_states)
    has_s7 = latest_evaluation is not None

    if not has_s2 and not has_s7:
        learner_state = "new_learner"
        unavailable.extend(["s2_knowledge_model", "s7_evaluation"])
    elif not has_s2:
        learner_state = "returning_without_mastery_history"
        unavailable.append("s2_knowledge_model")
    elif not has_s7:
        learner_state = "practicing_with_mastery_history"
        unavailable.append("s7_evaluation")
    else:
        learner_state = "active_with_recent_evaluation"

    priority = _priority_targets(knowledge_model, skill_graph, latest_evaluation)
    mistakes = _recurring_mistakes(knowledge_model) if has_s2 else ()
    retention = _retention_targets(knowledge_model, skill_graph) if has_s2 else ()
    strengths = _recent_strengths(knowledge_model, skill_graph, latest_evaluation)
    revision = _revision_needs(latest_evaluation)

    guidance = _conversation_guidance(
        learner_state=learner_state,
        priority_targets=priority,
        mistakes=mistakes,
        revision_needs=revision,
    )

    return StudentSpeakingLiveContext(
        context_version=STUDENT_SPEAKING_LIVE_CONTEXT_VERSION,
        student_reference=student_reference,
        speaking_goal=speaking_goal or "general_english",
        learner_state=learner_state,
        priority_skill_targets=priority,
        recurring_mistake_patterns=mistakes,
        retention_review_targets=retention,
        recent_strengths=strengths,
        recent_revision_needs=revision,
        conversation_guidance=guidance,
        unavailable_context=tuple(unavailable),
        generated_at=_now_iso(),
    )
