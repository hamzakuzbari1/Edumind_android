"""Phase 1 (dry-run parse/validate) and Phase 2A (apply implementation, not yet run) of the
Listening draft-to-bank insertion plan.

Phase 1 parses and validates backend/content_drafts/listening_mvp_60_item_bank_expansion_draft.md
and builds in-memory candidate rows for LanguagePlacementQuestionBankItem
(build_dry_run_summary()) -- this path never opens a database session and never writes anything.

Phase 2A (apply_seed_batch() below) adds the actual DB insert/update path, used only when a caller
explicitly passes a real AsyncSession and apply=True. It is idempotent by stable_key
("listening_mvp_60:<draft_id>"): a stable_key match updates content fields only and never resets
is_active/is_verified (mirroring language_speaking_placement_seed_service.py's own
_apply_content_fields safety invariant, so a later human activation decision can never be silently
reset by a routine content-sync re-run); a brand-new row is inserted with is_active=False,
is_verified=False, source="listening_mvp_60_draft". Activation is a deliberate, separate, later
step -- never performed by this module.

Kept importable/testable under app/services/ (backend/scripts/ is excluded from the test Docker
image), matching the established pattern from language_speaking_placement_seed_service.py and
language_listening_bank_audio_backfill_service.py. backend/scripts/seed_listening_bank_expansion.py
is a thin CLI wrapper around build_dry_run_summary()/apply_seed_batch() below.

draft_id (e.g. "LST-A1-01") is an authoring-time identifier only. It is never written to any
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
    Path(__file__).resolve().parents[2] / "content_drafts" / "listening_mvp_60_item_bank_expansion_draft.md"
)

STABLE_KEY_PREFIX = "listening_mvp_60"
SOURCE = "listening_mvp_60_draft"
SKILL = "listening"

EXPECTED_DISTRIBUTION: dict[tuple[str, str], int] = {
    ("A1", "mcq"): 4, ("A1", "gap_fill"): 4,
    ("A2", "mcq"): 4, ("A2", "gap_fill"): 4,
    ("B1", "mcq"): 4, ("B1", "gap_fill"): 4,
    ("B2", "mcq"): 3, ("B2", "gap_fill"): 3,
    ("C1", "mcq"): 3, ("C1", "gap_fill"): 3,
    ("C2", "mcq"): 3, ("C2", "gap_fill"): 3,
}
EXPECTED_TOTAL = 42
EXPECTED_MCQ_TOTAL = 21
EXPECTED_GAP_FILL_TOTAL = 21
_LEVELS_WITH_MANDATORY_WORD_BANK = ("A1", "A2")

REQUIRED_COMMON_FIELDS = (
    "draft_id", "cefr_level", "question_type", "listening_skill", "audio_context",
    "discourse_type", "transcript", "transcript_word_count", "situation",
    "prompt_or_question", "review_status", "human_reviewed", "audio_generation_status",
)


@dataclass
class ValidationIssue:
    draft_id: str | None
    field: str
    message: str
    severity: str = "error"  # "error" blocks Phase 2; "warning" is advisory only


@dataclass
class SeedCandidate:
    """An in-memory, not-yet-inserted row shape for LanguagePlacementQuestionBankItem."""

    draft_id: str
    stable_key: str
    cefr_level: str
    question_type: str
    prompt_text: str
    situation: str | None
    options_json: list | None
    correct_index: int | None
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
    parts = re.split(r"(?=^### ITEM LST-)", text, flags=re.MULTILINE)
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


def _extract_json_value(block: str, name: str):
    """For fields written as a JSON array literal or `null` on a single bullet line."""
    raw = _extract_scalar(block, name)
    if raw is None or raw == "null":
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def _extract_int(block: str, name: str) -> int | None:
    raw = _extract_scalar(block, name)
    if raw is None:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def _extract_bool(block: str, name: str) -> bool | None:
    raw = _extract_scalar(block, name)
    if raw is None:
        return None
    return raw.strip().lower() == "true"


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
    parsed["cefr_level"] = _extract_scalar(block, "cefr_level")
    parsed["question_type"] = _extract_scalar(block, "question_type")
    parsed["listening_skill"] = _extract_scalar(block, "listening_skill")
    secondary = _extract_scalar(block, "secondary_skill")
    parsed["secondary_skill"] = None if secondary in (None, "(none)", "null") else secondary
    parsed["audio_context"] = _extract_scalar(block, "audio_context")
    parsed["discourse_type"] = _extract_scalar(block, "discourse_type")
    parsed["transcript"] = _extract_quoted(block, "transcript")
    parsed["transcript_word_count"] = _extract_int(block, "transcript_word_count")
    parsed["target_duration_seconds"] = _extract_int(block, "target_duration_seconds")
    parsed["situation"] = _extract_scalar(block, "situation")
    parsed["prompt_or_question"] = _extract_scalar(block, "prompt_or_question")
    parsed["review_status"] = _extract_scalar(block, "review_status")
    parsed["human_reviewed"] = _extract_bool(block, "human_reviewed")
    parsed["audio_generation_status"] = _extract_scalar(block, "audio_generation_status")

    qtype = parsed["question_type"]
    if qtype == "mcq":
        parsed["options"] = _extract_json_value(block, "options")
        parsed["correct_index"] = _extract_int(block, "correct_index")
        parsed["correct_answer"] = _extract_scalar(block, "correct_answer")
        parsed["rationale"] = _extract_scalar(block, "rationale")
        parsed["distractor_rationale"] = _extract_scalar(block, "distractor_rationale")
    elif qtype == "gap_fill":
        parsed["accepted_answers"] = _extract_json_value(block, "accepted_answers")
        parsed["max_words"] = _extract_int(block, "max_words")
        parsed["case_sensitive"] = _extract_bool(block, "case_sensitive")
        parsed["word_bank"] = _extract_json_value(block, "word_bank")
        parsed["correct_answer"] = _extract_scalar(block, "correct_answer")
        parsed["rationale"] = _extract_scalar(block, "rationale")

    parsed["body_json_candidate"] = _extract_json_fence(block)
    return parsed


def _normalize_text(value) -> str:
    if not isinstance(value, str):
        return ""
    return " ".join(value.replace('"', "").split()).strip().lower()


def _normalize_tag(value) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip().lower().replace("_", " ").replace("-", " ")


def _validate_item(raw: dict) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    draft_id = raw.get("draft_id")

    for f in REQUIRED_COMMON_FIELDS:
        value = raw.get(f)
        missing = value is None or (isinstance(value, str) and not value.strip())
        if f == "human_reviewed" and value is False:
            missing = False  # a real, present boolean value -- not "missing"
        if missing:
            issues.append(ValidationIssue(draft_id, f, f"missing or empty required field '{f}'"))

    body = raw.get("body_json_candidate")
    if body is None or not isinstance(body, dict):
        issues.append(ValidationIssue(draft_id, "body_json_candidate", "missing or invalid JSON fence block"))
        body = {}

    qtype = raw.get("question_type")
    if qtype == "mcq":
        opts = raw.get("options")
        ci = raw.get("correct_index")
        if not isinstance(opts, list) or len(opts) != 4:
            issues.append(ValidationIssue(draft_id, "options", "MCQ must have exactly 4 options"))
        if not isinstance(ci, int) or not (0 <= ci <= 3):
            issues.append(ValidationIssue(draft_id, "correct_index", "MCQ correct_index must be an integer from 0 to 3"))
        if not raw.get("correct_answer"):
            issues.append(ValidationIssue(draft_id, "correct_answer", "MCQ missing correct_answer"))
        if not raw.get("rationale"):
            issues.append(ValidationIssue(draft_id, "rationale", "MCQ missing rationale"))
        if _normalize_text(body.get("transcript")) != _normalize_text(raw.get("transcript")):
            issues.append(ValidationIssue(draft_id, "body_json_candidate.transcript", "body_json transcript does not match visible transcript"))
        if _normalize_text(body.get("question")) != _normalize_text(raw.get("prompt_or_question")):
            issues.append(ValidationIssue(draft_id, "body_json_candidate.question", "body_json question does not match visible prompt_or_question"))
        if body.get("options") != opts:
            issues.append(ValidationIssue(draft_id, "body_json_candidate.options", "body_json options do not match visible options"))
        if body.get("correct_index") != ci:
            issues.append(ValidationIssue(draft_id, "body_json_candidate.correct_index", "body_json correct_index does not match visible correct_index"))
    elif qtype == "gap_fill":
        aa = raw.get("accepted_answers")
        mw = raw.get("max_words")
        cs = raw.get("case_sensitive")
        wb = raw.get("word_bank")
        level = raw.get("cefr_level")

        if not isinstance(aa, list) or not aa:
            issues.append(ValidationIssue(draft_id, "accepted_answers", "Gap Fill accepted_answers must be a non-empty list"))
            aa = []
        if not isinstance(mw, int) or mw <= 0:
            issues.append(ValidationIssue(draft_id, "max_words", "Gap Fill max_words must be a positive integer"))
            mw = None
        if cs is not False:
            issues.append(ValidationIssue(draft_id, "case_sensitive", "Gap Fill case_sensitive must be false"))

        for a in aa:
            if not isinstance(a, str) or not a.strip():
                issues.append(ValidationIssue(draft_id, "accepted_answers", f"empty or non-string accepted answer: {a!r}"))
            elif mw is not None and len(a.split()) > mw:
                issues.append(ValidationIssue(draft_id, "accepted_answers", f"accepted answer '{a}' exceeds max_words={mw}"))

        if level in _LEVELS_WITH_MANDATORY_WORD_BANK:
            if not isinstance(wb, list) or not wb:
                issues.append(ValidationIssue(draft_id, "word_bank", f"{level} Gap Fill items require a non-empty word_bank"))
                wb = []
            else:
                normalized_wb = {_normalize_text(w) for w in wb if isinstance(w, str)}
                normalized_aa = {_normalize_text(a) for a in aa if isinstance(a, str)}
                if normalized_wb.isdisjoint(normalized_aa):
                    issues.append(ValidationIssue(
                        draft_id, "word_bank",
                        "correct answer does not appear in word_bank (expected where practical for A1/A2)",
                        severity="warning",
                    ))
        if isinstance(wb, list) and mw is not None:
            for w in wb:
                if isinstance(w, str) and len(w.split()) > mw:
                    issues.append(ValidationIssue(draft_id, "word_bank", f"word_bank option '{w}' exceeds max_words={mw}"))

        if not raw.get("correct_answer"):
            issues.append(ValidationIssue(draft_id, "correct_answer", "Gap Fill missing correct_answer"))
        if not raw.get("rationale"):
            issues.append(ValidationIssue(draft_id, "rationale", "Gap Fill missing rationale"))

        if _normalize_text(body.get("transcript")) != _normalize_text(raw.get("transcript")):
            issues.append(ValidationIssue(draft_id, "body_json_candidate.transcript", "body_json transcript does not match visible transcript"))
        if _normalize_text(body.get("prompt")) != _normalize_text(raw.get("prompt_or_question")):
            issues.append(ValidationIssue(draft_id, "body_json_candidate.prompt", "body_json prompt does not match visible prompt_or_question"))
        if body.get("accepted_answers") != raw.get("accepted_answers"):
            issues.append(ValidationIssue(draft_id, "body_json_candidate.accepted_answers", "body_json accepted_answers do not match visible accepted_answers"))
        if body.get("max_words") != raw.get("max_words"):
            issues.append(ValidationIssue(draft_id, "body_json_candidate.max_words", "body_json max_words does not match visible max_words"))
        if body.get("word_bank") != raw.get("word_bank"):
            issues.append(ValidationIssue(draft_id, "body_json_candidate.word_bank", "body_json word_bank does not match visible word_bank"))
    else:
        issues.append(ValidationIssue(draft_id, "question_type", f"unknown question_type: {qtype!r}"))

    for tag_field in ("listening_skill", "audio_context", "discourse_type"):
        if _normalize_tag(body.get(tag_field)) != _normalize_tag(raw.get(tag_field)):
            issues.append(ValidationIssue(draft_id, f"body_json_candidate.{tag_field}", f"body_json {tag_field} does not match visible {tag_field}"))

    return issues


def _build_candidate(raw: dict) -> SeedCandidate:
    draft_id = raw.get("draft_id") or "UNKNOWN"
    body = dict(raw.get("body_json_candidate") or {})
    # Defensive: draft_id (an authoring-time identifier) and any database-ID-shaped key must never
    # leak into body_json -- the draft file has never included these, but strip defensively anyway.
    for key in ("id", "draft_id", "bank_item_id"):
        body.pop(key, None)

    # The live audio-resolution path (_listening_text_from_body, shared by the audio backfill
    # service and the runtime exam) reads only audio_transcript/text/passage -- never this draft
    # format's own "transcript" authoring-metadata key. Mirror it into audio_transcript so every
    # seeded row is actually resolvable for audio, while leaving "transcript" itself untouched.
    transcript = body.get("transcript")
    if transcript and not body.get("audio_transcript"):
        body["audio_transcript"] = transcript

    qtype = raw.get("question_type") or ""
    return SeedCandidate(
        draft_id=draft_id,
        stable_key=f"{STABLE_KEY_PREFIX}:{draft_id}",
        cefr_level=raw.get("cefr_level") or "",
        question_type=qtype,
        prompt_text=raw.get("prompt_or_question") or "",
        situation=raw.get("situation"),
        options_json=raw.get("options") if qtype == "mcq" else None,
        correct_index=raw.get("correct_index") if qtype == "mcq" else None,
        body_json=body,
    )


def parse_draft_file(draft_path: Path | None = None) -> list[dict]:
    """Read and parse the draft markdown into raw per-item field dicts. Read-only; no DB access."""
    path = draft_path or DEFAULT_DRAFT_PATH
    text = path.read_text(encoding="utf-8")
    return [_parse_item_block(block) for block in _split_items(text)]


def build_dry_run_summary(draft_path: Path | None = None, *, enforce_batch_totals: bool = True) -> DryRunSummary:
    """Parse + validate the draft file and build in-memory candidates. Never touches a database.

    enforce_batch_totals=False skips only the whole-batch 42/distribution/21+21 checks (every
    per-item validation rule still runs). This exists solely so Phase 2A apply tests can exercise
    real insert/update/idempotency behavior against small synthetic fixtures without needing to
    replicate the full 42-item MVP batch; the CLI and the real 42-item draft always use the
    default (True), so production/dry-run behavior is completely unchanged.
    """
    raw_items = parse_draft_file(draft_path)

    issues: list[ValidationIssue] = []
    seen_ids: Counter = Counter()
    candidates: list[SeedCandidate] = []
    distribution: Counter = Counter()

    for raw in raw_items:
        draft_id = raw.get("draft_id")
        if draft_id:
            seen_ids[draft_id] += 1
        issues.extend(_validate_item(raw))
        level, qtype = raw.get("cefr_level"), raw.get("question_type")
        if level and qtype:
            distribution[(level, qtype)] += 1
        candidate = _build_candidate(raw)
        candidates.append(candidate)

        audio_transcript = candidate.body_json.get("audio_transcript")
        if not isinstance(audio_transcript, str) or not audio_transcript.strip():
            issues.append(
                ValidationIssue(
                    candidate.draft_id, "body_json.audio_transcript",
                    "candidate body_json is missing a non-empty audio_transcript",
                )
            )

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
            issues.append(ValidationIssue(None, "mcq_total", f"expected {EXPECTED_MCQ_TOTAL} MCQ items, got {mcq_total}"))
        if gap_fill_total != EXPECTED_GAP_FILL_TOTAL:
            issues.append(ValidationIssue(None, "gap_fill_total", f"expected {EXPECTED_GAP_FILL_TOTAL} Gap Fill items, got {gap_fill_total}"))

    return DryRunSummary(
        total_parsed=len(raw_items),
        candidates=candidates,
        issues=issues,
        distribution=dict(distribution),
    )


# ---------------------------------------------------------------------------
# Phase 2A: apply-mode implementation. Only executes DB writes when a caller explicitly passes a
# real AsyncSession and apply=True -- never invoked by Phase 1 dry-run code above, and not run
# against any real database by this task.
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
    handles separately (see module docstring for the safety reasoning -- mirrors
    language_speaking_placement_seed_service.py's _apply_content_fields)."""
    row.language_id = language_id
    row.skill = candidate.skill
    row.level = LanguageLevel(candidate.cefr_level)
    row.question_type = candidate.question_type
    row.prompt_text = candidate.prompt_text
    row.situation = candidate.situation
    row.options_json = candidate.options_json
    row.correct_index = candidate.correct_index
    row.body_json = dict(candidate.body_json)
    row.source = candidate.source
    # Deliberately never touched here: audio_meta_json (Phase 2A never generates/assigns audio),
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
    be resolved) -- callers should always check summary.is_valid / apply_result is not None rather
    than assume success.

    Insert: is_active=False, is_verified=False, source="listening_mvp_60_draft" -- brand-new rows
    are never active or verified; a separate, later, deliberate step activates MCQ rows once audio
    exists (see the insertion plan). Update: an existing row's is_active/is_verified are left
    completely untouched, so this can be re-run at any time (e.g. to fix a content typo) without
    ever resetting a human reviewer's later activation decision.
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
