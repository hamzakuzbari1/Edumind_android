"""Pure Grammar Review scheduling engine (G2.3).

Deterministic. No LLM. No randomness. Never touches Progression unlock/current/next.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.services.language_grammar.enums import (
    GrammarMasteryState,
    GrammarReviewMode,
    GrammarReviewPriority,
    GrammarReviewReason,
)
from app.services.language_grammar.id_canon import normalize_grammar_id
from app.services.language_grammar_catalog.types import GrammarCatalogSnapshot, GrammarTopic
from app.services.language_grammar_mastery.types import GrammarMasteryRecord, GrammarMasterySnapshot
from app.services.language_grammar_review.types import (
    GRAMMAR_REVIEW_SCHEMA_VERSION,
    GrammarReviewHistoryEntry,
    GrammarReviewItem,
    GrammarReviewQueue,
    GrammarReviewSnapshot,
    GrammarReviewStudentState,
)

_PRIORITY_RANK: dict[GrammarReviewPriority, int] = {
    GrammarReviewPriority.critical: 0,
    GrammarReviewPriority.high: 1,
    GrammarReviewPriority.medium: 2,
    GrammarReviewPriority.low: 3,
}

# Early-pull thresholds (before calendar due) — retention crisis / confidence collapse.
_EARLY_RETENTION_MAX = 45.0
_EARLY_RETENTION_RISK_MIN = 70.0
_EARLY_CONFIDENCE_MAX = 35.0


class GrammarReviewError(ValueError):
    """Invalid review input or corrupted review state."""


def _parse_ts(value: str | None) -> datetime | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError as exc:
        raise GrammarReviewError(f"Invalid timestamp: {value}") from exc
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def format_ts(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_as_of(as_of: str | datetime) -> datetime:
    if isinstance(as_of, datetime):
        dt = as_of
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    parsed = _parse_ts(as_of)
    if parsed is None:
        raise GrammarReviewError("as_of is required")
    return parsed


def empty_student_state(*, student_id: int, language_id: int) -> GrammarReviewStudentState:
    return GrammarReviewStudentState(student_id=student_id, language_id=language_id)


def disabled_review_snapshot(
    *,
    student_id: int,
    language_id: int,
    as_of: str,
) -> GrammarReviewSnapshot:
    return GrammarReviewSnapshot(
        student_id=student_id,
        language_id=language_id,
        as_of=as_of,
        schedule=(),
        queue=GrammarReviewQueue(),
        enabled=False,
        schema_version=GRAMMAR_REVIEW_SCHEMA_VERSION,
    )


def _anchor_time(
    record: GrammarMasteryRecord,
    history: GrammarReviewHistoryEntry | None,
    *,
    as_of: datetime,
) -> datetime:
    for raw in (
        history.last_reviewed_at if history else None,
        record.last_seen_at,
        record.last_updated_at,
        record.introduced_at,
    ):
        parsed = _parse_ts(raw)
        if parsed is not None:
            return parsed
    return as_of


def _state_scale(state: GrammarMasteryState) -> float:
    if state is GrammarMasteryState.mastered:
        return 1.0
    if state is GrammarMasteryState.practicing:
        return 0.40
    if state is GrammarMasteryState.learning:
        return 0.18
    return 0.12


def _interval_days(
    record: GrammarMasteryRecord,
    topic: GrammarTopic,
    history: GrammarReviewHistoryEntry | None,
) -> float:
    half_life = max(0.5, float(topic.review_half_life_days))
    retention = float(record.dimensions.retention)
    confidence = float(record.confidence)
    stability = float(record.stability)

    retention_factor = 0.40 + (retention / 100.0) * 1.20
    confidence_factor = 0.50 + (confidence / 100.0) * 1.00
    stability_factor = 0.50 + (stability / 100.0) * 1.00

    min_ctx = max(1, int(topic.minimum_context_diversity))
    context_factor = 0.60 if record.distinct_context_count < min_ctx else 1.0

    review_count = int(history.review_count) if history else 0
    if review_count < 0:
        raise GrammarReviewError(f"Broken review state: negative review_count for {record.grammar_id}")
    history_factor = min(1.50, 1.0 + 0.05 * review_count)

    interval = (
        half_life
        * _state_scale(record.state)
        * retention_factor
        * confidence_factor
        * stability_factor
        * context_factor
        * history_factor
    )
    return max(0.25, min(60.0, interval))


def _context_gap(record: GrammarMasteryRecord, topic: GrammarTopic) -> float:
    min_ctx = max(1, int(topic.minimum_context_diversity))
    if record.distinct_context_count >= min_ctx:
        return 0.0
    return 100.0 * (1.0 - (record.distinct_context_count / min_ctx))


def _urgency_score(
    *,
    record: GrammarMasteryRecord,
    topic: GrammarTopic,
    due_at: datetime,
    as_of: datetime,
) -> float:
    overdue_days = max(0.0, (as_of - due_at).total_seconds() / 86400.0)
    overdue_norm = min(100.0, overdue_days * 20.0)
    catalog_boost = float(max(1, min(5, int(topic.review_priority))))
    # Higher catalog review_priority (5) => more urgent; invert 1..5 → 20..100 band contrib.
    catalog_norm = catalog_boost * 20.0
    gap = _context_gap(record, topic)

    score = (
        float(record.retention_risk) * 0.30
        + (100.0 - float(record.confidence)) * 0.22
        + (100.0 - float(record.stability)) * 0.18
        + overdue_norm * 0.18
        + gap * 0.07
        + catalog_norm * 0.05
    )
    return round(max(0.0, min(100.0, score)), 4)


def _priority_band(urgency: float, record: GrammarMasteryRecord) -> GrammarReviewPriority:
    if urgency >= 75.0 or record.dimensions.retention < 40.0 or record.retention_risk >= 80.0:
        return GrammarReviewPriority.critical
    if urgency >= 55.0:
        return GrammarReviewPriority.high
    if urgency >= 35.0:
        return GrammarReviewPriority.medium
    return GrammarReviewPriority.low


def _primary_reason(
    *,
    review_due: bool,
    due_at: datetime,
    as_of: datetime,
    record: GrammarMasteryRecord,
    topic: GrammarTopic,
) -> GrammarReviewReason:
    if as_of > due_at + timedelta(hours=1):
        return GrammarReviewReason.overdue
    if record.dimensions.retention < _EARLY_RETENTION_MAX:
        return GrammarReviewReason.low_retention
    if record.retention_risk >= _EARLY_RETENTION_RISK_MIN:
        return GrammarReviewReason.low_retention
    if record.confidence < _EARLY_CONFIDENCE_MAX:
        return GrammarReviewReason.low_confidence
    if record.stability < 40.0:
        return GrammarReviewReason.low_stability
    if _context_gap(record, topic) >= 50.0:
        return GrammarReviewReason.low_context_diversity
    # Stale: last seen more than 2x interval ago relative to as_of vs due
    if review_due and (as_of - due_at) >= timedelta(days=2):
        return GrammarReviewReason.stale_evidence
    if int(topic.review_priority) >= 5 and review_due:
        return GrammarReviewReason.catalog_priority
    if review_due:
        return GrammarReviewReason.due
    return GrammarReviewReason.due


def _recommended_mode(
    record: GrammarMasteryRecord,
    topic: GrammarTopic,
    reason: GrammarReviewReason,
) -> GrammarReviewMode:
    if reason in (GrammarReviewReason.low_retention, GrammarReviewReason.stale_evidence):
        return GrammarReviewMode.retention_check
    if reason is GrammarReviewReason.low_context_diversity or _context_gap(record, topic) >= 50.0:
        return GrammarReviewMode.context_transfer
    if (
        record.state is GrammarMasteryState.mastered
        and record.dimensions.retention >= 70.0
        and record.confidence >= 60.0
    ):
        return GrammarReviewMode.quick_recall
    return GrammarReviewMode.spaced_practice


def _should_queue(
    *,
    review_due: bool,
    record: GrammarMasteryRecord,
) -> bool:
    if review_due:
        return True
    if record.dimensions.retention < _EARLY_RETENTION_MAX:
        return True
    if record.retention_risk >= _EARLY_RETENTION_RISK_MIN:
        return True
    if record.confidence < _EARLY_CONFIDENCE_MAX:
        return True
    return False


def _schedule_one(
    record: GrammarMasteryRecord,
    *,
    topic: GrammarTopic,
    history: GrammarReviewHistoryEntry | None,
    as_of: datetime,
) -> GrammarReviewItem:
    anchor = _anchor_time(record, history, as_of=as_of)
    interval = _interval_days(record, topic, history)
    due_at = anchor + timedelta(days=interval)
    review_due = due_at <= as_of
    urgency = _urgency_score(record=record, topic=topic, due_at=due_at, as_of=as_of)
    # Early-pull items get urgency floor so they sort ahead of distant due items.
    if not review_due and _should_queue(review_due=False, record=record):
        urgency = max(urgency, 60.0)
        review_due_flag = True
    else:
        review_due_flag = review_due

    priority = _priority_band(urgency, record)
    reason = _primary_reason(
        review_due=review_due_flag,
        due_at=due_at,
        as_of=as_of,
        record=record,
        topic=topic,
    )
    mode = _recommended_mode(record, topic, reason)
    return GrammarReviewItem(
        grammar_id=record.grammar_id,
        due_at=format_ts(due_at),
        priority=priority,
        reason=reason,
        recommended_review_mode=mode,
        review_due=review_due_flag,
        urgency_score=urgency,
        retention_risk=float(record.retention_risk),
    )


def compute_review_snapshot(
    *,
    mastery: GrammarMasterySnapshot,
    student: GrammarReviewStudentState,
    catalog: GrammarCatalogSnapshot,
    as_of: str | datetime,
) -> GrammarReviewSnapshot:
    """Build full schedule + due queue from mastery + review history + catalog."""
    if mastery.student_id != student.student_id or mastery.language_id != student.language_id:
        raise GrammarReviewError("Mastery / review student-language mismatch")

    as_of_dt = parse_as_of(as_of)
    as_of_str = format_ts(as_of_dt)
    history_map = {h.grammar_id: h for h in student.history}

    schedule_items: list[GrammarReviewItem] = []
    seen: set[str] = set()

    for record in sorted(mastery.records, key=lambda r: r.grammar_id):
        gid = normalize_grammar_id(record.grammar_id)
        if not gid:
            raise GrammarReviewError("Empty grammar_id in mastery record")
        if gid in seen:
            raise GrammarReviewError(f"Duplicate mastery grammar_id: {gid}")
        seen.add(gid)

        topic = catalog.topic_by_id(gid)
        if topic is None:
            raise GrammarReviewError(f"Unknown grammar_id: {gid}")

        if record.evidence_count <= 0:
            continue

        item = _schedule_one(
            record,
            topic=topic,
            history=history_map.get(gid),
            as_of=as_of_dt,
        )
        schedule_items.append(item)

    # Stable deterministic queue ordering.
    queue_items = [i for i in schedule_items if i.review_due]
    queue_items.sort(
        key=lambda i: (
            _PRIORITY_RANK[i.priority],
            -i.urgency_score,
            i.due_at,
            i.grammar_id,
        )
    )

    # Reject duplicate queue entries (defensive — schedule already unique).
    qids = [i.grammar_id for i in queue_items]
    if len(qids) != len(set(qids)):
        raise GrammarReviewError("Duplicate review queue entries")

    return GrammarReviewSnapshot(
        student_id=student.student_id,
        language_id=student.language_id,
        as_of=as_of_str,
        schedule=tuple(schedule_items),
        queue=GrammarReviewQueue(items=tuple(queue_items)),
        enabled=True,
        schema_version=GRAMMAR_REVIEW_SCHEMA_VERSION,
    )


def record_review_completed(
    state: GrammarReviewStudentState,
    *,
    grammar_id: str,
    reviewed_at: str | datetime,
    mode: GrammarReviewMode,
    catalog: GrammarCatalogSnapshot,
) -> GrammarReviewStudentState:
    """Append / update durable review history for a topic. Does not unlock grammar."""
    gid = normalize_grammar_id(grammar_id)
    if catalog.topic_by_id(gid) is None:
        raise GrammarReviewError(f"Unknown grammar_id: {gid}")

    reviewed_dt = parse_as_of(reviewed_at)
    reviewed_str = format_ts(reviewed_dt)

    by_id = {h.grammar_id: h for h in state.history}
    prior = by_id.get(gid)
    count = (prior.review_count if prior else 0) + 1
    if count < 1:
        raise GrammarReviewError("Broken review state after completion")

    by_id[gid] = GrammarReviewHistoryEntry(
        grammar_id=gid,
        last_reviewed_at=reviewed_str,
        review_count=count,
        last_mode=mode,
    )
    history = tuple(by_id[k] for k in sorted(by_id))
    return GrammarReviewStudentState(
        student_id=state.student_id,
        language_id=state.language_id,
        history=history,
        schema_version=GRAMMAR_REVIEW_SCHEMA_VERSION,
    )
