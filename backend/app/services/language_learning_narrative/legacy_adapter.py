"""Backward-compatible adapters mapping narrative output to legacy explainability types."""

from __future__ import annotations

from app.services.language_learning_facts.labels import slug_label
from app.services.language_learning_narrative.types import LessonNarrative
from app.services.language_listening_confidence.telemetry import compute_confidence_telemetry
from app.services.language_listening_confidence.types import ConfidenceState
from app.services.language_listening_explainability.facts import ExplainabilityFacts
from app.services.language_listening_explainability.types import LessonExplainability, StudentSummary


def legacy_lesson_explainability(
    narrative: LessonNarrative,
    explain: ExplainabilityFacts,
) -> LessonExplainability:
    """Map Phase 2.1 narrative + facts to legacy LessonExplainability for existing callers."""
    focus_text = ", ".join(narrative.student_focus) if narrative.student_focus else "none selected"
    obj_text = ", ".join(slug_label(o) for o in explain.curriculum_objectives) or "none selected"
    q_types = ", ".join(slug_label(t) for t in explain.question_types) if explain.question_types else ""

    why_topic = (
        f"Topic category '{slug_label(explain.situation.category)}' with situation "
        f"'{narrative.situation_label}' matched intelligence rotation signals."
    )
    why_format = (
        f"Format '{slug_label(explain.situation.narrative_format)}' at pace "
        f"'{slug_label(explain.situation.pace)}' aligned with format rotation."
    )
    why_difficulty = narrative.challenge_reason
    if q_types:
        why_questions = f"Questions use types [{q_types}] targeting objectives [{obj_text}]."
    else:
        why_questions = f"Question design follows objectives [{obj_text}] and focus [{focus_text}]."

    current_goal = "No learning goal signal recorded for this lesson."
    if explain.goal.lesson_goal_id:
        current_goal = (
            f"Lesson Goal '{explain.goal.goal_profile_label or slug_label(explain.goal.lesson_goal_id)}' "
            f"(alignment {explain.goal.goal_alignment_score:.2f})."
        )

    confidence_reason = "No per-objective confidence snapshot recorded for this lesson."
    if explain.weak_objectives:
        lines = [
            f"{slug_label(w.objective_id)} confidence {w.confidence:.2f}, coverage {w.coverage:.2f}"
            for w in explain.weak_objectives[:2]
        ]
        confidence_reason = "Confidence engine prioritised: " + "; ".join(lines) + "."

    review_reason = "No review intent or review objectives in this lesson recommendation."
    if explain.review_active:
        review_objs = ", ".join(slug_label(o) for o in explain.review_objectives) or "none listed"
        review_reason = f"Review intent active; review objectives: {review_objs}."

    next_bits = [slug_label(code.split(":", 1)[-1]) for code in explain.next_planning_signal_codes[:4]]
    next_recommendation = (
        "Next planning signals suggest: " + "; ".join(next_bits) + "."
        if next_bits
        else "Continue balanced coverage at current challenge band."
    )

    teacher_note = (
        f"Lesson intent={explain.selection_rationale.lesson_intent}, "
        f"stage={explain.selection_rationale.curriculum_stage}, "
        f"challenge={explain.challenge.challenge_level}, "
        f"goal={explain.goal.lesson_goal_id or 'general'}."
    )
    if explain.weak_skills:
        teacher_note += f" Learner weak skills flagged: {', '.join(slug_label(w) for w in explain.weak_skills)}."

    return LessonExplainability(
        why_this_lesson=narrative.why_this_lesson,
        why_this_topic=why_topic,
        why_this_format=why_format,
        why_this_difficulty=why_difficulty,
        why_these_questions=why_questions,
        current_focus=f"Skill focus: {focus_text}. Objectives: {obj_text}.",
        current_goal=current_goal,
        challenge_reason=narrative.challenge_reason,
        confidence_reason=confidence_reason,
        review_reason=review_reason,
        next_recommendation=next_recommendation,
        teacher_note=teacher_note,
        student_tip=narrative.coach_summary,
    )


def legacy_student_summary(
    narrative: LessonNarrative,
    explain: ExplainabilityFacts,
    *,
    confidence_state: ConfidenceState | None,
) -> StudentSummary:
    """Map narrative + facts to legacy StudentSummary for existing callers."""
    conf_telemetry = compute_confidence_telemetry(confidence_state) if confidence_state else None

    improved_parts: list[str] = []
    if conf_telemetry:
        for oid, trend in sorted(conf_telemetry.trends.items(), key=lambda x: x[1], reverse=True)[:2]:
            if trend > 0.02:
                improved_parts.append(f"{slug_label(oid)} (confidence trend +{trend:.2f})")
    what_improved = (
        "You are improving in: " + ", ".join(improved_parts) + "."
        if improved_parts
        else "Keep practising — improvement trends will appear after more completed lessons."
    )

    practice_targets = list(narrative.expected_improvement)
    if conf_telemetry and conf_telemetry.under_confident:
        practice_targets.append(slug_label(conf_telemetry.under_confident[0]))
    what_needs_practice = (
        "Today's practice targets: " + ", ".join(dict.fromkeys(practice_targets)) + "."
        if practice_targets
        else "Continue balanced listening practice across all skills."
    )

    why_today_matters = narrative.why_this_lesson
    knowledge_node = explain.knowledge_node
    situation_raw = explain.situation.situation_id
    how_helps = (
        f"Practising '{narrative.situation_label}' builds your '{slug_label(knowledge_node)}' "
        f"knowledge chain for future lessons at {explain.level_context.cefr_level}."
        if knowledge_node and situation_raw
        else narrative.next_after_this
    )

    study_tip = narrative.coach_summary
    if conf_telemetry and conf_telemetry.needs_evidence:
        oid = conf_telemetry.needs_evidence[0]
        missing = conf_telemetry.missing_evidence_summary.get(oid, {})
        axes = [k for k, vals in missing.items() if isinstance(vals, list) and vals]
        if axes:
            study_tip = (
                f"For {slug_label(oid)}, seek listening practice with varied "
                f"{', '.join(slug_label(a) for a in axes[:3])}."
            )

    mastered = conf_telemetry.mastered_count if conf_telemetry else 0
    promote = explain.challenge.promotion_count
    motivational = (
        f"You have {mastered} mastered listening objective(s) at {explain.level_context.cefr_level}"
        + (f" and {promote} challenge promotion(s) on record." if promote else ".")
    )

    return StudentSummary(
        what_improved=what_improved,
        what_needs_practice=what_needs_practice,
        why_today_matters=why_today_matters,
        how_helps_future=how_helps,
        study_tip=study_tip,
        motivational_sentence=motivational,
    )
