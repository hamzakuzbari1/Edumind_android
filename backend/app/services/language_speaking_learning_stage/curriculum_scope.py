"""Curriculum-relative skill membership for stage signals (S15).

Evaluates the student against CURRENT official CEFR skills only.
B1 mastery must never advance A2 internal stage signals.
"""

from __future__ import annotations

from app.services.language_speaking_curriculum.skill_catalog import SPEAKING_SKILL_GRAPH
from app.services.language_speaking_curriculum.types import SpeakingSkillNode

# Core skills: in-level roots OR low-difficulty in-level nodes.
CORE_DIFFICULTY_FLOOR = 2


def _cefr_rank(level: str) -> int:
    order = ("A1", "A2", "B1", "B2", "C1", "C2")
    try:
        return order.index(level.upper()[:2] if len(level) > 2 else level.upper())
    except ValueError:
        return 2


def skill_within_official_cefr(node: SpeakingSkillNode, official_cefr: str) -> bool:
    """Node is in-level iff cefr_min ≤ official ≤ cefr_max (mirrors diagnostic selector)."""
    rank = _cefr_rank(official_cefr)
    return _cefr_rank(node.cefr_min.value) <= rank <= _cefr_rank(node.cefr_max.value)


def curriculum_skills_for_official_cefr(
    official_cefr: str,
    *,
    graph=SPEAKING_SKILL_GRAPH,
) -> tuple[SpeakingSkillNode, ...]:
    """Return S1 nodes belonging to the given official CEFR band only."""
    return tuple(
        sorted(
            (n for n in graph.nodes if skill_within_official_cefr(n, official_cefr)),
            key=lambda n: (n.difficulty, n.skill_id),
        )
    )


def core_curriculum_skills(
    nodes: tuple[SpeakingSkillNode, ...],
    *,
    difficulty_floor: int = CORE_DIFFICULTY_FLOOR,
) -> tuple[SpeakingSkillNode, ...]:
    """Core in-level skills: roots or difficulty ≤ floor."""
    return tuple(n for n in nodes if n.is_root or n.difficulty <= difficulty_floor)
