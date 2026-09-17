"""Learning Narrative Builder — converts facts into student-facing copy (Phase 2.1)."""

from __future__ import annotations

from app.services.language_learning_facts.labels import slug_label
from app.services.language_learning_facts.types import (
    LessonFactsBundle,
    LevelContextFacts,
    PostLessonFacts,
    ProgressionFacts,
)
from app.services.language_learning_narrative.types import AfterLessonNarrative, LessonNarrative
from app.services.language_listening_explainability.facts import ExplainabilityFacts


def _format_factors(factors: tuple[tuple[str, float], ...]) -> str:
    if not factors:
        return ""
    return ", ".join(f"{slug_label(name)} ({score:.2f})" for name, score in factors)


def _level_note_text(facts: ExplainabilityFacts) -> str | None:
    code = facts.level_context.mismatch_reason_code
    if not facts.level_context.mismatch or not code:
        return None
    if code == "CHALLENGE_MODE":
        return "This lesson is at a challenge level to stretch your listening skills."
    if code == "SPECIAL_REVIEW":
        return "This lesson reviews skills at a supportive level to rebuild confidence."
    if code == "PROMOTION_TEST":
        return "This lesson is part of your promotion assessment."
    return None


def _build_student_focus(lesson: LessonFactsBundle, explain: ExplainabilityFacts) -> tuple[str, ...]:
    items: list[str] = []
    for oid in explain.curriculum_objectives[:2]:
        label = slug_label(oid)
        if label and label not in items:
            items.append(label)
    for sk in explain.skill_focus:
        label = slug_label(sk)
        if label and label not in items:
            items.append(label)
    for qtype in explain.question_types[:2]:
        label = slug_label(qtype)
        if label and label not in items:
            items.append(label)
    if lesson.lesson_title and len(items) < 3:
        items.append(lesson.lesson_title)
    situation = slug_label(explain.situation.situation_id)
    if situation and len(items) < 3 and situation not in items:
        items.append(situation)
    return tuple(items[:3])


def _reward_line(progression: ProgressionFacts | None, level: LevelContextFacts) -> str:
    if progression and progression.journey_target_level:
        return f"Progress toward {progression.journey_target_level}"
    if progression and progression.official_level:
        return f"Progress at {progression.official_level}"
    if level.official_level:
        return f"Progress at {level.official_level}"
    return f"Progress at {level.cefr_level}"


def build_lesson_narrative(
    lesson: LessonFactsBundle,
    explain: ExplainabilityFacts,
    *,
    progression: ProgressionFacts | None = None,
) -> LessonNarrative:
    """Produce all lesson-scoped student copy from structured facts."""
    level: LevelContextFacts = explain.level_context
    situation_label = slug_label(explain.situation.situation_id) or "today's topic"
    intent = slug_label(explain.selection_rationale.lesson_intent)
    stage = slug_label(explain.selection_rationale.curriculum_stage)
    score = explain.selection_rationale.recommendation_score
    factors = _format_factors(explain.selection_rationale.top_score_factors)

    reason_selected = (
        f"Curriculum selected {situation_label} with intent '{intent}' at stage '{stage}' "
        f"(score {score:.2f}"
        + (f"; factors: {factors}" if factors else "")
        + ")."
    )
    if explain.selection_rationale.goal_id:
        reason_selected += (
            f" Lesson Goal '{slug_label(explain.selection_rationale.goal_id)}' "
            f"alignment {explain.selection_rationale.goal_alignment_score:.2f}."
        )

    objectives_text = ", ".join(slug_label(o) for o in explain.curriculum_objectives) or "core listening skills"
    why_this_lesson = (
        f"This {explain.challenge.challenge_label} lesson about {situation_label} "
        f"uses intent '{intent}' to work on {objectives_text}."
    )
    if explain.weak_objectives:
        weak = slug_label(explain.weak_objectives[0].objective_id)
        why_this_lesson += f" Priority objective: {weak} (coverage {explain.weak_objectives[0].coverage:.2f})."

    student_focus = _build_student_focus(lesson, explain)
    expected_improvement = tuple(slug_label(o) for o in explain.curriculum_objectives[:4]) or (
        "balanced listening skills",
    )

    challenge_reason = (
        f"Challenge level '{explain.challenge.challenge_level}' "
        f"(score {explain.challenge.challenge_score:.2f}); "
        f"band '{slug_label(explain.challenge.effective_difficulty_band)}'."
    )
    if explain.review_active:
        review_objs = ", ".join(slug_label(o) for o in explain.review_objectives) or "scheduled review"
        challenge_reason += f" Review focus: {review_objs}."

    reward = _reward_line(progression, level)
    if progression and progression.promotion and progression.promotion.estimated_lessons_remaining is not None:
        remaining = progression.promotion.estimated_lessons_remaining
        next_after_this = (
            f"After this lesson, about {remaining} more practice lesson(s) until your promotion test."
            if remaining > 0
            else "You may be ready to try your promotion test after this lesson."
        )
    else:
        next_after_this = "Continue with your next listening practice clip."

    focus_preview = student_focus[0] if student_focus else "main ideas"
    coach_summary = (
        f"Today you will practice {focus_preview} in a "
        f"{slug_label(explain.situation.narrative_format) or 'listening'} clip about {situation_label}."
    )
    if lesson.goal.lesson_goal_id:
        coach_summary += f" This supports your {lesson.goal.goal_profile_label or slug_label(lesson.goal.lesson_goal_id)} Lesson Goal."

    return LessonNarrative(
        reason_selected=reason_selected,
        why_this_lesson=why_this_lesson,
        student_focus=student_focus,
        expected_improvement=expected_improvement,
        reward=reward,
        coach_summary=coach_summary,
        challenge_reason=challenge_reason,
        next_after_this=next_after_this,
        situation_label=situation_label,
        level_note=_level_note_text(explain),
    )


def build_after_lesson_narrative(
    lesson: LessonFactsBundle,
    explain: ExplainabilityFacts,
    post: PostLessonFacts,
    *,
    progression: ProgressionFacts | None = None,
) -> AfterLessonNarrative:
    """Post-lesson student copy from result facts."""
    passed = post.passed
    headline = "Great work!" if passed else "Good effort — keep practising!"
    summary = (
        f"You scored {post.score_percent:.0f}% ({post.correct_count}/{post.total_questions} correct)."
    )

    improved: list[str] = []
    for oid in post.objectives_correct[:3]:
        improved.append(f"{slug_label(oid)} listening")
    if not improved and passed:
        improved.append("overall listening accuracy")

    needs: list[str] = []
    for oid in post.objectives_incorrect[:3]:
        needs.append(slug_label(oid))
    if not needs:
        for sk in explain.skill_focus[:2]:
            needs.append(slug_label(sk))

    teaser = "Your next listening practice clip is ready when you are."
    if progression and progression.promotion and progression.promotion.can_start_promotion_test:
        teaser = "You may be ready for your promotion test."

    coach_summary = (
        "Strong session — your listening practice is paying off."
        if passed
        else "Every attempt builds your listening skills — try the next clip when ready."
    )

    return AfterLessonNarrative(
        headline=headline,
        summary=summary,
        improved=tuple(improved) if improved else ("keep practising consistently",),
        needs_practice=tuple(needs) if needs else ("balanced listening practice",),
        next_lesson_teaser=teaser,
        coach_summary=coach_summary,
    )
