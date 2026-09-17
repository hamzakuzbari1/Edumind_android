"""Gather writing progression signals from persisted state."""

from __future__ import annotations

from statistics import mean

from app.services.language_writing_learning_stage.types import WritingSignalSnapshot
from app.services.language_writing_progression.storage import writing_state_from_payload


def _avg_mastery(mastery: dict) -> float:
    # No evidence yet -> low baseline (readiness must reflect real evidence, not
    # an optimistic default).
    if not mastery:
        return 0.3
    vals = [float(v) for v in mastery.values() if v is not None]
    return mean(vals) if vals else 0.3


def _revision_quality(history: list) -> float:
    scores: list[float] = []
    for h in history[-10:]:
        if not isinstance(h, dict):
            continue
        total = int(h.get("criteria_total") or 0)
        met = int(h.get("criteria_met") or 0)
        if total <= 0:
            continue
        base = met / total
        rev = int(h.get("revision_count") or 1)
        bonus = min(0.15, max(0, (rev - 1) * 0.05))
        scores.append(min(1.0, base + bonus))
    return mean(scores) if scores else 0.25


def _confidence(history: list) -> tuple[float, float]:
    vals: list[float] = []
    for h in history[-8:]:
        if not isinstance(h, dict):
            continue
        if h.get("confidence") is not None:
            vals.append(float(h["confidence"]))
        elif h.get("criteria_total"):
            vals.append(int(h.get("criteria_met") or 0) / max(int(h["criteria_total"]), 1))
    if not vals:
        return 0.3, 0.0
    avg = mean(vals)
    trend = (vals[-1] - vals[0]) / max(len(vals) - 1, 1) if len(vals) >= 2 else 0.0
    return avg, trend


def _stability(history: list) -> float:
    scores: list[float] = []
    for h in history[-8:]:
        if not isinstance(h, dict):
            continue
        total = int(h.get("criteria_total") or 0)
        met = int(h.get("criteria_met") or 0)
        if total > 0:
            scores.append(met / total)
    if len(scores) < 3:
        # Not enough completed lessons to establish stability.
        return 0.35
    m = mean(scores)
    var = sum((s - m) ** 2 for s in scores) / len(scores)
    return max(0.0, min(1.0, 1.0 - var * 4.0))


def _history_score_avg(history: list, key: str, *, default: float) -> float:
    """Mean of a continuous per-lesson score across the recent window.

    Backward compatible: entries persisted before enrichment lack the key and are
    skipped; falls back to the criteria ratio when no scored entries exist.
    """
    vals: list[float] = []
    for h in history[-8:]:
        if not isinstance(h, dict):
            continue
        v = h.get(key)
        if v is not None:
            try:
                vals.append(max(0.0, min(1.0, float(v))))
            except (TypeError, ValueError):
                continue
    if vals:
        return mean(vals)
    # Fallback to criteria ratio (older entries).
    ratios: list[float] = []
    for h in history[-8:]:
        if not isinstance(h, dict):
            continue
        total = int(h.get("criteria_total") or 0)
        if total > 0:
            ratios.append(int(h.get("criteria_met") or 0) / total)
    return mean(ratios) if ratios else default


def _cefr_alignment(history: list) -> float:
    """How well recent drafts match the target CEFR band.

    Uses the persisted per-lesson `cefr_alignment` value (1.0 = at/above band,
    lower = below band). Repeatedly performing below the official CEFR keeps this
    low so readiness cannot falsely climb.
    """
    vals: list[float] = []
    for h in history[-8:]:
        if not isinstance(h, dict):
            continue
        v = h.get("cefr_alignment")
        if v is not None:
            try:
                vals.append(max(0.0, min(1.0, float(v))))
            except (TypeError, ValueError):
                continue
    return mean(vals) if vals else 0.4


def _repeated_mistake_ratio(state: dict) -> float:
    """Penalty signal (0 = none, 1 = many) for mistakes recurring across lessons."""
    memory = state.get("coach_memory") or {}
    mistakes = memory.get("repeated_mistakes") or []
    if not isinstance(mistakes, list) or not mistakes:
        return 0.0
    recurring = 0
    for m in mistakes:
        if isinstance(m, dict) and int(m.get("occurrence_count") or 0) >= 2:
            recurring += 1
    return max(0.0, min(1.0, recurring / 4.0))


def gather_writing_signals_from_state(
    state: dict,
    *,
    official_cefr: str,
) -> WritingSignalSnapshot:
    """Pure signal gather — lesson count is exposure only, not stage driver."""
    grammar_avg = _avg_mastery(state.get("grammar_mastery") or {})
    vocab_avg = _avg_mastery(state.get("vocabulary_mastery") or {})
    history = list(state.get("lesson_history") or [])
    lesson_index = int(state.get("lessons_completed_count") or len(history))
    revision_q = _revision_quality(history)
    conf_avg, conf_trend = _confidence(history)
    completed = len(state.get("completed_node_ids") or [])
    target_nodes = max(4, lesson_index // 2 + 2)
    evidence = min(1.0, completed / target_nodes)
    weak = len(state.get("weak_skills") or [])
    task_response = _history_score_avg(history, "task_response_score", default=0.3)
    organization = _history_score_avg(history, "organization_score", default=0.3)
    cefr_alignment = _cefr_alignment(history)
    repeated = _repeated_mistake_ratio(state)
    return WritingSignalSnapshot(
        official_cefr=official_cefr.upper(),
        grammar_mastery_avg=grammar_avg,
        vocabulary_mastery_avg=vocab_avg,
        revision_quality_avg=revision_q,
        confidence_avg=max(0.0, min(1.0, conf_avg + conf_trend * 0.25)),
        confidence_trend=conf_trend,
        evidence_coverage_avg=evidence,
        recent_stability=_stability(history),
        lesson_index=lesson_index,
        completed_nodes=completed,
        pending_weak_skills=weak,
        task_response_avg=task_response,
        organization_avg=organization,
        cefr_alignment_avg=cefr_alignment,
        repeated_mistake_ratio=repeated,
    )


def gather_writing_signals(payload: dict | None, *, official_cefr: str) -> WritingSignalSnapshot:
    return gather_writing_signals_from_state(writing_state_from_payload(payload), official_cefr=official_cefr)
