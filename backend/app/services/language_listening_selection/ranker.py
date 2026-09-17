"""Deterministic listening lesson ranking (Phase 2.2).

Ranking order (ascending — lower wins):
1. Weakest Objective coverage match
2. Review Priority
3. Curriculum Priority (higher recommendation_score first)
4. Oldest Candidate
5. Difficulty Match (normal before stretch)
6. Stable tie-breaker (content_item.id ASC)
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.models.language.content import LanguageContentItem
from app.services.language_listening_confidence.types import ConfidenceState


@dataclass(frozen=True, slots=True)
class ListeningCandidateRank:
    content_item_id: int
    weakest_objective_coverage: float
    review_priority: int
    curriculum_priority: float
    oldest_key: float
    difficulty_rank: int
    tie_breaker_id: int

    def sort_key(self) -> tuple[float, int, float, float, int, int]:
        return (
            self.weakest_objective_coverage,
            self.review_priority,
            -self.curriculum_priority,
            self.oldest_key,
            self.difficulty_rank,
            self.tie_breaker_id,
        )


def _body_dict(item: LanguageContentItem) -> dict:
    return item.body_json if isinstance(item.body_json, dict) else {}


def _weakest_objective_coverage(body: dict, confidence: ConfidenceState | None) -> float:
    cur = body.get("listening_curriculum") if isinstance(body.get("listening_curriculum"), dict) else {}
    objectives = [str(o) for o in (cur.get("objectives") or []) if o]
    if not objectives:
        skill_focus = [str(s) for s in (cur.get("skill_focus") or []) if s]
        objectives = skill_focus
    if not objectives:
        return 1.0
    coverages: list[float] = []
    for oid in objectives:
        if confidence and oid in confidence.objectives:
            coverages.append(float(confidence.objectives[oid].coverage_score))
        else:
            coverages.append(0.0)
    return min(coverages) if coverages else 1.0


def _review_priority(body: dict) -> int:
    cur = body.get("listening_curriculum") if isinstance(body.get("listening_curriculum"), dict) else {}
    intent = str(cur.get("lesson_intent") or "")
    review_objs = cur.get("review_objectives") or []
    if intent == "review" or (isinstance(review_objs, list) and len(review_objs) > 0):
        return 0
    return 1


def _curriculum_priority(body: dict) -> float:
    cur = body.get("listening_curriculum") if isinstance(body.get("listening_curriculum"), dict) else {}
    try:
        return float(cur.get("recommendation_score") or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _oldest_key(item: LanguageContentItem) -> float:
    created: datetime | None = item.created_at
    if created is not None:
        return created.timestamp()
    return float(item.sort_order or 0)


def _difficulty_rank(body: dict) -> int:
    ch = body.get("listening_challenge_lesson") if isinstance(body.get("listening_challenge_lesson"), dict) else {}
    level = str(ch.get("challenge_level") or "normal").lower()
    if level in ("normal", ""):
        return 0
    return 1


def rank_listening_candidate(
    item: LanguageContentItem,
    *,
    confidence: ConfidenceState | None,
) -> ListeningCandidateRank:
    body = _body_dict(item)
    return ListeningCandidateRank(
        content_item_id=int(item.id),
        weakest_objective_coverage=_weakest_objective_coverage(body, confidence),
        review_priority=_review_priority(body),
        curriculum_priority=_curriculum_priority(body),
        oldest_key=_oldest_key(item),
        difficulty_rank=_difficulty_rank(body),
        tie_breaker_id=int(item.id),
    )


def select_best_candidate(
    items: list[LanguageContentItem],
    *,
    confidence: ConfidenceState | None,
) -> LanguageContentItem | None:
    if not items:
        return None
    ranked = sorted(
        items,
        key=lambda it: rank_listening_candidate(it, confidence=confidence).sort_key(),
    )
    return ranked[0]
