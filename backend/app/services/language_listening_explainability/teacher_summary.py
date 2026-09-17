"""Teacher-facing explainability summary (Phase 3.4)."""

from __future__ import annotations

from app.services.language_learning_goal.profiles import profile_for_goal
from app.services.language_learning_goal.types import LearningGoal
from app.services.language_listening_challenge.telemetry import compute_challenge_telemetry
from app.services.language_listening_challenge.types import ChallengeState
from app.services.language_listening_confidence.telemetry import compute_confidence_telemetry
from app.services.language_listening_confidence.types import ConfidenceState
from app.services.language_learning_facts.labels import slug_label
from app.services.language_listening_explainability.builder import extract_signals
from app.services.language_listening_explainability.learning_path import build_learning_path
from app.services.language_listening_explainability.types import ExplainabilitySignals, TeacherSummary


def build_teacher_summary(
    signals: ExplainabilitySignals,
    *,
    confidence_state: ConfidenceState | None,
    challenge_state: ChallengeState | None,
) -> TeacherSummary:
    level = signals.cefr_level
    conf_telemetry = compute_confidence_telemetry(confidence_state) if confidence_state else None
    ch_telemetry = compute_challenge_telemetry(challenge_state) if challenge_state else None
    path = build_learning_path(confidence_state, level=level)

    strengths: list[str] = []
    weaknesses: list[str] = []
    if conf_telemetry:
        for oid in conf_telemetry.high_confidence[:4]:
            conf = conf_telemetry.confidence_by_objective.get(oid, 0.0)
            cov = conf_telemetry.coverage_by_objective.get(oid, 0.0)
            trend = conf_telemetry.trends.get(oid, 0.0)
            strengths.append(
                f"{slug_label(oid)}: confidence {conf:.2f}, coverage {cov:.2f}"
                + (f", trend +{trend:.2f}" if trend > 0.02 else "")
            )
        for oid in conf_telemetry.under_confident[:4]:
            conf = conf_telemetry.confidence_by_objective.get(oid, 0.0)
            weaknesses.append(f"{slug_label(oid)}: confidence {conf:.2f}")

    improved: list[str] = []
    if conf_telemetry:
        for oid, trend in sorted(conf_telemetry.trends.items(), key=lambda x: x[1], reverse=True):
            if trend > 0.03:
                improved.append(f"{slug_label(oid)} (+{trend:.2f})")
    recent_improvement = (
        "Recent confidence gains: " + ", ".join(improved[:3]) + "."
        if improved
        else "No positive confidence trends recorded yet."
    )

    bottleneck = "No confidence state available."
    if path.objectives:
        weakest = min(path.objectives, key=lambda o: o.mastery)
        bottleneck = (
            f"{weakest.label} — mastery {weakest.mastery:.2f}, "
            f"confidence {weakest.confidence:.2f}, status {weakest.status}."
        )

    recommended_challenge = "normal"
    if ch_telemetry:
        recommended_challenge = (
            f"{level} {ch_telemetry.current_challenge.title()} "
            f"(challenge score {ch_telemetry.challenge_score:.2f}; "
            f"last adjustment: {ch_telemetry.last_adjustment_reason})."
        )

    review_priorities = tuple(slug_label(o) for o in (conf_telemetry.review_due[:5] if conf_telemetry else []))

    intel = signals.intelligence
    goal_meta = signals.goal
    suggested_styles: list[str] = []
    nf = intel.get("narrative_format")
    if isinstance(nf, str) and nf:
        suggested_styles.append(slug_label(nf))
    arc = intel.get("narrative_arc")
    if isinstance(arc, str) and arc:
        suggested_styles.append(slug_label(arc))

    suggested_situations: list[str] = []
    situation = intel.get("situation")
    if isinstance(situation, str) and situation:
        suggested_situations.append(slug_label(situation))
    goal_val = str(goal_meta.get("learning_goal") or "")
    if goal_val:
        try:
            profile = profile_for_goal(LearningGoal(goal_val))
            suggested_situations.extend(slug_label(s) for s in sorted(profile.preferred_situations)[:4])
        except ValueError:
            pass
    seen: set[str] = set()
    deduped_situations = tuple(s for s in suggested_situations if not (s in seen or seen.add(s)))

    return TeacherSummary(
        strengths=tuple(strengths) if strengths else ("No high-confidence objectives recorded yet.",),
        weaknesses=tuple(weaknesses) if weaknesses else ("No under-confident objectives flagged.",),
        recent_improvement=recent_improvement,
        current_bottleneck=bottleneck,
        recommended_next_challenge=recommended_challenge,
        review_priorities=review_priorities,
        suggested_transcript_styles=tuple(suggested_styles) if suggested_styles else ("No format signal.",),
        suggested_situations=deduped_situations if deduped_situations else ("No situation signal.",),
    )
