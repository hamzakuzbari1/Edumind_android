"""Balanced skill focus selection (Phase 2.3.1)."""

from __future__ import annotations

import re

from app.services.language_cefr.engine import get_cefr_profile
from app.services.language_listening_curriculum.intent import LessonIntent
from app.services.language_listening_curriculum.objective_catalog import objective_skills
from app.services.language_listening_curriculum.types import ListeningSkillFocus

SKILL_LABELS: dict[ListeningSkillFocus, str] = {
    ListeningSkillFocus.main_idea: "Main Idea",
    ListeningSkillFocus.detail: "Detail",
    ListeningSkillFocus.inference: "Inference",
    ListeningSkillFocus.purpose: "Purpose",
    ListeningSkillFocus.speaker_intention: "Speaker Intention",
    ListeningSkillFocus.tone: "Tone",
    ListeningSkillFocus.prediction: "Prediction",
    ListeningSkillFocus.sequence: "Sequence",
    ListeningSkillFocus.opinion: "Opinion",
    ListeningSkillFocus.bias: "Bias",
}

WEAKNESS_TO_SKILL: dict[str, ListeningSkillFocus] = {
    "inference": ListeningSkillFocus.inference,
    "infer": ListeningSkillFocus.inference,
    "detail": ListeningSkillFocus.detail,
    "main idea": ListeningSkillFocus.main_idea,
    "main_idea": ListeningSkillFocus.main_idea,
    "purpose": ListeningSkillFocus.purpose,
    "speaker intention": ListeningSkillFocus.speaker_intention,
    "speaker_intention": ListeningSkillFocus.speaker_intention,
    "tone": ListeningSkillFocus.tone,
    "prediction": ListeningSkillFocus.prediction,
    "sequence": ListeningSkillFocus.sequence,
    "opinion": ListeningSkillFocus.opinion,
    "bias": ListeningSkillFocus.bias,
    "listening": ListeningSkillFocus.detail,
}

SKILL_COOLDOWN = 3
WEAK_SKILL_BOOST = 0.18


def allowed_skills_for_level(level: str) -> tuple[ListeningSkillFocus, ...]:
    profile = get_cefr_profile(level)
    mapping = {s.value: s for s in ListeningSkillFocus}
    skills: list[ListeningSkillFocus] = []
    for qtype in profile.allowed_question_types:
        skill = mapping.get(qtype.value)
        if skill and skill not in skills:
            skills.append(skill)
    return tuple(skills)


def parse_weak_listening_skills(weaknesses: list[str] | None) -> tuple[ListeningSkillFocus, ...]:
    found: list[ListeningSkillFocus] = []
    for weakness in weaknesses or []:
        blob = weakness.lower().strip()
        for key, skill in WEAKNESS_TO_SKILL.items():
            if key in blob and skill not in found:
                found.append(skill)
    return tuple(found)


def _skill_counts(curriculum_history: list, allowed: tuple[ListeningSkillFocus, ...]) -> dict[str, int]:
    counts: dict[str, int] = {s.value: 0 for s in allowed}
    for entry in curriculum_history[-40:]:
        for skill in getattr(entry, "skill_focus", ()) or ():
            if skill in counts:
                counts[skill] += 1
    return counts


def _recent_skills(curriculum_history: list) -> set[str]:
    recent: set[str] = set()
    for entry in curriculum_history[-SKILL_COOLDOWN:]:
        for skill in getattr(entry, "skill_focus", ()) or ():
            recent.add(skill)
    return recent


def _rank_skills_by_deficit(
    allowed: tuple[ListeningSkillFocus, ...],
    counts: dict[str, int],
    recent: set[str],
    *,
    weak_skills: tuple[ListeningSkillFocus, ...],
    weak_boost: float = WEAK_SKILL_BOOST,
) -> list[ListeningSkillFocus]:
    avg = sum(counts.values()) / max(1, len(counts))
    scored: list[tuple[float, ListeningSkillFocus]] = []
    for skill in allowed:
        deficit = avg - counts.get(skill.value, 0)
        score = 1.0 + deficit * 0.45
        if skill in weak_skills:
            score += weak_boost
        if skill.value in recent:
            score *= 0.25
        scored.append((score, skill))
    scored.sort(key=lambda x: (-x[0], x[1].value))
    return [skill for _, skill in scored]


def _primary_weak_share(curriculum_history: list, weak_skills: tuple[ListeningSkillFocus, ...]) -> float:
    if not weak_skills or not curriculum_history:
        return 0.0
    weak_vals = {s.value for s in weak_skills}
    window = curriculum_history[-40:]
    primaries = [h.skill_focus[0] for h in window if getattr(h, "skill_focus", ())]
    if not primaries:
        return 0.0
    return sum(1 for p in primaries if p in weak_vals) / len(primaries)


def pick_skill_focus(
    level: str,
    *,
    curriculum_history: list,
    weak_skills: tuple[ListeningSkillFocus, ...],
    intent: LessonIntent,
    objectives: tuple[str, ...] = (),
    generation_index: int = 0,
) -> tuple[str, ...]:
    """Select 2–3 skills using balanced intent — weak skills are weighted, never mandatory."""
    allowed = allowed_skills_for_level(level)
    if not allowed:
        return ("detail",)

    counts = _skill_counts(curriculum_history, allowed)
    recent = _recent_skills(curriculum_history)
    weak_share = _primary_weak_share(curriculum_history, weak_skills)

    boost = 0.0
    if intent == LessonIntent.weak_recovery and weak_skills:
        boost = WEAK_SKILL_BOOST
        if weak_share >= 0.35:
            boost *= 0.15
        elif weak_share >= 0.30:
            boost *= 0.45
    elif weak_skills and intent == LessonIntent.balanced_coverage:
        boost = 0.06

    ranked = _rank_skills_by_deficit(allowed, counts, recent, weak_skills=weak_skills, weak_boost=boost)

    objective_related = {s for oid in objectives for s in objective_skills(oid) if s in {a.value for a in allowed}}

    focus: list[str] = []

    if intent == LessonIntent.review and objective_related:
        focus.extend(list(objective_related)[:1])

    if intent == LessonIntent.exploration:
        for skill in ranked:
            if counts.get(skill.value, 0) == 0 and skill.value not in focus:
                focus.append(skill.value)
                break

    for skill in ranked:
        if skill.value not in focus:
            focus.append(skill.value)
        if len(focus) >= 3:
            break

    if intent == LessonIntent.weak_recovery and weak_skills:
        weak_vals = {s.value for s in weak_skills}
        if not any(s in weak_vals for s in focus):
            weakest = min(weak_skills, key=lambda s: counts.get(s.value, 0))
            if len(focus) >= 3:
                focus[-1] = weakest.value
            else:
                focus.append(weakest.value)

    while len(focus) < 3 and ranked:
        for skill in ranked:
            if skill.value not in focus:
                focus.append(skill.value)
            if len(focus) >= 3:
                break

    return tuple(focus[:3])


def neglected_skills(
    level: str,
    curriculum_history: list,
    *,
    min_share: float = 0.04,
    window: int = 40,
) -> list[str]:
    allowed = allowed_skills_for_level(level)
    if not allowed:
        return []
    counts = _skill_counts(curriculum_history[-window:], allowed)
    total = sum(counts.values()) or 1
    return [s.value for s in allowed if counts.get(s.value, 0) / total < min_share]


def objective_slug(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")
    return slug[:64] or "objective"
