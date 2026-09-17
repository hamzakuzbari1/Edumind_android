"""Signal extraction from stored lesson metadata (Phase 2.1)."""

from __future__ import annotations

from app.services.language_learning_goal import GOAL_KEY
from app.services.language_listening_challenge.constants import LESSON_CHALLENGE_KEY
from app.services.language_listening_confidence.constants import LESSON_CONFIDENCE_KEY
from app.services.language_listening_curriculum.memory import CURRICULUM_KEY
from app.services.language_listening_explainability.types import ExplainabilitySignals
from app.services.language_listening_intelligence import HISTORY_KEY

EXPECTED_SIGNALS: tuple[str, ...] = (
    "listening_intelligence",
    "listening_curriculum",
    "listening_learning_goal",
    "listening_confidence_lesson",
    "listening_challenge_lesson",
    "question_types",
    "cefr_level",
)


def _as_dict(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def extract_signals(
    body_json: dict | None,
    *,
    cefr_level: str = "",
    weak_skills: list[str] | None = None,
) -> ExplainabilitySignals:
    body = body_json or {}
    questions = body.get("questions") or []
    q_types: list[str] = []
    if isinstance(questions, list):
        for q in questions:
            if isinstance(q, dict):
                t = q.get("type")
                if isinstance(t, str) and t not in q_types:
                    q_types.append(t)

    level = cefr_level or str(
        _as_dict(body.get(HISTORY_KEY)).get("level")
        or body.get("level")
        or ""
    )

    return ExplainabilitySignals(
        intelligence=_as_dict(body.get(HISTORY_KEY)),
        curriculum=_as_dict(body.get(CURRICULUM_KEY)),
        goal=_as_dict(body.get(GOAL_KEY)),
        confidence_lesson=_as_dict(body.get(LESSON_CONFIDENCE_KEY)),
        challenge_lesson=_as_dict(body.get(LESSON_CHALLENGE_KEY)),
        question_types=tuple(q_types),
        cefr_level=level,
        weak_skills=tuple(weak_skills or ()),
    )


def top_score_factors(breakdown: dict[str, object], *, limit: int = 2) -> list[tuple[str, float]]:
    pairs: list[tuple[str, float]] = []
    for key, raw in breakdown.items():
        try:
            val = float(raw)
        except (TypeError, ValueError):
            continue
        if val > 0.05:
            pairs.append((key, val))
    pairs.sort(key=lambda x: x[1], reverse=True)
    return pairs[:limit]
