"""Resolve learner text to a canonical learning goal (Phase 3.1)."""

from __future__ import annotations

import re

from app.services.language_learning_goal.types import LearningGoal

_GOAL_ALIASES: dict[str, LearningGoal] = {
    "academic": LearningGoal.academic,
    "ielts": LearningGoal.ielts,
    "toefl": LearningGoal.toefl,
    "business": LearningGoal.business,
    "job interview": LearningGoal.job_interview,
    "job_interview": LearningGoal.job_interview,
    "interview prep": LearningGoal.job_interview,
    "career": LearningGoal.job_interview,
    "travel": LearningGoal.travel,
    "daily life": LearningGoal.daily_life,
    "daily_life": LearningGoal.daily_life,
    "everyday": LearningGoal.daily_life,
    "university": LearningGoal.university,
    "college": LearningGoal.university,
    "campus": LearningGoal.university,
    "conversation": LearningGoal.conversation,
    "speaking": LearningGoal.conversation,
    "general english": LearningGoal.general_english,
    "general_english": LearningGoal.general_english,
    "general": LearningGoal.general_english,
    "english": LearningGoal.general_english,
}

_FUTURE_GOAL_MAP: dict[str, LearningGoal] = {
    "engineer": LearningGoal.academic,
    "doctor": LearningGoal.academic,
    "teacher": LearningGoal.university,
    "business": LearningGoal.business,
    "travel": LearningGoal.travel,
    "undecided": LearningGoal.general_english,
}


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower().strip())


def match_learning_goal(text: str) -> LearningGoal | None:
    blob = _normalize(text)
    if not blob:
        return None
    for alias, goal in sorted(_GOAL_ALIASES.items(), key=lambda x: -len(x[0])):
        if alias in blob:
            return goal
    return None


def resolve_learning_goal(
    *,
    explicit: str | LearningGoal | None = None,
    future_goal: str | None = None,
    learning_goals: list[str] | None = None,
) -> LearningGoal:
    if isinstance(explicit, LearningGoal):
        return explicit
    if explicit:
        matched = match_learning_goal(str(explicit))
        if matched:
            return matched
        try:
            return LearningGoal(str(explicit).lower().replace(" ", "_"))
        except ValueError:
            pass

    for raw in learning_goals or []:
        matched = match_learning_goal(raw)
        if matched:
            return matched

    if future_goal:
        mapped = _FUTURE_GOAL_MAP.get(_normalize(future_goal))
        if mapped:
            return mapped
        matched = match_learning_goal(future_goal)
        if matched:
            return matched

    return LearningGoal.general_english


def parse_learning_goal_from_context(adaptive_context: str) -> LearningGoal:
    future_goal = ""
    goals: list[str] = []
    for line in (adaptive_context or "").splitlines():
        lower = line.lower()
        if lower.startswith("future goal:"):
            future_goal = line.split(":", 1)[-1].strip()
        elif lower.startswith("learning goals:"):
            tail = line.split(":", 1)[-1].strip()
            goals = [part.strip() for part in tail.split(",") if part.strip()]
    return resolve_learning_goal(future_goal=future_goal, learning_goals=goals)


def enrich_topics_for_goal(base_topics: str, profile_vocabulary: tuple[str, ...]) -> str:
    parts = [part.strip() for part in (base_topics or "").split(",") if part.strip()]
    for domain in profile_vocabulary:
        if domain not in parts:
            parts.append(domain)
    return ", ".join(parts[:12])
