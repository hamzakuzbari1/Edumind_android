"""Evidence model and coverage algorithms (Phase 3.2.1)."""

from __future__ import annotations

from app.services.language_listening_confidence.constants import (
    COVERAGE_AXIS_WEIGHTS,
    DIFFICULTY_EVIDENCE_DIMS,
    FORMAT_EVIDENCE_DIMS,
    MASTERY_SCORE_THRESHOLD,
    MIN_COVERAGE_FOR_MASTERY,
    SPEAKER_EVIDENCE_DIMS,
    SPEED_EVIDENCE_DIMS,
    TOPIC_EVIDENCE_DIMS,
)
from app.services.language_listening_confidence.types import (
    LessonConfidenceContext,
    ObjectiveConfidenceRecord,
    ObjectiveEvidenceRecord,
)

PACE_TO_SPEED: dict[str, str] = {
    "slow_clear": "slow",
    "conversational": "normal",
    "brisk_informative": "fast",
    "dynamic_multi_speaker": "fast",
}

CATEGORY_ALIASES: dict[str, str] = {
    "travel": "travel",
    "business": "business",
    "education": "education",
    "health": "health",
    "technology": "technology",
    "daily_life": "daily_life",
    "customer_service": "customer_service",
    "news": "announcements",
    "culture": "museum",
    "entertainment": "daily_life",
    "environment": "education",
    "public_services": "announcements",
}


def _axis_coverage(seen: dict[str, int], dimensions: tuple[str, ...]) -> float:
    if not dimensions:
        return 0.0
    hits = sum(1 for dim in dimensions if seen.get(dim, 0) > 0)
    return hits / len(dimensions)


def compute_coverage_score(evidence: ObjectiveEvidenceRecord) -> float:
    """Diversity-weighted coverage across evidence axes (0–1)."""
    axes = {
        "difficulty": _axis_coverage(evidence.difficulty, DIFFICULTY_EVIDENCE_DIMS),
        "format": _axis_coverage(evidence.formats, FORMAT_EVIDENCE_DIMS),
        "topic": _axis_coverage(evidence.topics, TOPIC_EVIDENCE_DIMS),
        "speaker": _axis_coverage(evidence.speakers, SPEAKER_EVIDENCE_DIMS),
        "speed": _axis_coverage(evidence.speed, SPEED_EVIDENCE_DIMS),
    }
    total_weight = sum(COVERAGE_AXIS_WEIGHTS.values()) or 1.0
    return round(
        sum(COVERAGE_AXIS_WEIGHTS[k] * axes[k] for k in COVERAGE_AXIS_WEIGHTS) / total_weight,
        4,
    )


def compute_mastery_score(confidence: float, coverage: float) -> float:
    return round(confidence * coverage, 4)


def is_evidence_mastered(confidence: float, coverage: float) -> bool:
    mastery = compute_mastery_score(confidence, coverage)
    return mastery >= MASTERY_SCORE_THRESHOLD and coverage >= MIN_COVERAGE_FOR_MASTERY


def normalize_difficulty_evidence(difficulty_band: str, narrative_format: str) -> tuple[str, ...]:
    band = (difficulty_band or "normal").lower()
    fmt = (narrative_format or "").lower()
    keys: list[str] = []
    if band == "easy":
        keys.append("easy")
    elif band == "challenging":
        keys.append("hard")
        if fmt in {"lecture", "news", "panel", "discussion"}:
            keys.append("exam")
    else:
        keys.append("normal")
    return tuple(dict.fromkeys(keys))


def normalize_format_evidence(narrative_format: str, format_hint: str) -> str:
    fmt = (narrative_format or format_hint or "monologue").lower()
    if fmt == "announcement":
        return "news"
    if fmt in FORMAT_EVIDENCE_DIMS:
        return fmt
    return "monologue"


def normalize_topic_evidence(category: str, situation: str) -> str:
    cat = CATEGORY_ALIASES.get((category or "").lower(), "")
    if cat in TOPIC_EVIDENCE_DIMS:
        return cat
    sit = (situation or "").lower()
    if sit in {"airport", "hotel", "restaurant", "travel"}:
        return "travel"
    if sit in {"meeting", "office"}:
        return "meetings"
    if sit in {"lecture", "school"}:
        return "education"
    if sit in {"doctor"}:
        return "health"
    if sit in {"museum"}:
        return "museum"
    if sit in {"public_announcement"}:
        return "announcements"
    if sit in {"customer_support"}:
        return "customer_service"
    return "daily_life"


def normalize_speaker_evidence(speaker_count: int) -> str:
    if speaker_count >= 3:
        return "multi"
    if speaker_count == 2:
        return "two"
    return "single"


def normalize_speed_evidence(pace: str) -> str:
    return PACE_TO_SPEED.get((pace or "").lower(), "normal")


def _bump(bucket: dict[str, int], key: str) -> None:
    if key:
        bucket[key] = bucket.get(key, 0) + 1


def record_evidence(
    record: ObjectiveConfidenceRecord,
    ctx: LessonConfidenceContext,
    *,
    outcome_signal: float,
) -> None:
    """Record evidence only on successful demonstration (no fake evidence)."""
    if outcome_signal < 0.5:
        return

    ev = record.evidence
    for diff in normalize_difficulty_evidence(ctx.difficulty_band, ctx.narrative_format):
        _bump(ev.difficulty, diff)
    _bump(ev.formats, normalize_format_evidence(ctx.narrative_format, ctx.format_hint))
    _bump(ev.topics, normalize_topic_evidence(ctx.category, ctx.situation))
    _bump(ev.speakers, normalize_speaker_evidence(ctx.speaker_count))
    _bump(ev.speed, normalize_speed_evidence(ctx.pace))


def record_evidence_from_lesson(
    state,
    ctx: LessonConfidenceContext,
    question_results: list[dict],
    *,
    objective_signals: dict[str, float] | None = None,
) -> None:
    """Record evidence for objectives with successful outcomes — separate from confidence update."""
    from app.services.language_listening_confidence.update import _objectives_from_question_results

    signals = objective_signals or _objectives_from_question_results(question_results, ctx.lesson_objectives)
    overall = (
        sum(1 for r in question_results if r.get("is_correct")) / max(1, len(question_results))
        if question_results
        else 0.0
    )
    involved = set(ctx.lesson_objectives) | set(ctx.skill_focus)
    for oid in involved:
        rec = state.objectives.get(oid)
        if rec is None:
            continue
        signal = signals.get(oid, overall)
        record_evidence(rec, ctx, outcome_signal=signal)


def missing_evidence(record: ObjectiveConfidenceRecord) -> dict[str, list[str]]:
    ev = record.evidence
    missing: dict[str, list[str]] = {}
    for dim in DIFFICULTY_EVIDENCE_DIMS:
        if ev.difficulty.get(dim, 0) == 0:
            missing.setdefault("difficulty", []).append(dim)
    for dim in FORMAT_EVIDENCE_DIMS:
        if ev.formats.get(dim, 0) == 0:
            missing.setdefault("format", []).append(dim)
    for dim in TOPIC_EVIDENCE_DIMS:
        if ev.topics.get(dim, 0) == 0:
            missing.setdefault("topic", []).append(dim)
    for dim in SPEAKER_EVIDENCE_DIMS:
        if ev.speakers.get(dim, 0) == 0:
            missing.setdefault("speaker", []).append(dim)
    for dim in SPEED_EVIDENCE_DIMS:
        if ev.speed.get(dim, 0) == 0:
            missing.setdefault("speed", []).append(dim)
    return missing


def objectives_needing_evidence(state, *, confidence_min: float = 0.70, coverage_max: float = 0.55) -> list[str]:
    out: list[str] = []
    for oid, rec in state.objectives.items():
        cov = compute_coverage_score(rec.evidence)
        if rec.confidence >= confidence_min and cov < coverage_max:
            out.append(oid)
    return out


def plan_evidence_fill_score(
    *,
    narrative_format: str,
    format_hint: str,
    category: str,
    situation: str,
    difficulty_band: str,
    speaker_count: int,
    pace: str,
    target_objectives: tuple[str, ...],
    state,
) -> float:
    """Score how well a plan fills missing evidence for high-confidence objectives."""
    if not target_objectives:
        return 0.5

    fmt = normalize_format_evidence(narrative_format, format_hint)
    topic = normalize_topic_evidence(category, situation)
    speaker = normalize_speaker_evidence(speaker_count)
    speed = normalize_speed_evidence(pace)
    diffs = set(normalize_difficulty_evidence(difficulty_band, narrative_format))

    fills = 0.0
    checks = 0.0
    for oid in target_objectives:
        rec = state.objectives.get(oid)
        if rec is None or rec.confidence < 0.65:
            continue
        gaps = missing_evidence(rec)
        if not gaps:
            continue
        if fmt in gaps.get("format", []):
            fills += 1.0
        checks += 1.0
        if topic in gaps.get("topic", []):
            fills += 0.85
        checks += 0.85
        if speaker in gaps.get("speaker", []):
            fills += 0.6
        checks += 0.6
        if speed in gaps.get("speed", []):
            fills += 0.5
        checks += 0.5
        for d in diffs:
            if d in gaps.get("difficulty", []):
                fills += 0.7
                checks += 0.7

    if checks <= 0:
        return 0.5
    return round(min(1.0, 0.35 + (fills / checks) * 0.65), 4)


def coverage_breakdown(evidence: ObjectiveEvidenceRecord) -> dict[str, float]:
    return {
        "difficulty": round(_axis_coverage(evidence.difficulty, DIFFICULTY_EVIDENCE_DIMS), 4),
        "format": round(_axis_coverage(evidence.formats, FORMAT_EVIDENCE_DIMS), 4),
        "topic": round(_axis_coverage(evidence.topics, TOPIC_EVIDENCE_DIMS), 4),
        "speaker": round(_axis_coverage(evidence.speakers, SPEAKER_EVIDENCE_DIMS), 4),
        "speed": round(_axis_coverage(evidence.speed, SPEED_EVIDENCE_DIMS), 4),
    }
