"""Placement question-bank selection helpers.

This is the foundation for the smarter placement flow: reviewed bank items first,
boundary items when the engine is uncertain, and live AI generation only as a later fallback.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.language.enums import LanguageLevel
from app.models.language.question_bank import LanguagePlacementQuestionBankItem


PLACEMENT_BANK_SKILLS = frozenset(
    {
        "reading",
        "listening",
        "grammar_vocab",
        "writing_prompt",
        "speaking_prompt",
    }
)

_CEFR_ORDER = [
    LanguageLevel.A1,
    LanguageLevel.A2,
    LanguageLevel.B1,
    LanguageLevel.B2,
    LanguageLevel.C1,
    LanguageLevel.C2,
]


@dataclass(frozen=True)
class BoundaryTarget:
    low: LanguageLevel
    high: LanguageLevel


def normalize_bank_skill(skill: str) -> str:
    normalized = (skill or "").strip().lower().replace("-", "_")
    if normalized not in PLACEMENT_BANK_SKILLS:
        raise ValueError(f"Unsupported placement-bank skill: {skill!r}")
    return normalized


def normalize_level(level: LanguageLevel | str) -> LanguageLevel:
    if isinstance(level, LanguageLevel):
        return level
    return LanguageLevel(str(level).strip().upper())


def cefr_rank(level: LanguageLevel | str) -> int:
    normalized = normalize_level(level)
    return _CEFR_ORDER.index(normalized)


def boundary_between(a: LanguageLevel | str, b: LanguageLevel | str) -> BoundaryTarget | None:
    first = normalize_level(a)
    second = normalize_level(b)
    first_rank = cefr_rank(first)
    second_rank = cefr_rank(second)
    if abs(first_rank - second_rank) != 1:
        return None
    low, high = (first, second) if first_rank < second_rank else (second, first)
    return BoundaryTarget(low=low, high=high)


def adjacent_boundary(level: LanguageLevel | str, *, upward: bool) -> BoundaryTarget | None:
    rank = cefr_rank(level)
    neighbor_rank = rank + (1 if upward else -1)
    if neighbor_rank < 0 or neighbor_rank >= len(_CEFR_ORDER):
        return None
    return boundary_between(_CEFR_ORDER[rank], _CEFR_ORDER[neighbor_rank])


async def select_placement_bank_items(
    db: AsyncSession,
    *,
    language_id: int,
    skill: str,
    level: LanguageLevel | str,
    count: int = 2,
    used_item_ids: Iterable[int] | None = None,
    boundary: BoundaryTarget | tuple[LanguageLevel | str, LanguageLevel | str] | None = None,
    subskills: Sequence[str] | None = None,
    require_verified: bool = True,
    require_mvp_marker: bool = False,
    exclude_subskills: Sequence[str] | None = None,
    allow_gap_fill: bool = False,
) -> list[LanguagePlacementQuestionBankItem]:
    """Select reviewed placement items, preferring boundary items when requested.

    The function intentionally returns ORM rows instead of API schemas so the future exam
    flow can store internal fields like correct_index without exposing them to the frontend.

    require_mvp_marker: speaking-placement-only gate (only ever passed True by
    _speaking_bank_prompt in language_exam.py). When set, restricts results to items whose
    body_json marks them as the curated MVP speaking bank
    (review_status="mvp_approved_pending_full_review", human_reviewed=false) -- this excludes
    older/legacy speaking_prompt rows that predate that bank (seeded by the generic
    seed_placement_question_bank.py script) without deleting or deactivating them. Has no effect
    on reading/listening/grammar_vocab/writing_prompt, which never pass this flag.

    exclude_subskills: speaking-placement-only diversity preference (only ever passed by
    _speaking_bank_prompt, as a soft preference -- callers re-query without it if this returns
    nothing). Excludes items whose subskill/task_type is in the given list. Has no effect on
    reading/listening/grammar_vocab/writing_prompt, which never pass this.

    allow_gap_fill: durable, code-level guard -- defaults closed. When False (every existing
    caller today), question_type="gap_fill" rows are excluded even if is_active/is_verified in the
    database -- every other question_type (mcq, speaking_prompt, writing_prompt, ...) is
    unaffected. This is intentionally independent of is_active, since is_active alone was never
    meant to be the only thing preventing an unsupported question type
    (e.g. Gap Fill, before frontend rendering exists) from reaching a student. Only pass True once
    the caller's frontend/answer-handling can actually support the returned question_type.
    """

    normalized_skill = normalize_bank_skill(skill)
    normalized_level = normalize_level(level)
    limit = max(1, int(count or 1))
    exclude_ids = {int(x) for x in (used_item_ids or []) if x is not None}
    wanted_subskills = [s for s in (subskills or []) if s]
    unwanted_subskills = [s for s in (exclude_subskills or []) if s]

    boundary_target: BoundaryTarget | None
    if isinstance(boundary, BoundaryTarget) or boundary is None:
        boundary_target = boundary
    else:
        boundary_target = boundary_between(boundary[0], boundary[1])

    async def _fetch(*, boundary_only: bool) -> list[LanguagePlacementQuestionBankItem]:
        stmt = (
            select(LanguagePlacementQuestionBankItem)
            .where(
                LanguagePlacementQuestionBankItem.language_id == language_id,
                LanguagePlacementQuestionBankItem.skill == normalized_skill,
                LanguagePlacementQuestionBankItem.is_active.is_(True),
            )
            .order_by(LanguagePlacementQuestionBankItem.usage_count.asc(), func.random())
            .limit(limit - len(selected))
        )
        if require_verified:
            stmt = stmt.where(LanguagePlacementQuestionBankItem.is_verified.is_(True))
        if not allow_gap_fill:
            stmt = stmt.where(LanguagePlacementQuestionBankItem.question_type != "gap_fill")
        if require_mvp_marker:
            stmt = stmt.where(
                LanguagePlacementQuestionBankItem.body_json["review_status"].astext
                == "mvp_approved_pending_full_review",
                LanguagePlacementQuestionBankItem.body_json["human_reviewed"].astext == "false",
            )
        if exclude_ids:
            stmt = stmt.where(LanguagePlacementQuestionBankItem.id.not_in(exclude_ids))
        if wanted_subskills:
            stmt = stmt.where(LanguagePlacementQuestionBankItem.subskill.in_(wanted_subskills))
        if unwanted_subskills:
            stmt = stmt.where(LanguagePlacementQuestionBankItem.subskill.not_in(unwanted_subskills))

        if boundary_only and boundary_target:
            stmt = stmt.where(
                LanguagePlacementQuestionBankItem.boundary_low_level == boundary_target.low,
                LanguagePlacementQuestionBankItem.boundary_high_level == boundary_target.high,
            )
        else:
            stmt = stmt.where(LanguagePlacementQuestionBankItem.level == normalized_level)

        return list((await db.execute(stmt)).scalars().all())

    selected: list[LanguagePlacementQuestionBankItem] = []

    if boundary_target:
        for row in await _fetch(boundary_only=True):
            selected.append(row)
            exclude_ids.add(row.id)
            if len(selected) >= limit:
                return selected

    for row in await _fetch(boundary_only=False):
        selected.append(row)
        exclude_ids.add(row.id)
        if len(selected) >= limit:
            break

    return selected


def bank_item_to_exam_item(item: LanguagePlacementQuestionBankItem) -> dict:
    """Convert a bank item into the internal dict shape used by the placement exam state."""

    options = item.options_json if isinstance(item.options_json, list) else []
    body = item.body_json or {}
    content_item_id = body.get("content_item_id")
    try:
        content_item_id = int(content_item_id) if content_item_id is not None else None
    except (TypeError, ValueError):
        content_item_id = None
    return {
        "bank_item_id": item.id,
        "content_id": content_item_id,
        "audio_url": (item.audio_meta_json or {}).get("public_url"),
        "level": item.level.value,
        "boundary": (
            f"{item.boundary_low_level.value}/{item.boundary_high_level.value}"
            if item.boundary_low_level and item.boundary_high_level
            else ""
        ),
        "skill": item.skill,
        "subskill": item.subskill or "",
        "question_type": item.question_type,
        # Gap Fill only (question_type == "gap_fill"); absent/default for every current MCQ row.
        # Kept private -- _build_state_out never surfaces these to the public exam state.
        "accepted_answers": body.get("accepted_answers"),
        "max_words": body.get("max_words"),
        "case_sensitive": body.get("case_sensitive", False),
        # Gap Fill only, display-only -- unlike the three fields above, this one IS surfaced to
        # the public exam state (McqPromptOut.word_bank) since it carries no scoring information.
        "word_bank": body.get("word_bank"),
        # Listening bundles only (Phase 6). MCQ bundle: subquestions (each with its own
        # correct_index, kept private). Gap Fill bundle: note_template (display-only) + blanks
        # (each with accepted_answers/max_words/case_sensitive, kept private).
        "subquestions": body.get("subquestions"),
        "note_template": body.get("note_template"),
        "blanks": body.get("blanks"),
        "passage": item.passage or "",
        "situation": item.situation or "",
        "question": item.prompt_text,
        "options": list(options),
        "correct_index": item.correct_index,
        "explanation": item.explanation or "",
        "media_object_id": item.media_object_id,
        "audio_meta": item.audio_meta_json or {},
        "body": body,
    }


async def record_bank_item_answer(db: AsyncSession, *, item_id: int, correct: bool) -> None:
    """Increment coarse calibration counters after a placement answer.

    The caller owns commit/rollback so this can be used inside a larger exam transaction.
    """

    values = {
        "usage_count": LanguagePlacementQuestionBankItem.usage_count + 1,
    }
    if correct:
        values["correct_count"] = LanguagePlacementQuestionBankItem.correct_count + 1

    await db.execute(
        update(LanguagePlacementQuestionBankItem)
        .where(LanguagePlacementQuestionBankItem.id == item_id)
        .values(**values)
    )


async def fetch_bank_item_metadata(db: AsyncSession, item_ids: Iterable[int]) -> dict[int, dict]:
    """Read-only lookup of body_json for a specific set of bank item ids (e.g. review_status /
    expected_response_seconds needed to build report-time evidence summaries). Never mutates
    rows. Missing/deleted ids are simply absent from the returned mapping -- callers must handle
    that safely rather than assuming every id resolves."""
    ids = {int(x) for x in item_ids if x is not None}
    if not ids:
        return {}
    rows = (
        await db.execute(
            select(LanguagePlacementQuestionBankItem.id, LanguagePlacementQuestionBankItem.body_json).where(
                LanguagePlacementQuestionBankItem.id.in_(ids)
            )
        )
    ).all()
    return {row.id: (row.body_json or {}) for row in rows}
