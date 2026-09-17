"""Writing MVP v1 draft-to-placement-bank seeding.

The source draft is a JSON object with 60 CEFR-aligned prompts:
10 per A1/A2/B1/B2/C1/C2. Fresh apply rows are inactive/unverified; the explicit cutover path
activates this curated source and soft-retires legacy content_seed Writing rows.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.language.catalog import Language
from app.models.language.enums import LanguageLevel
from app.models.language.question_bank import LanguagePlacementQuestionBankItem


SKILL = "writing_prompt"
SOURCE = "writing_mvp_v1_draft"
STABLE_KEY_PREFIX = "writing_mvp_v1"
DEFAULT_DRAFT_PATH = Path(__file__).resolve().parents[2] / "content_drafts" / "writing_mvp_v1_draft.json"
LEVELS = ("A1", "A2", "B1", "B2", "C1", "C2")
EXPECTED_WORD_RANGES = {
    "A1": (30, 50),
    "A2": (50, 80),
    "B1": (90, 130),
    "B2": (140, 190),
    "C1": (200, 260),
    "C2": (260, 340),
}
_KEY_RE = re.compile(r"^writing_mvp_v1_(A1|A2|B1|B2|C1|C2)_(0[1-9]|10)$")


@dataclass(frozen=True)
class ValidationIssue:
    stable_key: str | None
    field: str
    message: str
    severity: str = "error"


@dataclass(frozen=True)
class WritingSeedCandidate:
    stable_key: str
    level: str
    task_type: str
    prompt: str
    target_min_words: int
    target_max_words: int
    rubric_focus: list[str]
    expected_language_features: list[str]
    student_instructions: str
    review_status: str

    @property
    def bank_stable_key(self) -> str:
        return self.stable_key

    @property
    def body_json(self) -> dict[str, Any]:
        return {
            "task_type": self.task_type,
            "target_min_words": self.target_min_words,
            "target_max_words": self.target_max_words,
            "rubric_focus": list(self.rubric_focus),
            "expected_language_features": list(self.expected_language_features),
            "student_instructions": self.student_instructions,
            "review_status": self.review_status,
            "source_version": STABLE_KEY_PREFIX,
        }


@dataclass
class DryRunSummary:
    total_parsed: int
    candidates: list[WritingSeedCandidate] = field(default_factory=list)
    issues: list[ValidationIssue] = field(default_factory=list)
    distribution: dict[str, int] = field(default_factory=dict)

    @property
    def errors(self) -> list[ValidationIssue]:
        return [issue for issue in self.issues if issue.severity == "error"]

    @property
    def warnings(self) -> list[ValidationIssue]:
        return [issue for issue in self.issues if issue.severity == "warning"]

    @property
    def is_valid(self) -> bool:
        return not self.errors


@dataclass
class ApplyResult:
    inserted: int
    updated: int
    stable_keys: list[str] = field(default_factory=list)


@dataclass
class CutoverResult:
    inserted: int
    updated: int
    activated_mvp_rows: int
    retired_content_seed_rows: int
    active_mvp_rows: int
    active_content_seed_rows: int
    stable_keys: list[str] = field(default_factory=list)


def _as_clean_str(value: object) -> str:
    return str(value or "").strip()


def _validate_string_list(
    item: dict[str, Any],
    *,
    stable_key: str | None,
    field: str,
    issues: list[ValidationIssue],
) -> list[str]:
    value = item.get(field)
    if not isinstance(value, list) or not value:
        issues.append(ValidationIssue(stable_key, field, "must be a non-empty list of strings"))
        return []
    cleaned = [_as_clean_str(part) for part in value]
    if any(not part for part in cleaned):
        issues.append(ValidationIssue(stable_key, field, "must not contain empty values"))
    return cleaned


def _load_items(path: Path) -> tuple[list[dict[str, Any]], list[ValidationIssue]]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return [], [ValidationIssue(None, "draft_path", f"file not found: {path}")]
    except json.JSONDecodeError as exc:
        return [], [ValidationIssue(None, "json", f"invalid JSON: {exc}")]
    if not isinstance(raw, dict) or not isinstance(raw.get("writing_prompts"), list):
        return [], [ValidationIssue(None, "writing_prompts", "draft must contain a writing_prompts list")]
    items = raw["writing_prompts"]
    if not all(isinstance(item, dict) for item in items):
        return [], [ValidationIssue(None, "writing_prompts", "every prompt must be an object")]
    return list(items), []


def build_dry_run_summary(
    draft_path: Path | None = None,
    *,
    enforce_batch_totals: bool = True,
) -> DryRunSummary:
    path = draft_path or DEFAULT_DRAFT_PATH
    raw_items, issues = _load_items(path)
    candidates: list[WritingSeedCandidate] = []
    distribution = {level: 0 for level in LEVELS}
    seen_keys: set[str] = set()

    for idx, item in enumerate(raw_items, start=1):
        stable_key = _as_clean_str(item.get("stable_key")) or f"row-{idx}"
        level = _as_clean_str(item.get("level")).upper()
        task_type = _as_clean_str(item.get("task_type"))
        prompt = _as_clean_str(item.get("prompt"))
        student_instructions = _as_clean_str(item.get("student_instructions"))
        review_status = _as_clean_str(item.get("review_status")) or "draft"
        rubric_focus = _validate_string_list(item, stable_key=stable_key, field="rubric_focus", issues=issues)
        expected_features = _validate_string_list(
            item,
            stable_key=stable_key,
            field="expected_language_features",
            issues=issues,
        )

        if stable_key in seen_keys:
            issues.append(ValidationIssue(stable_key, "stable_key", "duplicate stable_key"))
        seen_keys.add(stable_key)
        match = _KEY_RE.fullmatch(stable_key)
        if not match:
            issues.append(ValidationIssue(stable_key, "stable_key", "must match writing_mvp_v1_{LEVEL}_{01-10}"))
        elif level and match.group(1) != level:
            issues.append(ValidationIssue(stable_key, "level", "level must match stable_key level"))

        if level not in EXPECTED_WORD_RANGES:
            issues.append(ValidationIssue(stable_key, "level", "must be A1, A2, B1, B2, C1, or C2"))
        else:
            distribution[level] += 1

        if not task_type:
            issues.append(ValidationIssue(stable_key, "task_type", "must not be empty"))
        if len(prompt.split()) < 8:
            issues.append(ValidationIssue(stable_key, "prompt", "must be a clear task prompt"))
        if not student_instructions:
            issues.append(ValidationIssue(stable_key, "student_instructions", "must not be empty"))

        expected_range = EXPECTED_WORD_RANGES.get(level)
        target_min = item.get("target_min_words")
        target_max = item.get("target_max_words")
        if not isinstance(target_min, int) or isinstance(target_min, bool):
            issues.append(ValidationIssue(stable_key, "target_min_words", "must be an integer"))
            target_min = 0
        if not isinstance(target_max, int) or isinstance(target_max, bool):
            issues.append(ValidationIssue(stable_key, "target_max_words", "must be an integer"))
            target_max = 0
        if expected_range and (target_min, target_max) != expected_range:
            issues.append(
                ValidationIssue(
                    stable_key,
                    "word_range",
                    f"must be {expected_range[0]}-{expected_range[1]} words for {level}",
                )
            )
        if target_min and target_max and target_min >= target_max:
            issues.append(ValidationIssue(stable_key, "word_range", "target_min_words must be below target_max_words"))

        candidates.append(
            WritingSeedCandidate(
                stable_key=stable_key,
                level=level,
                task_type=task_type,
                prompt=prompt,
                target_min_words=int(target_min or 0),
                target_max_words=int(target_max or 0),
                rubric_focus=rubric_focus,
                expected_language_features=expected_features,
                student_instructions=student_instructions,
                review_status=review_status,
            )
        )

    if enforce_batch_totals:
        if len(raw_items) != 60:
            issues.append(ValidationIssue(None, "writing_prompts", f"expected 60 prompts, found {len(raw_items)}"))
        for level in LEVELS:
            if distribution[level] != 10:
                issues.append(ValidationIssue(None, f"distribution.{level}", f"expected 10, found {distribution[level]}"))

    return DryRunSummary(
        total_parsed=len(raw_items),
        candidates=candidates,
        issues=issues,
        distribution=distribution,
    )


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
    return {str(row.stable_key): row for row in rows if row.stable_key}


def _apply_candidate_fields(row: LanguagePlacementQuestionBankItem, candidate: WritingSeedCandidate, *, language_id: int) -> None:
    row.language_id = language_id
    row.skill = SKILL
    row.level = LanguageLevel(candidate.level)
    row.boundary_low_level = None
    row.boundary_high_level = None
    row.subskill = candidate.task_type
    row.question_type = "writing_prompt"
    row.prompt_text = candidate.prompt
    row.passage = None
    row.situation = None
    row.options_json = None
    row.correct_index = None
    row.explanation = None
    row.body_json = candidate.body_json
    row.source = SOURCE


async def apply_seed_batch(
    db: AsyncSession,
    *,
    language_code: str = "en",
    apply: bool = True,
    draft_path: Path | None = None,
    enforce_batch_totals: bool = True,
) -> tuple[DryRunSummary, ApplyResult | None]:
    summary = build_dry_run_summary(draft_path, enforce_batch_totals=enforce_batch_totals)
    if not apply or not summary.is_valid:
        return summary, None

    language_id = await _language_id(db, language_code)
    if language_id is None:
        summary.issues.append(ValidationIssue(None, "language_id", f"language code {language_code!r} not found or inactive"))
        return summary, None

    keys = [candidate.bank_stable_key for candidate in summary.candidates]
    existing = await _existing_by_stable_key(db, keys)
    inserted = updated = 0
    for candidate in summary.candidates:
        row = existing.get(candidate.bank_stable_key)
        if row is None:
            row = LanguagePlacementQuestionBankItem(stable_key=candidate.bank_stable_key)
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


async def activate_writing_mvp_v1_cutover(
    db: AsyncSession,
    *,
    language_code: str = "en",
    draft_path: Path | None = None,
    enforce_batch_totals: bool = True,
) -> tuple[DryRunSummary, CutoverResult | None]:
    summary, apply_result = await apply_seed_batch(
        db,
        language_code=language_code,
        apply=True,
        draft_path=draft_path,
        enforce_batch_totals=enforce_batch_totals,
    )
    if not summary.is_valid or apply_result is None:
        return summary, None

    language_id = await _language_id(db, language_code)
    if language_id is None:
        summary.issues.append(ValidationIssue(None, "language_id", f"language code {language_code!r} not found or inactive"))
        return summary, None

    keys = [candidate.bank_stable_key for candidate in summary.candidates]
    rows = (
        await db.execute(
            select(LanguagePlacementQuestionBankItem).where(
                LanguagePlacementQuestionBankItem.language_id == language_id,
                LanguagePlacementQuestionBankItem.skill == SKILL,
                LanguagePlacementQuestionBankItem.stable_key.in_(keys),
            )
        )
    ).scalars().all()
    if len(rows) != len(keys):
        summary.issues.append(ValidationIssue(None, "stable_keys", f"expected {len(keys)} MVP rows, found {len(rows)}"))
        return summary, None

    activated = 0
    for row in rows:
        if row.source != SOURCE or not str(row.stable_key or "").startswith(STABLE_KEY_PREFIX):
            summary.issues.append(ValidationIssue(str(row.stable_key), "source", "unexpected source for MVP row"))
            return summary, None
        if not row.is_active or not row.is_verified:
            activated += 1
        row.is_active = True
        row.is_verified = True

    old_rows = (
        await db.execute(
            select(LanguagePlacementQuestionBankItem).where(
                LanguagePlacementQuestionBankItem.language_id == language_id,
                LanguagePlacementQuestionBankItem.skill == SKILL,
                LanguagePlacementQuestionBankItem.source == "content_seed",
                LanguagePlacementQuestionBankItem.is_active.is_(True),
            )
        )
    ).scalars().all()
    retired = 0
    for row in old_rows:
        row.is_active = False
        retired += 1

    await db.commit()

    active_mvp_rows = len([row for row in rows if row.is_active and row.is_verified and row.source == SOURCE])
    active_content_seed_rows = (
        await db.execute(
            select(LanguagePlacementQuestionBankItem.id).where(
                LanguagePlacementQuestionBankItem.language_id == language_id,
                LanguagePlacementQuestionBankItem.skill == SKILL,
                LanguagePlacementQuestionBankItem.source == "content_seed",
                LanguagePlacementQuestionBankItem.is_active.is_(True),
            )
        )
    ).scalars().all()

    return summary, CutoverResult(
        inserted=apply_result.inserted,
        updated=apply_result.updated,
        activated_mvp_rows=activated,
        retired_content_seed_rows=retired,
        active_mvp_rows=active_mvp_rows,
        active_content_seed_rows=len(active_content_seed_rows),
        stable_keys=keys,
    )
