"""Phase 2 — Error Intelligence Engine.

Tracks, aggregates and analyses recurring learner mistakes across ALL sessions. It REUSES the
corrections the conversation pipeline already produces (`evaluation_json.correction`) — each
error is normalized to a stable `pattern_key` and upserted into `LanguageErrorPattern`
(occurrence_count++ on recurrence). Reports power the weakness view and feed the Phase 1 learner
memory (recurring issues become "weak areas" in the prompt context).
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.language.error_pattern import LanguageErrorPattern

ALLOWED_ERROR_TYPES = {"grammar", "vocabulary", "pronunciation", "spelling", "punctuation"}
RECURRING_MIN = 3
RECENT_DAYS = 7
_WS = re.compile(r"\s+")


# --------------------------------------------------------------------------------------------------
# Pure helpers (no I/O — unit-tested directly)
# --------------------------------------------------------------------------------------------------
def normalize_form(value: str | None) -> str:
    """Lowercase, collapse whitespace, length-cap — the dedupe-friendly form of an error string."""
    s = (value or "").strip().lower()
    s = _WS.sub(" ", s)
    return s[:160]


def normalize_error_type(value: str | None) -> str:
    """Map a raw error type onto the allowed set (unknown / 'fluency' -> grammar)."""
    t = (value or "").strip().lower()
    return t if t in ALLOWED_ERROR_TYPES else "grammar"


def make_pattern_key(error_type: str, incorrect_form: str) -> str:
    """Stable dedupe key for one recurring mistake, capped to the column width (200)."""
    return f"{normalize_error_type(error_type)}:{normalize_form(incorrect_form)}"[:200]


def extract_errors_from_correction(correction: dict | None) -> list[dict]:
    """Turn a conversation correction payload into loggable error rows.

    The conversation schema gives {has_errors, original, corrected, errors:[{type, message, ...}]}.
    The recurring unit is the specific issue (the error message); we keep the corrected sentence and
    the original as context. Falls back to a single sentence-level row when errors[] is empty.
    """
    correction = correction or {}
    if not correction.get("has_errors"):
        return []
    original = (correction.get("original") or "").strip()
    corrected = (correction.get("corrected") or "").strip()
    out: list[dict] = []
    for e in correction.get("errors") or []:
        if not isinstance(e, dict):
            continue
        issue = (e.get("message") or e.get("hint_ar") or "").strip()
        if not issue:
            continue
        out.append(
            {
                "error_type": normalize_error_type(e.get("type")),
                "incorrect_form": issue[:500],
                "corrected_form": corrected[:500],
                "context_sentence": (original[:500] or None),
            }
        )
    if not out and original and corrected and original != corrected:
        out.append(
            {
                "error_type": "grammar",
                "incorrect_form": original[:500],
                "corrected_form": corrected[:500],
                "context_sentence": original[:500] or None,
            }
        )
    return out


def compute_trend(active_recent: int, total_recurring: int) -> str:
    """Coarse trend from how many recurring issues are still active recently."""
    if total_recurring <= 0:
        return "stable"
    ratio = active_recent / total_recurring
    if ratio >= 0.6:
        return "worsening"
    if ratio <= 0.2:
        return "improving"
    return "stable"


# --------------------------------------------------------------------------------------------------
# Persistence + analytics
# --------------------------------------------------------------------------------------------------
async def log_error(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
    error_type: str,
    incorrect_form: str,
    corrected_form: str = "",
    context_sentence: str | None = None,
) -> None:
    """Upsert one error pattern: increment occurrence_count + refresh recency on recurrence."""
    incorrect_form = (incorrect_form or "").strip()
    if not incorrect_form:
        return
    etype = normalize_error_type(error_type)
    key = make_pattern_key(etype, incorrect_form)
    now = datetime.now(timezone.utc)

    existing = (
        await db.execute(
            select(LanguageErrorPattern).where(
                LanguageErrorPattern.student_id == student_id,
                LanguageErrorPattern.language_id == language_id,
                LanguageErrorPattern.pattern_key == key,
            )
        )
    ).scalar_one_or_none()

    if existing is not None:
        existing.occurrence_count = int(existing.occurrence_count or 0) + 1
        existing.last_seen = now
        if corrected_form:
            existing.corrected_form = corrected_form
        if context_sentence:
            existing.context_sentence = context_sentence
        return

    db.add(
        LanguageErrorPattern(
            student_id=student_id,
            language_id=language_id,
            error_type=etype,
            pattern_key=key,
            incorrect_form=incorrect_form,
            corrected_form=corrected_form or "",
            context_sentence=context_sentence,
            occurrence_count=1,
            first_seen=now,
            last_seen=now,
        )
    )


async def log_correction(
    db: AsyncSession, *, student_id: int, language_id: int, correction: dict | None
) -> int:
    """Log every error in a conversation correction payload. Returns how many were logged."""
    rows = extract_errors_from_correction(correction)
    for r in rows:
        await log_error(
            db,
            student_id=student_id,
            language_id=language_id,
            error_type=r["error_type"],
            incorrect_form=r["incorrect_form"],
            corrected_form=r["corrected_form"],
            context_sentence=r["context_sentence"],
        )
    return len(rows)


def _to_dict(p: LanguageErrorPattern) -> dict:
    return {
        "error_type": p.error_type,
        "incorrect_form": p.incorrect_form,
        "corrected_form": p.corrected_form,
        "context_sentence": p.context_sentence,
        "occurrence_count": int(p.occurrence_count or 0),
        "first_seen": p.first_seen,
        "last_seen": p.last_seen,
    }


async def get_top_errors(
    db: AsyncSession, *, student_id: int, language_id: int, limit: int = 10
) -> list[dict]:
    rows = (
        await db.execute(
            select(LanguageErrorPattern)
            .where(
                LanguageErrorPattern.student_id == student_id,
                LanguageErrorPattern.language_id == language_id,
            )
            .order_by(
                LanguageErrorPattern.occurrence_count.desc(),
                LanguageErrorPattern.last_seen.desc(),
            )
            .limit(limit)
        )
    ).scalars().all()
    return [_to_dict(p) for p in rows]


async def get_recurring_errors(
    db: AsyncSession, *, student_id: int, language_id: int, min_occurrences: int = RECURRING_MIN
) -> list[dict]:
    rows = (
        await db.execute(
            select(LanguageErrorPattern)
            .where(
                LanguageErrorPattern.student_id == student_id,
                LanguageErrorPattern.language_id == language_id,
                LanguageErrorPattern.occurrence_count >= min_occurrences,
            )
            .order_by(LanguageErrorPattern.occurrence_count.desc())
        )
    ).scalars().all()
    return [_to_dict(p) for p in rows]


async def top_issue_labels(
    db: AsyncSession, *, student_id: int, language_id: int, limit: int = 3, min_occurrences: int = RECURRING_MIN
) -> list[str]:
    """Short labels of the most recurring issues — for the Phase 1 memory weakness context."""
    recurring = await get_recurring_errors(
        db, student_id=student_id, language_id=language_id, min_occurrences=min_occurrences
    )
    return [r["incorrect_form"] for r in recurring[:limit] if r.get("incorrect_form")]


async def generate_weakness_report(
    db: AsyncSession, *, student_id: int, language_id: int
) -> dict:
    """Grouped top errors + most-recurring + recommended focus + trend."""
    rows = (
        await db.execute(
            select(LanguageErrorPattern)
            .where(
                LanguageErrorPattern.student_id == student_id,
                LanguageErrorPattern.language_id == language_id,
            )
            .order_by(LanguageErrorPattern.occurrence_count.desc())
        )
    ).scalars().all()

    by_type: dict[str, list[dict]] = {"grammar": [], "vocabulary": [], "pronunciation": []}
    recurring = 0
    active_recent = 0
    cutoff = datetime.now(timezone.utc) - timedelta(days=RECENT_DAYS)
    for p in rows:
        bucket = p.error_type if p.error_type in by_type else "grammar"
        by_type[bucket].append(_to_dict(p))
        if int(p.occurrence_count or 0) >= RECURRING_MIN:
            recurring += 1
            last = p.last_seen
            if last is not None:
                if last.tzinfo is None:
                    last = last.replace(tzinfo=timezone.utc)
                if last >= cutoff:
                    active_recent += 1

    most_recurring = _to_dict(rows[0]) if rows else None
    return {
        "top_grammar_errors": by_type["grammar"][:5],
        "top_vocabulary_errors": by_type["vocabulary"][:5],
        "top_pronunciation_errors": by_type["pronunciation"][:5],
        "most_recurring": most_recurring,
        "recommended_focus": (most_recurring or {}).get("incorrect_form") if most_recurring else "",
        "trend": compute_trend(active_recent, recurring),
    }
