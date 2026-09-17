"""Promotion readiness telemetry — blockers, strengths, actions (Phase 5.3)."""

from __future__ import annotations

from app.services.language_promotion_readiness.types import ReadinessDimensionScore
from app.services.language_transition_gate.types import TransitionGateContext

_BLOCKER_LABELS: dict[str, str] = {
    "evidence": "Evidence coverage",
    "learning_stage": "Learning stage progress",
    "stage_score": "Stage score",
    "confidence": "Listening confidence",
    "objective_mastery": "Objective mastery",
    "transition_gate": "Transition gate completion",
    "review_completion": "Pending reviews",
    "lesson_exposure": "Lesson count",
    "challenge_stability": "Challenge stability",
    "consistency": "Listening consistency",
}

_STRENGTH_THRESHOLDS: dict[str, str] = {
    "confidence": "High confidence",
    "evidence": "Strong evidence coverage",
    "consistency": "Strong consistency",
    "objective_mastery": "Strong objective mastery",
    "challenge_stability": "Stable challenge performance",
    "stage_score": "Strong stage score",
    "transition_gate": "Transition gate nearly complete",
}


def _blocker_label(name: str) -> str:
    return _BLOCKER_LABELS.get(name, name.replace("_", " ").title())


def build_blockers(
    *,
    dimensions: list[ReadinessDimensionScore],
    ranked_gaps: list[tuple[str, float]],
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    if not ranked_gaps:
        return (), ()

    primary_name = ranked_gaps[0][0]
    primary = (_blocker_label(primary_name),)
    secondary = tuple(_blocker_label(name) for name, _ in ranked_gaps[1:4])
    return primary, secondary


def build_strengths(
    *,
    ctx: TransitionGateContext,
    dimensions: list[ReadinessDimensionScore],
) -> tuple[str, ...]:
    strengths: list[str] = []

    for dim in dimensions:
        if dim.progress < 0.85:
            continue
        label = _STRENGTH_THRESHOLDS.get(dim.name)
        if label:
            strengths.append(f"{label} ({int(dim.progress * 100)}%).")

    if ctx.missing_inference_evidence is False and ctx.confidence_avg >= 0.80:
        msg = "Excellent inference accuracy."
        if msg not in strengths:
            strengths.append(msg)

    if not ctx.missing_speaker_evidence and ctx.evidence_coverage_avg >= 0.72:
        msg = "Excellent multi-speaker evidence."
        if msg not in strengths:
            strengths.append(msg)

    if ctx.recent_consistency >= 0.70:
        msg = "Strong consistency across recent lessons."
        if msg not in strengths:
            strengths.append(msg)

    if ctx.confidence_avg >= 0.80:
        msg = "High confidence."
        if msg not in strengths:
            strengths.append(msg)

    return tuple(strengths[:6])


def build_next_actions(
    *,
    ctx: TransitionGateContext,
    dimensions: list[ReadinessDimensionScore],
    ranked_gaps: list[tuple[str, float]],
) -> tuple[str, ...]:
    actions: list[str] = []
    gap_names = {name for name, _ in ranked_gaps}

    if ctx.pending_review_count > 0:
        if ctx.review_due_objectives:
            actions.append(
                f"Complete review lessons for: {', '.join(ctx.review_due_objectives[:2])}."
            )
        else:
            actions.append(
                f"Complete {ctx.pending_review_count} pending review lesson(s)."
            )

    if "evidence" in gap_names:
        if ctx.missing_inference_evidence:
            actions.append("Improve announcement and inference evidence.")
        if ctx.missing_speaker_evidence:
            actions.append("Practice one lecture or multi-speaker listening lesson.")
        elif ctx.needs_evidence_objectives:
            actions.append(
                f"Close evidence gaps for: {', '.join(ctx.needs_evidence_objectives[:2])}."
            )

    if "lesson_exposure" in gap_names:
        exposure_dim = next((d for d in dimensions if d.name == "lesson_exposure"), None)
        if exposure_dim:
            bar_remaining = max(0, int(exposure_dim.required - exposure_dim.current))
            if bar_remaining:
                actions.append(f"Complete {bar_remaining} more listening lesson(s) for exposure.")

    if "confidence" in gap_names:
        actions.append(
            f"Build confidence from {int(ctx.confidence_avg * 100)}% "
            "with focused practice on weaker objectives."
        )

    if "consistency" in gap_names:
        actions.append("Increase listening consistency with regular short sessions.")

    if "learning_stage" in gap_names or "stage_score" in gap_names:
        actions.append(
            f"Advance learning stage (currently stage {ctx.persistent_stage}, "
            f"score {ctx.stage_score})."
        )

    if "objective_mastery" in gap_names:
        remaining = max(0, ctx.total_objectives - ctx.mastered_objectives)
        actions.append(f"Master {remaining} more curriculum objective(s).")

    if "challenge_stability" in gap_names:
        actions.append(
            f"Stabilize challenge at Normal (current: {ctx.challenge_level})."
        )

    seen: set[str] = set()
    unique: list[str] = []
    for action in actions:
        if action not in seen:
            seen.add(action)
            unique.append(action)
    return tuple(unique[:6])
