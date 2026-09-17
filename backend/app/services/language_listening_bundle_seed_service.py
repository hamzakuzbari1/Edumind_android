"""Phase 6C (dry-run parse/validate) and apply-implementation (not yet run) of the bundled
Listening seed pipeline.

Parses and validates backend/content_drafts/listening_bundles_v1_draft.md -- 30 Listening task
bundles (18 MCQ bundles of 3 subquestions each, 12 Gap Fill / note-completion bundles of 3 blanks
each) -- and builds in-memory candidate rows for LanguagePlacementQuestionBankItem
(build_dry_run_summary()). This path never opens a database session and never writes anything.

apply_seed_batch() adds the actual DB insert/update path, used only when a caller explicitly
passes a real AsyncSession and apply=True. It is idempotent by stable_key
("listening_bundles_v1:<draft_id>"), following the exact same safety pattern already proven by
language_listening_bank_seed_service.py (the earlier, single-question batch, kept unmodified and
untouched by this file): a stable_key match updates content fields only and never resets
is_active/is_verified; a brand-new row is inserted with is_active=False, is_verified=False,
source="listening_bundles_v1_draft". Activation (and the later deactivation of the old
single-question batch) is a deliberate, separate, later step -- never performed by this module.

A bundle is still exactly one row / one adaptive-pool passage. MCQ bundle content
(subquestions, each with its own correct_index) and Gap Fill bundle content (note_template +
blanks, each with accepted_answers/max_words/case_sensitive) live entirely inside body_json --
the top-level options_json/correct_index columns are left NULL for every bundle row, since the
real answer data lives in body_json["subquestions"] instead.

draft_id (e.g. "LSTB-A1-MCQ-01") is an authoring-time identifier only. It is never written to any
database ID column -- it is used solely to build the stable_key above.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.language.catalog import Language
from app.models.language.enums import LanguageLevel
from app.models.language.question_bank import LanguagePlacementQuestionBankItem

DEFAULT_DRAFT_PATH = (
    Path(__file__).resolve().parents[2] / "content_drafts" / "listening_bundles_v1_draft.md"
)

STABLE_KEY_PREFIX = "listening_bundles_v1"
SOURCE = "listening_bundles_v1_draft"
SKILL = "listening"

EXPECTED_DISTRIBUTION: dict[tuple[str, str], int] = {
    ("A1", "mcq"): 3, ("A1", "gap_fill"): 2,
    ("A2", "mcq"): 3, ("A2", "gap_fill"): 2,
    ("B1", "mcq"): 3, ("B1", "gap_fill"): 2,
    ("B2", "mcq"): 3, ("B2", "gap_fill"): 2,
    ("C1", "mcq"): 3, ("C1", "gap_fill"): 2,
    ("C2", "mcq"): 3, ("C2", "gap_fill"): 2,
}
EXPECTED_TOTAL = 30
EXPECTED_MCQ_TOTAL = 18
EXPECTED_GAP_FILL_TOTAL = 12
EXPECTED_ANSWER_POINTS = 90

_BUNDLE_SUBQUESTION_COUNT = 3
_BUNDLE_BLANK_COUNT = 3
_NOTE_TEMPLATE_TOKENS = ("{{1}}", "{{2}}", "{{3}}")
_DISALLOWED_GAP_FILL_SKILLS = frozenset({"inference", "implied_meaning", "speaker_attitude", "following_argument"})

REQUIRED_COMMON_FIELDS = ("draft_id", "level", "question_type", "audio_transcript")

_PROMPT_TEXT_BY_QUESTION_TYPE = {
    "mcq": "Listen to the clip, then answer the following questions.",
    "gap_fill": "Listen to the clip, then complete the notes below.",
}


@dataclass
class ValidationIssue:
    draft_id: str | None
    field: str
    message: str
    severity: str = "error"  # "error" blocks apply; "warning" is advisory only


@dataclass
class SeedCandidate:
    """An in-memory, not-yet-inserted row shape for LanguagePlacementQuestionBankItem.

    options_json/correct_index are deliberately not part of this shape -- every bundle row leaves
    those top-level columns NULL; the real MCQ answer data lives in body_json["subquestions"]."""

    draft_id: str
    stable_key: str
    cefr_level: str
    question_type: str
    prompt_text: str
    situation: str | None
    body_json: dict
    skill: str = SKILL
    source: str = SOURCE
    is_active: bool = False
    is_verified: bool = False


@dataclass
class DryRunSummary:
    total_parsed: int
    candidates: list[SeedCandidate]
    issues: list[ValidationIssue]
    distribution: dict[tuple[str, str], int]
    answer_points: int

    @property
    def errors(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == "error"]

    @property
    def warnings(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == "warning"]

    @property
    def is_valid(self) -> bool:
        return not self.errors


def _split_items(text: str) -> list[str]:
    parts = re.split(r"(?=^### ITEM LSTB-)", text, flags=re.MULTILINE)
    return [p for p in parts if p.startswith("### ITEM")]


def _extract_scalar(block: str, name: str) -> str | None:
    m = re.search(rf"^- {re.escape(name)}: (.+)$", block, flags=re.MULTILINE)
    return m.group(1).strip() if m else None


def _extract_quoted(block: str, name: str) -> str | None:
    raw = _extract_scalar(block, name)
    if raw is None:
        return None
    if raw.startswith('"') and raw.endswith('"') and len(raw) >= 2:
        return raw[1:-1]
    return raw


def _extract_int(block: str, name: str) -> int | None:
    raw = _extract_scalar(block, name)
    if raw is None:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def _extract_tag_list(block: str, name: str) -> list[str]:
    """For fields authored as a bare, unquoted bracket list, e.g. `[situation, explicit_detail]`
    -- not valid JSON, so parsed as a simple comma-split rather than json.loads."""
    raw = _extract_scalar(block, name)
    if raw is None:
        return []
    raw = raw.strip()
    if raw.startswith("[") and raw.endswith("]"):
        raw = raw[1:-1]
    return [t.strip() for t in raw.split(",") if t.strip()]


def _extract_json_fence(block: str) -> dict | None:
    m = re.search(r"```json\s*\n(.*?)\n```", block, flags=re.DOTALL)
    if not m:
        return None
    try:
        return json.loads(m.group(1))
    except json.JSONDecodeError:
        return None


def _parse_item_block(block: str) -> dict:
    parsed: dict = {}
    parsed["draft_id"] = _extract_scalar(block, "draft_id")
    parsed["level"] = _extract_scalar(block, "level")
    parsed["question_type"] = _extract_scalar(block, "question_type")
    parsed["title"] = _extract_scalar(block, "title")
    parsed["situation"] = _extract_scalar(block, "situation")
    parsed["audio_transcript"] = _extract_quoted(block, "audio_transcript")
    parsed["listening_skill_tags"] = _extract_tag_list(block, "listening_skill_tags")
    parsed["estimated_audio_duration_seconds"] = _extract_int(block, "estimated_audio_duration_seconds")
    parsed["body_json_candidate"] = _extract_json_fence(block)
    return parsed


def _validate_mcq_bundle(draft_id: str | None, body: dict) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    subquestions = body.get("subquestions")
    if not isinstance(subquestions, list) or len(subquestions) != _BUNDLE_SUBQUESTION_COUNT:
        issues.append(ValidationIssue(
            draft_id, "subquestions",
            f"MCQ bundle must have exactly {_BUNDLE_SUBQUESTION_COUNT} subquestions, "
            f"found {len(subquestions) if isinstance(subquestions, list) else type(subquestions).__name__}",
        ))
        subquestions = []
    for idx, sq in enumerate(subquestions):
        if not isinstance(sq, dict):
            issues.append(ValidationIssue(draft_id, f"subquestions[{idx}]", "subquestion must be an object"))
            continue
        if not str(sq.get("question") or "").strip():
            issues.append(ValidationIssue(draft_id, f"subquestions[{idx}].question", "missing non-empty question text"))
        options = sq.get("options")
        ci = sq.get("correct_index")
        if not isinstance(options, list) or len(options) != 4:
            issues.append(ValidationIssue(draft_id, f"subquestions[{idx}].options", "must have exactly 4 options"))
            options = []
        if not isinstance(ci, int) or isinstance(ci, bool) or not (0 <= ci < len(options)):
            issues.append(ValidationIssue(draft_id, f"subquestions[{idx}].correct_index", "must be a valid, in-range integer"))
    return issues


def _validate_gap_fill_bundle(draft_id: str | None, body: dict, skill_tags: list[str]) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    note_template = body.get("note_template")
    if not isinstance(note_template, str) or not note_template.strip():
        issues.append(ValidationIssue(draft_id, "note_template", "missing non-empty note_template"))
        note_template = ""
    else:
        for token in _NOTE_TEMPLATE_TOKENS:
            count = note_template.count(token)
            if count != 1:
                issues.append(ValidationIssue(
                    draft_id, "note_template", f"token {token} appears {count} times (expected exactly 1)"
                ))

    blanks = body.get("blanks")
    if not isinstance(blanks, list) or len(blanks) != _BUNDLE_BLANK_COUNT:
        issues.append(ValidationIssue(
            draft_id, "blanks",
            f"Gap Fill bundle must have exactly {_BUNDLE_BLANK_COUNT} blanks, "
            f"found {len(blanks) if isinstance(blanks, list) else type(blanks).__name__}",
        ))
        blanks = []

    for idx, blank in enumerate(blanks):
        if not isinstance(blank, dict):
            issues.append(ValidationIssue(draft_id, f"blanks[{idx}]", "blank must be an object"))
            continue
        aa = blank.get("accepted_answers")
        mw = blank.get("max_words")
        cs = blank.get("case_sensitive")
        if not isinstance(aa, list) or not aa:
            issues.append(ValidationIssue(draft_id, f"blanks[{idx}].accepted_answers", "must be a non-empty list"))
            aa = []
        if not isinstance(mw, int) or isinstance(mw, bool) or mw <= 0:
            issues.append(ValidationIssue(draft_id, f"blanks[{idx}].max_words", "must be a positive integer"))
            mw = None
        if cs is not False:
            issues.append(ValidationIssue(draft_id, f"blanks[{idx}].case_sensitive", "must be exactly false"))
        for a in aa:
            if not isinstance(a, str) or not a.strip():
                issues.append(ValidationIssue(draft_id, f"blanks[{idx}].accepted_answers", f"empty or non-string accepted answer: {a!r}"))
            elif mw is not None and len(a.split()) > mw:
                issues.append(ValidationIssue(draft_id, f"blanks[{idx}].accepted_answers", f"accepted answer '{a}' exceeds max_words={mw}"))

    # No accepted-answer leakage into the visible (non-token) note_template text.
    if note_template and isinstance(blanks, list):
        stripped = re.sub(r"\{\{\d+\}\}", "", note_template).lower()
        for idx, blank in enumerate(blanks):
            if not isinstance(blank, dict):
                continue
            for a in (blank.get("accepted_answers") or []):
                if isinstance(a, str) and len(a) > 2 and a.lower() in stripped:
                    issues.append(ValidationIssue(
                        draft_id, f"blanks[{idx}].accepted_answers",
                        f"possible leakage: '{a}' appears in visible note_template text",
                        severity="warning",
                    ))

    disallowed_hit = set(skill_tags) & _DISALLOWED_GAP_FILL_SKILLS
    if disallowed_hit:
        issues.append(ValidationIssue(
            draft_id, "listening_skill_tags",
            f"Gap Fill bundle uses disallowed skill tag(s): {sorted(disallowed_hit)}",
        ))

    return issues


def _validate_item(raw: dict) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    draft_id = raw.get("draft_id")

    for f in REQUIRED_COMMON_FIELDS:
        value = raw.get(f)
        if value is None or (isinstance(value, str) and not value.strip()):
            issues.append(ValidationIssue(draft_id, f, f"missing or empty required field '{f}'"))

    body = raw.get("body_json_candidate")
    if body is None or not isinstance(body, dict):
        issues.append(ValidationIssue(draft_id, "body_json_candidate", "missing or invalid JSON fence block"))
        body = {}

    if not isinstance(body.get("audio_transcript"), str) or not body.get("audio_transcript", "").strip():
        issues.append(ValidationIssue(draft_id, "body_json_candidate.audio_transcript", "body_json missing non-empty audio_transcript"))

    qtype = raw.get("question_type")
    if qtype == "mcq":
        issues.extend(_validate_mcq_bundle(draft_id, body))
    elif qtype == "gap_fill":
        issues.extend(_validate_gap_fill_bundle(draft_id, body, raw.get("listening_skill_tags") or []))
    else:
        issues.append(ValidationIssue(draft_id, "question_type", f"unknown question_type: {qtype!r}"))

    return issues


def _build_candidate(raw: dict) -> SeedCandidate:
    draft_id = raw.get("draft_id") or "UNKNOWN"
    body = dict(raw.get("body_json_candidate") or {})
    # Defensive: draft_id (an authoring-time identifier) and any database-ID-shaped key must never
    # leak into body_json.
    for key in ("id", "draft_id", "bank_item_id"):
        body.pop(key, None)

    qtype = raw.get("question_type") or ""
    return SeedCandidate(
        draft_id=draft_id,
        stable_key=f"{STABLE_KEY_PREFIX}:{draft_id}",
        cefr_level=raw.get("level") or "",
        question_type=qtype,
        prompt_text=_PROMPT_TEXT_BY_QUESTION_TYPE.get(qtype, ""),
        situation=raw.get("situation"),
        body_json=body,
    )


def parse_draft_file(draft_path: Path | None = None) -> list[dict]:
    """Read and parse the draft markdown into raw per-item field dicts. Read-only; no DB access."""
    path = draft_path or DEFAULT_DRAFT_PATH
    text = path.read_text(encoding="utf-8")
    return [_parse_item_block(block) for block in _split_items(text)]


def build_dry_run_summary(draft_path: Path | None = None, *, enforce_batch_totals: bool = True) -> DryRunSummary:
    """Parse + validate the draft file and build in-memory candidates. Never touches a database.

    enforce_batch_totals=False skips only the whole-batch 30/distribution/18+12/90-answer-point
    checks (every per-item validation rule still runs). Exists solely so apply tests can exercise
    real insert/update/idempotency behavior against small synthetic fixtures without needing to
    replicate the full 30-item batch; the CLI and the real draft always use the default (True).
    """
    raw_items = parse_draft_file(draft_path)

    issues: list[ValidationIssue] = []
    seen_ids: Counter = Counter()
    candidates: list[SeedCandidate] = []
    distribution: Counter = Counter()
    answer_points = 0

    for raw in raw_items:
        draft_id = raw.get("draft_id")
        if draft_id:
            seen_ids[draft_id] += 1
        issues.extend(_validate_item(raw))
        level, qtype = raw.get("level"), raw.get("question_type")
        if level and qtype:
            distribution[(level, qtype)] += 1
        candidate = _build_candidate(raw)
        candidates.append(candidate)

        body = candidate.body_json
        if qtype == "mcq":
            subquestions = body.get("subquestions")
            if isinstance(subquestions, list):
                answer_points += len(subquestions)
        elif qtype == "gap_fill":
            blanks = body.get("blanks")
            if isinstance(blanks, list):
                answer_points += len(blanks)

    for draft_id, count in seen_ids.items():
        if count > 1:
            issues.append(ValidationIssue(draft_id, "draft_id", f"duplicate draft_id appears {count} times"))

    if enforce_batch_totals:
        if len(raw_items) != EXPECTED_TOTAL:
            issues.append(ValidationIssue(None, "total_count", f"expected {EXPECTED_TOTAL} items, parsed {len(raw_items)}"))

        if dict(distribution) != EXPECTED_DISTRIBUTION:
            issues.append(ValidationIssue(None, "distribution", f"distribution mismatch: expected {EXPECTED_DISTRIBUTION}, got {dict(distribution)}"))

        mcq_total = sum(v for (_lvl, qt), v in distribution.items() if qt == "mcq")
        gap_fill_total = sum(v for (_lvl, qt), v in distribution.items() if qt == "gap_fill")
        if mcq_total != EXPECTED_MCQ_TOTAL:
            issues.append(ValidationIssue(None, "mcq_total", f"expected {EXPECTED_MCQ_TOTAL} MCQ bundles, got {mcq_total}"))
        if gap_fill_total != EXPECTED_GAP_FILL_TOTAL:
            issues.append(ValidationIssue(None, "gap_fill_total", f"expected {EXPECTED_GAP_FILL_TOTAL} Gap Fill bundles, got {gap_fill_total}"))
        if answer_points != EXPECTED_ANSWER_POINTS:
            issues.append(ValidationIssue(None, "answer_points", f"expected {EXPECTED_ANSWER_POINTS} total answer points, got {answer_points}"))

    return DryRunSummary(
        total_parsed=len(raw_items),
        candidates=candidates,
        issues=issues,
        distribution=dict(distribution),
        answer_points=answer_points,
    )


# ---------------------------------------------------------------------------
# Apply-mode implementation. Only executes DB writes when a caller explicitly passes a real
# AsyncSession and apply=True -- never invoked by the dry-run code above, and not run against any
# real database by Phase 6C.
# ---------------------------------------------------------------------------


@dataclass
class ApplyResult:
    inserted: int
    updated: int
    stable_keys: list[str] = field(default_factory=list)


async def _language_id(db: AsyncSession, code: str) -> int | None:
    return (
        await db.execute(select(Language.id).where(Language.code == code, Language.is_active.is_(True)).limit(1))
    ).scalar_one_or_none()


async def _existing_by_stable_key(db: AsyncSession, keys: list[str]) -> dict[str, LanguagePlacementQuestionBankItem]:
    if not keys:
        return {}
    rows = (
        await db.execute(select(LanguagePlacementQuestionBankItem).where(LanguagePlacementQuestionBankItem.stable_key.in_(keys)))
    ).scalars().all()
    return {r.stable_key: r for r in rows if r.stable_key}


def _apply_candidate_fields(row: LanguagePlacementQuestionBankItem, candidate: SeedCandidate, *, language_id: int) -> None:
    """Populate every field this seed step owns except is_active/is_verified, which the caller
    handles separately (mirrors language_listening_bank_seed_service.py's own safety invariant so
    a later human activation decision can never be silently reset by a routine content-sync
    re-run). options_json/correct_index are always left NULL -- bundle rows carry MCQ answer data
    only inside body_json["subquestions"]."""
    row.language_id = language_id
    row.skill = candidate.skill
    row.level = LanguageLevel(candidate.cefr_level)
    row.question_type = candidate.question_type
    row.prompt_text = candidate.prompt_text
    row.situation = candidate.situation
    row.options_json = None
    row.correct_index = None
    row.body_json = dict(candidate.body_json)
    row.source = candidate.source
    # Deliberately never touched here: audio_meta_json (this phase never generates/assigns audio),
    # is_active, is_verified (see caller).


async def apply_seed_batch(
    db: AsyncSession,
    *,
    language_code: str = "en",
    apply: bool = True,
    draft_path: Path | None = None,
    enforce_batch_totals: bool = True,
) -> tuple[DryRunSummary, ApplyResult | None]:
    """Validate the draft and, only if apply=True and validation is clean, insert/update every
    candidate idempotently by stable_key. Returns (summary, apply_result); apply_result is None
    whenever nothing was written (apply=False, validation failed, or the language code could not
    be resolved).

    Insert: is_active=False, is_verified=False, source="listening_bundles_v1_draft" -- brand-new
    rows are never active or verified; activation (and the later, separate deactivation of the old
    single-question batch) is a deliberate, later step, never performed by this module. Update: an
    existing row's is_active/is_verified are left completely untouched.
    """
    summary = build_dry_run_summary(draft_path, enforce_batch_totals=enforce_batch_totals)
    if not apply or not summary.is_valid:
        return summary, None

    language_id = await _language_id(db, language_code)
    if language_id is None:
        summary.issues.append(ValidationIssue(None, "language_id", f"language code {language_code!r} not found or inactive"))
        return summary, None

    keys = [c.stable_key for c in summary.candidates]
    existing = await _existing_by_stable_key(db, keys)
    inserted = updated = 0
    for candidate in summary.candidates:
        row = existing.get(candidate.stable_key)
        if row is None:
            row = LanguagePlacementQuestionBankItem(stable_key=candidate.stable_key)
            _apply_candidate_fields(row, candidate, language_id=language_id)
            row.is_active = False
            row.is_verified = False
            db.add(row)
            inserted += 1
        else:
            _apply_candidate_fields(row, candidate, language_id=language_id)
            updated += 1
    await db.commit()
    return summary, ApplyResult(inserted=inserted, updated=updated, stable_keys=keys)
