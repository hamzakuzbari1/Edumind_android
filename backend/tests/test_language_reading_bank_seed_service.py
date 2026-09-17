"""Dry-run (parse/validate) and apply (DB-backed) tests for the Reading MVP v1 draft-to-bank seed
service.

Dry-run tests never touch a database -- they only exercise the pure parse/validate logic in
app/services/language_reading_bank_seed_service.py, either against the real draft file (for the
count/distribution checks) or against small synthetic in-memory markdown fixtures (for individual
validation-rule checks), matching the existing repo convention (see
test_language_listening_bank_seed_service.py) of not requiring Postgres for pure-logic tests.

Apply tests (`@pytest.mark.postgresql`, near the end of this file) exercise apply_seed_batch()
directly against the dedicated Postgres *_test* database -- never via the CLI script, never
against a real/dev database. Every test uses a throwaway Language row and unique synthetic
draft_ids (stable_key has a global-uniqueness constraint, not namespaced by language) so tests can
never collide with each other or with any real bank row; real rows never use
source="reading_mvp_v1_draft" or a "reading_mvp_v1:" stable_key prefix.
"""

from __future__ import annotations

import json
import subprocess
import sys
import uuid
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy import delete, select

from app.models.language.catalog import Language
from app.models.language.enums import LanguageLevel
from app.models.language.question_bank import LanguagePlacementQuestionBankItem
from app.services.language_reading_bank_seed_service import (
    DEFAULT_DRAFT_PATH,
    BOUNDARY_SOURCE,
    BOUNDARY_STABLE_KEY_PREFIX,
    EXPECTED_LEVELS,
    EXPECTED_PER_LEVEL,
    EXPECTED_TOTAL,
    READING_RESPONSE_TYPE_POLICY,
    STABLE_KEY_PREFIX,
    activate_reading_mvp_v1_cutover,
    apply_seed_batch,
    build_boundary_candidates,
    build_dry_run_summary,
    parse_draft_file,
    seed_reading_boundary_v1,
)

REPO_BACKEND_DIR = Path(__file__).resolve().parents[1]

# backend/content_drafts/ is authoring-time content, not app source, and is intentionally not
# copied into the test Docker image (same convention as backend/scripts/) -- these tests still run
# wherever the file is actually present (host, dev container) and skip gracefully otherwise.
_requires_real_draft = pytest.mark.skipif(
    not DEFAULT_DRAFT_PATH.exists(), reason="backend/content_drafts/ is not present in this test environment"
)


# ---------------------------------------------------------------------------
# Tests against the real draft file.
# ---------------------------------------------------------------------------


@_requires_real_draft
def test_parses_exactly_60_items():
    summary = build_dry_run_summary()
    assert summary.total_parsed == EXPECTED_TOTAL
    assert len(summary.candidates) == EXPECTED_TOTAL


@_requires_real_draft
def test_distribution_is_10_per_level():
    summary = build_dry_run_summary()
    assert summary.distribution == {lvl: EXPECTED_PER_LEVEL for lvl in EXPECTED_LEVELS}


@_requires_real_draft
def test_real_draft_has_zero_validation_errors():
    summary = build_dry_run_summary()
    assert summary.errors == []
    assert summary.is_valid


@_requires_real_draft
def test_candidates_default_to_inactive_and_unverified():
    summary = build_dry_run_summary()
    assert summary.candidates, "expected at least one candidate to check defaults on"
    for candidate in summary.candidates:
        assert candidate.is_active is False
        assert candidate.is_verified is False
        assert candidate.source == "reading_mvp_v1_draft"
        assert candidate.skill == "reading"
        assert candidate.question_type == "mcq"


@_requires_real_draft
def test_stable_key_format_is_correct():
    summary = build_dry_run_summary()
    for candidate in summary.candidates:
        assert candidate.stable_key == f"{STABLE_KEY_PREFIX}:{candidate.draft_id}"
        assert candidate.stable_key.startswith("reading_mvp_v1:RDG-")


@_requires_real_draft
def test_draft_id_never_used_as_a_database_id():
    summary = build_dry_run_summary()
    for candidate in summary.candidates:
        assert "id" not in candidate.body_json
        assert "bank_item_id" not in candidate.body_json
        assert "draft_id" not in candidate.body_json
        assert isinstance(candidate.draft_id, str)


def test_boundary_candidates_cover_adjacent_cefr_pairs():
    candidates = build_boundary_candidates()
    pairs = {(c.boundary_low_level, c.boundary_high_level) for c in candidates}
    assert pairs == {("A1", "A2"), ("A2", "B1"), ("B1", "B2"), ("B2", "C1"), ("C1", "C2")}
    assert len(candidates) == 10
    for candidate in candidates:
        assert candidate.stable_key.startswith(f"{BOUNDARY_STABLE_KEY_PREFIX}:")
        assert candidate.source == BOUNDARY_SOURCE
        assert candidate.is_active is True
        assert candidate.is_verified is True
        assert candidate.options_json[candidate.correct_index]
        metrics = candidate.body_json["placement_metrics"]
        assert metrics["cefr_level"] == candidate.cefr_level
        assert metrics["word_count"] > 0


@_requires_real_draft
def test_no_duplicate_titles_in_real_draft():
    raw_items = parse_draft_file()
    titles = [r.get("title") for r in raw_items]
    assert len(titles) == len(set(titles))


@_requires_real_draft
def test_real_draft_items_are_all_four_question_bundles():
    summary = build_dry_run_summary()
    assert summary.errors == []
    for candidate in summary.candidates:
        subquestions = candidate.body_json.get("subquestions") or []
        assert len(subquestions) == 4, candidate.draft_id
        assert subquestions[0]["question"] == candidate.prompt_text
        assert subquestions[0]["options"] == candidate.options_json
        assert subquestions[0]["correct_index"] == candidate.correct_index


@_requires_real_draft
def test_real_draft_question_types_follow_level_policy():
    summary = build_dry_run_summary()
    assert summary.errors == []
    for candidate in summary.candidates:
        policy = READING_RESPONSE_TYPE_POLICY[candidate.cefr_level]
        subquestions = candidate.body_json.get("subquestions") or []
        mcq_count = sum(1 for sq in subquestions if (sq.get("response_type") or "mcq") == "mcq")
        gap_count = sum(1 for sq in subquestions if sq.get("response_type") == "gap_fill")
        matching_count = sum(1 for sq in subquestions if sq.get("response_type") == "matching")
        short_count = sum(1 for sq in subquestions if sq.get("response_type") == "short_answer")
        assert mcq_count == policy["mcq"], candidate.draft_id
        assert gap_count == policy["gap_fill"], candidate.draft_id
        assert matching_count == policy["matching"], candidate.draft_id
        assert short_count == policy["short_answer"], candidate.draft_id


# ---------------------------------------------------------------------------
# Synthetic-fixture tests for individual validation rules.
# ---------------------------------------------------------------------------

_VALID_ITEM = """### ITEM RDG-TEST-01
- draft_id: RDG-A1-01
- cefr_level: A1
- question_type: mcq
- reading_subskill: specific_detail
- topic_domain: pets_daily_life
- title: My Cat Milo
- passage: I have a small cat named Milo. He is black and white and sleeps on my bed every night. In the morning, he eats fish and drinks water. After breakfast, he sits near the window and watches people walk to school.
- question: What does Milo eat in the morning?
- options: ["Bread", "Fish", "Eggs", "Cheese"]
- correct_index: 1
- correct_answer: Fish
- explanation: The text says directly that in the morning Milo "eats fish and drinks water".
- distractor_rationale: Bread, eggs and cheese are common breakfast foods but none appears in the text.
- review_status: mvp_approved_pending_full_review
- human_reviewed: false
- body_json_candidate:
```json
{
  "title": "My Cat Milo",
  "topic_domain": "pets_daily_life",
  "reading_subskill": "specific_detail",
  "review_status": "mvp_approved_pending_full_review",
  "human_reviewed": false,
  "distractor_rationale": "Bread, eggs and cheese are common breakfast foods but none appears in the text."
}
```
"""


def _write_draft(tmp_path: Path, *item_blocks: str) -> Path:
    path = tmp_path / "synthetic_draft.md"
    path.write_text("# Synthetic Draft\n\n" + "\n".join(item_blocks), encoding="utf-8")
    return path


_BATCH_LEVEL_FIELDS = {"total_count", "distribution"}


def _valid_subquestions() -> list[dict]:
    return [
        {
            "question": "What does Milo eat in the morning?",
            "options": ["Bread", "Fish", "Eggs", "Cheese"],
            "correct_index": 1,
            "subskill": "specific_detail",
        },
        {
            "question": "Where does Milo sleep?",
            "options": ["On the bed", "In the garden", "Under a chair", "At school"],
            "correct_index": 0,
            "subskill": "specific_detail",
        },
        {
            "question": "What is this text mostly about?",
            "response_type": "gap_fill",
            "accepted_answers": ["A small cat"],
            "max_words": 3,
            "word_bank": ["A small cat", "A red ball", "A sister's room", "Morning food"],
            "subskill": "main_idea",
        },
        {
            "question": "How does the writer feel about Milo?",
            "response_type": "short_answer",
            "accepted_answers": ["The writer likes him"],
            "max_words": 6,
            "subskill": "inference",
        },
    ]


def _with_subquestions(block: str, subquestions: list[dict]) -> str:
    return block.replace(
        '  "human_reviewed": false,\n',
        '  "human_reviewed": false,\n  "subquestions": '
        + json.dumps(subquestions, ensure_ascii=False, indent=2).replace("\n", "\n  ")
        + ",\n",
    )


def test_valid_synthetic_item_passes_with_no_errors(tmp_path):
    # A 1-item synthetic fixture will always fail the 60-item/distribution batch-level checks --
    # this test only asserts that no *per-item* validation error was raised for a well-formed item.
    path = _write_draft(tmp_path, _VALID_ITEM)
    summary = build_dry_run_summary(draft_path=path)
    assert summary.total_parsed == 1
    per_item_errors = [i for i in summary.errors if i.field not in _BATCH_LEVEL_FIELDS]
    assert per_item_errors == []


def test_valid_synthetic_bundle_item_passes_with_no_errors(tmp_path):
    path = _write_draft(tmp_path, _with_subquestions(_VALID_ITEM, _valid_subquestions()))
    summary = build_dry_run_summary(draft_path=path, enforce_batch_totals=False)
    assert summary.errors == []
    assert summary.candidates[0].body_json["subquestions"][0]["subskill"] == "specific_detail"
    assert len(summary.candidates[0].body_json["subquestions"]) == 4


def test_bundle_subquestions_reject_wrong_count(tmp_path):
    path = _write_draft(tmp_path, _with_subquestions(_VALID_ITEM, _valid_subquestions()[:3]))
    summary = build_dry_run_summary(draft_path=path, enforce_batch_totals=False)
    assert any(i.field == "body_json_candidate.subquestions" for i in summary.errors)


def test_first_bundle_subquestion_must_match_visible_question(tmp_path):
    subquestions = _valid_subquestions()
    subquestions[0] = {**subquestions[0], "correct_index": 0}
    path = _write_draft(tmp_path, _with_subquestions(_VALID_ITEM, subquestions))
    summary = build_dry_run_summary(draft_path=path, enforce_batch_totals=False)
    assert any(i.field == "body_json_candidate.subquestions[0].correct_index" for i in summary.errors)


def test_duplicate_draft_id_rejected(tmp_path):
    duplicate_same_id = _VALID_ITEM.replace("### ITEM RDG-TEST-01", "### ITEM RDG-TEST-02")
    path = _write_draft(tmp_path, _VALID_ITEM, duplicate_same_id)
    summary = build_dry_run_summary(draft_path=path)
    assert any(i.field == "draft_id" and "duplicate" in i.message for i in summary.errors)


def test_duplicate_title_rejected(tmp_path):
    second = _VALID_ITEM.replace("RDG-A1-01", "RDG-A1-02").replace("### ITEM RDG-TEST-01", "### ITEM RDG-TEST-02")
    path = _write_draft(tmp_path, _VALID_ITEM, second)
    summary = build_dry_run_summary(draft_path=path)
    assert any(i.field == "title" and "duplicate" in i.message for i in summary.errors)


def test_invalid_option_count_rejected(tmp_path):
    bad = _VALID_ITEM.replace('- options: ["Bread", "Fish", "Eggs", "Cheese"]', '- options: ["Bread", "Fish", "Eggs"]')
    path = _write_draft(tmp_path, bad)
    summary = build_dry_run_summary(draft_path=path)
    assert any(i.field == "options" for i in summary.errors)


def test_invalid_correct_index_rejected(tmp_path):
    bad = _VALID_ITEM.replace("- correct_index: 1", "- correct_index: 7")
    path = _write_draft(tmp_path, bad)
    summary = build_dry_run_summary(draft_path=path)
    assert any(i.field == "correct_index" for i in summary.errors)


def test_correct_answer_not_matching_options_rejected(tmp_path):
    bad = _VALID_ITEM.replace("- correct_answer: Fish", "- correct_answer: Bread")
    path = _write_draft(tmp_path, bad)
    summary = build_dry_run_summary(draft_path=path)
    assert any(i.field == "correct_answer" for i in summary.errors)


def test_missing_required_field_rejected(tmp_path):
    bad = _VALID_ITEM.replace('- explanation: The text says directly that in the morning Milo "eats fish and drinks water".\n', "")
    path = _write_draft(tmp_path, bad)
    summary = build_dry_run_summary(draft_path=path)
    assert any(i.field == "explanation" for i in summary.errors)


def test_wrong_review_status_rejected(tmp_path):
    bad = _VALID_ITEM.replace(
        "- review_status: mvp_approved_pending_full_review", "- review_status: draft"
    )
    path = _write_draft(tmp_path, bad)
    summary = build_dry_run_summary(draft_path=path)
    assert any(i.field == "review_status" for i in summary.errors)


def test_human_reviewed_true_rejected(tmp_path):
    bad = _VALID_ITEM.replace("- human_reviewed: false", "- human_reviewed: true")
    path = _write_draft(tmp_path, bad)
    summary = build_dry_run_summary(draft_path=path)
    assert any(i.field == "human_reviewed" for i in summary.errors)


def test_todo_placeholder_rejected(tmp_path):
    bad = _VALID_ITEM.replace(
        "- explanation: The text says directly that in the morning Milo \"eats fish and drinks water\".",
        "- explanation: TODO write a real explanation.",
    )
    path = _write_draft(tmp_path, bad)
    summary = build_dry_run_summary(draft_path=path)
    assert any(i.field == "explanation" and "placeholder" in i.message for i in summary.errors)


def test_cefr_level_not_matching_draft_id_rejected(tmp_path):
    bad = _VALID_ITEM.replace("- cefr_level: A1", "- cefr_level: B2")
    path = _write_draft(tmp_path, bad)
    summary = build_dry_run_summary(draft_path=path)
    assert any(i.field == "cefr_level" for i in summary.errors)


def test_malformed_draft_id_rejected(tmp_path):
    bad = _VALID_ITEM.replace("- draft_id: RDG-A1-01", "- draft_id: RDG-A1-99")
    path = _write_draft(tmp_path, bad)
    summary = build_dry_run_summary(draft_path=path)
    assert any(i.field == "draft_id" and "pattern" in i.message for i in summary.errors)


def test_body_json_mismatch_with_visible_field_is_flagged(tmp_path):
    bad = _VALID_ITEM.replace('"reading_subskill": "specific_detail",', '"reading_subskill": "main_idea",')
    path = _write_draft(tmp_path, bad)
    summary = build_dry_run_summary(draft_path=path)
    assert any(i.field == "body_json_candidate.reading_subskill" for i in summary.errors)


def test_missing_body_json_fence_rejected(tmp_path):
    import re

    bad = re.sub(r"```json\s*\n.*?\n```\s*\Z", "", _VALID_ITEM, flags=re.DOTALL)
    path = _write_draft(tmp_path, bad)
    summary = build_dry_run_summary(draft_path=path)
    assert any(i.field == "body_json_candidate" for i in summary.errors)


def test_total_count_and_distribution_mismatch_is_flagged(tmp_path):
    path = _write_draft(tmp_path, _VALID_ITEM)
    summary = build_dry_run_summary(draft_path=path)
    assert any(i.field == "total_count" for i in summary.errors)
    assert any(i.field == "distribution" for i in summary.errors)


def test_enforce_batch_totals_false_skips_batch_checks_only(tmp_path):
    path = _write_draft(tmp_path, _VALID_ITEM)
    summary = build_dry_run_summary(draft_path=path, enforce_batch_totals=False)
    assert all(i.field not in _BATCH_LEVEL_FIELDS for i in summary.errors)
    assert summary.errors == []


# ---------------------------------------------------------------------------
# CLI wrapper: dry-run and --apply argument wiring only. Never opens a DB connection.
# ---------------------------------------------------------------------------


def test_cli_apply_flag_is_wired():
    script = REPO_BACKEND_DIR / "scripts" / "seed_reading_bank_mvp_v1.py"
    if not script.exists():
        pytest.skip("backend/scripts/ is not present in this test environment")
    result = subprocess.run(
        [sys.executable, str(script), "--help"],
        cwd=str(REPO_BACKEND_DIR),
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0
    assert "--apply" in result.stdout
    assert "--activate-cutover" in result.stdout


def test_cli_dry_run_succeeds_against_real_draft():
    script = REPO_BACKEND_DIR / "scripts" / "seed_reading_bank_mvp_v1.py"
    if not script.exists() or not DEFAULT_DRAFT_PATH.exists():
        pytest.skip("backend/scripts/ or backend/content_drafts/ is not present in this test environment")
    result = subprocess.run(
        [sys.executable, str(script)],
        cwd=str(REPO_BACKEND_DIR),
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert "DRY-RUN:" in result.stdout
    assert "parsed=60" in result.stdout
    assert result.returncode == 0
    assert "OK: draft is valid" in result.stdout


# ---------------------------------------------------------------------------
# Apply(): DB-write behavior (imports consolidated at the top of this file).
# ---------------------------------------------------------------------------


def _reading_block(draft_id: str, *, passage: str | None = None, subskill: str = "specific_detail") -> str:
    passage = passage or (
        "I have a small cat named Milo. He is black and white and sleeps on my bed every night. "
        "In the morning, he eats fish and drinks water. After breakfast, he sits near the window "
        "and watches people walk to school."
    )
    return f"""### ITEM {draft_id}
- draft_id: {draft_id}
- cefr_level: A1
- question_type: mcq
- reading_subskill: {subskill}
- topic_domain: pets_daily_life
- title: My Cat Milo {draft_id}
- passage: {passage}
- question: What does Milo eat in the morning?
- options: ["Bread", "Fish", "Eggs", "Cheese"]
- correct_index: 1
- correct_answer: Fish
- explanation: The text says directly that in the morning Milo "eats fish and drinks water".
- distractor_rationale: Bread, eggs and cheese are common breakfast foods but none appears in the text.
- review_status: mvp_approved_pending_full_review
- human_reviewed: false
- body_json_candidate:
```json
{{
  "title": "My Cat Milo {draft_id}",
  "topic_domain": "pets_daily_life",
  "reading_subskill": "{subskill}",
  "review_status": "mvp_approved_pending_full_review",
  "human_reviewed": false,
  "distractor_rationale": "Bread, eggs and cheese are common breakfast foods but none appears in the text."
}}
```
"""


@pytest_asyncio.fixture
async def seed_test_language(postgres_session_factory):
    marker = uuid.uuid4().hex[:8]
    code = f"rd{marker}"
    async with postgres_session_factory() as db:
        lang = Language(code=code, name_en="Reading seed test", name_ar="Reading seed test", is_active=True)
        db.add(lang)
        await db.commit()
        language_id = lang.id
    yield code, language_id
    async with postgres_session_factory() as db:
        await db.execute(
            delete(LanguagePlacementQuestionBankItem).where(LanguagePlacementQuestionBankItem.language_id == language_id)
        )
        await db.execute(delete(Language).where(Language.id == language_id))
        await db.commit()


@pytest.mark.postgresql
async def test_dry_run_writes_nothing(tmp_path, postgres_session_factory, seed_test_language):
    code, language_id = seed_test_language
    path = _write_draft(tmp_path, _reading_block("RDG-A1-01"))

    async with postgres_session_factory() as db:
        summary, result = await apply_seed_batch(
            db, language_code=code, apply=False, draft_path=path, enforce_batch_totals=False
        )
    assert summary.errors == []
    assert result is None

    async with postgres_session_factory() as db:
        rows = (
            await db.execute(
                select(LanguagePlacementQuestionBankItem).where(LanguagePlacementQuestionBankItem.language_id == language_id)
            )
        ).scalars().all()
    assert rows == []


@_requires_real_draft
@pytest.mark.postgresql
async def test_apply_inserts_all_60_as_inactive_and_unverified_with_correct_distribution(
    postgres_session_factory, seed_test_language
):
    code, _language_id = seed_test_language

    async with postgres_session_factory() as db:
        summary, result = await apply_seed_batch(db, language_code=code, apply=True)
    assert summary.errors == []
    assert result is not None
    assert result.inserted == EXPECTED_TOTAL
    assert result.updated == 0

    async with postgres_session_factory() as db:
        rows = (
            await db.execute(
                select(LanguagePlacementQuestionBankItem).where(
                    LanguagePlacementQuestionBankItem.stable_key.in_(result.stable_keys)
                )
            )
        ).scalars().all()
    assert len(rows) == EXPECTED_TOTAL
    by_level: dict[str, int] = {}
    for row in rows:
        assert row.is_active is False
        assert row.is_verified is False
        assert row.source == "reading_mvp_v1_draft"
        assert row.skill == "reading"
        assert row.question_type == "mcq"
        by_level[row.level.value] = by_level.get(row.level.value, 0) + 1
    assert by_level == {lvl: EXPECTED_PER_LEVEL for lvl in EXPECTED_LEVELS}


@pytest.mark.postgresql
async def test_apply_is_idempotent_and_stable_key_prevents_duplicates(tmp_path, postgres_session_factory, seed_test_language):
    code, _language_id = seed_test_language
    draft_id = "RDG-A1-01"
    path = _write_draft(tmp_path, _reading_block(draft_id))

    async with postgres_session_factory() as db:
        _summary1, result1 = await apply_seed_batch(
            db, language_code=code, apply=True, draft_path=path, enforce_batch_totals=False
        )
    assert result1.inserted == 1 and result1.updated == 0

    async with postgres_session_factory() as db:
        _summary2, result2 = await apply_seed_batch(
            db, language_code=code, apply=True, draft_path=path, enforce_batch_totals=False
        )
    assert result2.inserted == 0 and result2.updated == 1

    async with postgres_session_factory() as db:
        rows = (
            await db.execute(
                select(LanguagePlacementQuestionBankItem).where(
                    LanguagePlacementQuestionBankItem.stable_key == f"{STABLE_KEY_PREFIX}:{draft_id}"
                )
            )
        ).scalars().all()
    assert len(rows) == 1  # never duplicated on rerun


@pytest.mark.postgresql
async def test_apply_updates_content_fields_only(tmp_path, postgres_session_factory, seed_test_language):
    code, _language_id = seed_test_language
    draft_id = "RDG-A1-01"
    old_passage = (
        "I have a small cat named Milo. He is black and white and sleeps on my bed every night. "
        "In the morning, he eats fish and drinks water. After breakfast, he sits near the door "
        "and watches people walk to school."
    )
    path_v1 = _write_draft(tmp_path, _reading_block(draft_id, passage=old_passage))

    async with postgres_session_factory() as db:
        await apply_seed_batch(db, language_code=code, apply=True, draft_path=path_v1, enforce_batch_totals=False)

    new_passage = (
        "I have a small cat named Milo. He is black and white and sleeps on my bed every night. "
        "In the morning, he eats fresh fish and drinks water. After breakfast, he sits near the "
        "window and watches people walk to school."
    )
    path_v2 = _write_draft(tmp_path, _reading_block(draft_id, passage=new_passage, subskill="main_idea"))
    async with postgres_session_factory() as db:
        summary, result = await apply_seed_batch(
            db, language_code=code, apply=True, draft_path=path_v2, enforce_batch_totals=False
        )
    assert summary.errors == []
    assert result.inserted == 0 and result.updated == 1

    async with postgres_session_factory() as db:
        row = (
            await db.execute(
                select(LanguagePlacementQuestionBankItem).where(
                    LanguagePlacementQuestionBankItem.stable_key == f"{STABLE_KEY_PREFIX}:{draft_id}"
                )
            )
        ).scalar_one()
    assert row.passage == new_passage
    assert row.subskill == "main_idea"


@pytest.mark.postgresql
async def test_apply_rerun_never_resets_is_active_or_is_verified_once_a_human_has_set_them(
    tmp_path, postgres_session_factory, seed_test_language
):
    code, _language_id = seed_test_language
    draft_id = "RDG-A1-01"
    path = _write_draft(tmp_path, _reading_block(draft_id))

    async with postgres_session_factory() as db:
        await apply_seed_batch(db, language_code=code, apply=True, draft_path=path, enforce_batch_totals=False)

    # Simulate a later, separate, deliberate human activation step.
    async with postgres_session_factory() as db:
        row = (
            await db.execute(
                select(LanguagePlacementQuestionBankItem).where(
                    LanguagePlacementQuestionBankItem.stable_key == f"{STABLE_KEY_PREFIX}:{draft_id}"
                )
            )
        ).scalar_one()
        row.is_verified = True
        row.is_active = True
        await db.commit()

    # A routine content-sync re-run must never reset that decision.
    async with postgres_session_factory() as db:
        await apply_seed_batch(db, language_code=code, apply=True, draft_path=path, enforce_batch_totals=False)

    async with postgres_session_factory() as db:
        row = (
            await db.execute(
                select(LanguagePlacementQuestionBankItem).where(
                    LanguagePlacementQuestionBankItem.stable_key == f"{STABLE_KEY_PREFIX}:{draft_id}"
                )
            )
        ).scalar_one()
    assert row.is_active is True
    assert row.is_verified is True


@pytest.mark.postgresql
async def test_apply_rerun_never_resets_calibration_counters(tmp_path, postgres_session_factory, seed_test_language):
    code, _language_id = seed_test_language
    draft_id = "RDG-A1-01"
    path = _write_draft(tmp_path, _reading_block(draft_id))

    async with postgres_session_factory() as db:
        await apply_seed_batch(db, language_code=code, apply=True, draft_path=path, enforce_batch_totals=False)

    # Simulate accrued usage after activation.
    async with postgres_session_factory() as db:
        row = (
            await db.execute(
                select(LanguagePlacementQuestionBankItem).where(
                    LanguagePlacementQuestionBankItem.stable_key == f"{STABLE_KEY_PREFIX}:{draft_id}"
                )
            )
        ).scalar_one()
        row.usage_count = 17
        row.correct_count = 9
        row.difficulty_estimate = 0.42
        await db.commit()

    async with postgres_session_factory() as db:
        await apply_seed_batch(db, language_code=code, apply=True, draft_path=path, enforce_batch_totals=False)

    async with postgres_session_factory() as db:
        row = (
            await db.execute(
                select(LanguagePlacementQuestionBankItem).where(
                    LanguagePlacementQuestionBankItem.stable_key == f"{STABLE_KEY_PREFIX}:{draft_id}"
                )
            )
        ).scalar_one()
    assert row.usage_count == 17
    assert row.correct_count == 9
    assert row.difficulty_estimate == 0.42


@pytest.mark.postgresql
async def test_apply_maps_passage_options_and_correct_index(tmp_path, postgres_session_factory, seed_test_language):
    code, _language_id = seed_test_language
    draft_id = "RDG-A1-01"
    path = _write_draft(tmp_path, _reading_block(draft_id))

    async with postgres_session_factory() as db:
        await apply_seed_batch(db, language_code=code, apply=True, draft_path=path, enforce_batch_totals=False)
        row = (
            await db.execute(
                select(LanguagePlacementQuestionBankItem).where(
                    LanguagePlacementQuestionBankItem.stable_key == f"{STABLE_KEY_PREFIX}:{draft_id}"
                )
            )
        ).scalar_one()

    assert row.options_json == ["Bread", "Fish", "Eggs", "Cheese"]
    assert row.correct_index == 1
    assert row.question_type == "mcq"
    assert row.level == LanguageLevel.A1
    assert row.subskill == "specific_detail"
    assert "Milo" in row.passage
    assert row.explanation
    assert "draft_id" not in (row.body_json or {})
    assert "id" not in (row.body_json or {})
    metrics = (row.body_json or {}).get("placement_metrics") or {}
    assert metrics["cefr_level"] == "A1"
    assert metrics["subskill"] == "specific_detail"
    assert metrics["word_count"] > 0
    assert metrics["sentence_count"] > 0
    assert metrics["avg_sentence_words"] > 0
    assert metrics["difficulty_profile"]["word_count_min"] == 35
    assert metrics["difficulty_profile"]["word_count_max"] == 65


@pytest.mark.postgresql
async def test_boundary_seed_inserts_active_verified_boundary_rows(postgres_session_factory, seed_test_language):
    code, language_id = seed_test_language

    async with postgres_session_factory() as db:
        result = await seed_reading_boundary_v1(db, language_code=code, activate=True)

    assert result is not None
    assert result.inserted == 10
    assert result.updated == 0
    assert result.activated_rows == 10
    assert result.active_boundary_rows == 10

    async with postgres_session_factory() as db:
        rows = (
            await db.execute(
                select(LanguagePlacementQuestionBankItem).where(
                    LanguagePlacementQuestionBankItem.language_id == language_id,
                    LanguagePlacementQuestionBankItem.source == BOUNDARY_SOURCE,
                )
            )
        ).scalars().all()

    assert len(rows) == 10
    assert {row.skill for row in rows} == {"reading"}
    assert all(row.is_active and row.is_verified for row in rows)
    assert {row.boundary_low_level.value for row in rows} == {"A1", "A2", "B1", "B2", "C1"}
    assert {row.boundary_high_level.value for row in rows} == {"A2", "B1", "B2", "C1", "C2"}
    assert all((row.body_json or {}).get("placement_metrics", {}).get("word_count") for row in rows)


@pytest.mark.postgresql
async def test_boundary_seed_is_idempotent(postgres_session_factory, seed_test_language):
    code, _language_id = seed_test_language

    async with postgres_session_factory() as db:
        first = await seed_reading_boundary_v1(db, language_code=code, activate=True)
    async with postgres_session_factory() as db:
        second = await seed_reading_boundary_v1(db, language_code=code, activate=True)

    assert first is not None
    assert second is not None
    assert first.inserted == 10
    assert second.inserted == 0
    assert second.updated == 10
    assert second.activated_rows == 0
    assert second.active_boundary_rows == 10


@pytest.mark.postgresql
async def test_apply_refuses_when_validation_has_errors(tmp_path, postgres_session_factory, seed_test_language):
    code, _language_id = seed_test_language
    draft_id = "RDG-A1-01"
    bad = _reading_block(draft_id).replace(
        '- options: ["Bread", "Fish", "Eggs", "Cheese"]', '- options: ["Bread", "Fish", "Eggs"]'
    )
    path = _write_draft(tmp_path, bad)

    async with postgres_session_factory() as db:
        summary, result = await apply_seed_batch(
            db, language_code=code, apply=True, draft_path=path, enforce_batch_totals=False
        )
        rows = (
            await db.execute(
                select(LanguagePlacementQuestionBankItem).where(
                    LanguagePlacementQuestionBankItem.stable_key == f"{STABLE_KEY_PREFIX}:{draft_id}"
                )
            )
        ).scalars().all()

    assert not summary.is_valid
    assert result is None
    assert rows == []  # nothing was written


@pytest.mark.postgresql
async def test_apply_refuses_when_draft_id_is_duplicated(tmp_path, postgres_session_factory, seed_test_language):
    code, _language_id = seed_test_language
    draft_id = "RDG-A1-01"
    block_a = _reading_block(draft_id).replace("### ITEM RDG-A1-", "### ITEM RDG-A1-DUP-", 1)
    block_b = _reading_block(draft_id).replace("### ITEM RDG-A1-", "### ITEM RDG-A1-DUP2-", 1)
    path = _write_draft(tmp_path, block_a, block_b)

    async with postgres_session_factory() as db:
        summary, result = await apply_seed_batch(
            db, language_code=code, apply=True, draft_path=path, enforce_batch_totals=False
        )
        rows = (
            await db.execute(
                select(LanguagePlacementQuestionBankItem).where(
                    LanguagePlacementQuestionBankItem.stable_key == f"{STABLE_KEY_PREFIX}:{draft_id}"
                )
            )
        ).scalars().all()

    assert not summary.is_valid
    assert any(i.field == "draft_id" and "duplicate" in i.message for i in summary.errors)
    assert result is None
    assert rows == []


@pytest.mark.postgresql
async def test_old_content_seed_reading_rows_are_not_modified(tmp_path, postgres_session_factory, seed_test_language):
    code, language_id = seed_test_language
    marker = uuid.uuid4().hex[:8]

    async with postgres_session_factory() as db:
        old_row = LanguagePlacementQuestionBankItem(
            language_id=language_id,
            skill="reading",
            level=LanguageLevel.A1,
            question_type="mcq",
            prompt_text="Old content-seed question?",
            passage="Old content-seed passage.",
            options_json=["A", "B", "C", "D"],
            correct_index=0,
            subskill="comprehension",
            stable_key=f"content:{marker}",
            source="content_seed",
            is_active=True,
            is_verified=True,
            usage_count=5,
            correct_count=3,
            body_json={"title": "Old Content", "content_item_id": 999},
        )
        db.add(old_row)
        await db.commit()
        old_row_id = old_row.id

    draft_id = "RDG-A1-01"
    path = _write_draft(tmp_path, _reading_block(draft_id))
    async with postgres_session_factory() as db:
        await apply_seed_batch(db, language_code=code, apply=True, draft_path=path, enforce_batch_totals=False)

    async with postgres_session_factory() as db:
        old_row = (
            await db.execute(
                select(LanguagePlacementQuestionBankItem).where(LanguagePlacementQuestionBankItem.id == old_row_id)
            )
        ).scalar_one()
    assert old_row.stable_key == f"content:{marker}"
    assert old_row.source == "content_seed"
    assert old_row.is_active is True
    assert old_row.is_verified is True
    assert old_row.usage_count == 5
    assert old_row.correct_count == 3
    assert old_row.passage == "Old content-seed passage."
    assert old_row.body_json == {"title": "Old Content", "content_item_id": 999}


@pytest.mark.postgresql
async def test_no_non_reading_skill_rows_are_modified(tmp_path, postgres_session_factory, seed_test_language):
    code, language_id = seed_test_language
    marker = uuid.uuid4().hex[:8]

    async with postgres_session_factory() as db:
        listening_row = LanguagePlacementQuestionBankItem(
            language_id=language_id,
            skill="listening",
            level=LanguageLevel.A1,
            question_type="mcq",
            prompt_text="Unrelated listening question?",
            options_json=["A", "B", "C", "D"],
            correct_index=0,
            subskill="explicit_detail",
            stable_key=f"listening_mvp_60:LST-UNRELATED-{marker}",
            source="listening_mvp_60_draft",
            is_active=False,
            is_verified=False,
            body_json={"transcript": "unrelated"},
        )
        db.add(listening_row)
        await db.commit()
        listening_row_id = listening_row.id

    draft_id = "RDG-A1-01"
    path = _write_draft(tmp_path, _reading_block(draft_id))
    async with postgres_session_factory() as db:
        await apply_seed_batch(db, language_code=code, apply=True, draft_path=path, enforce_batch_totals=False)

    async with postgres_session_factory() as db:
        listening_row = (
            await db.execute(
                select(LanguagePlacementQuestionBankItem).where(LanguagePlacementQuestionBankItem.id == listening_row_id)
            )
        ).scalar_one()
    assert listening_row.skill == "listening"
    assert listening_row.source == "listening_mvp_60_draft"
    assert listening_row.body_json == {"transcript": "unrelated"}


@pytest.mark.postgresql
async def test_cutover_activates_mvp_rows_and_retires_old_content_seed_reading(
    tmp_path, postgres_session_factory, seed_test_language
):
    code, language_id = seed_test_language
    marker = uuid.uuid4().hex[:8]
    draft_id = "RDG-A1-01"
    path = _write_draft(tmp_path, _reading_block(draft_id))

    async with postgres_session_factory() as db:
        old_row = LanguagePlacementQuestionBankItem(
            language_id=language_id,
            skill="reading",
            level=LanguageLevel.A1,
            question_type="mcq",
            prompt_text="Old content-seed question?",
            passage="Old content-seed passage.",
            options_json=["A", "B", "C", "D"],
            correct_index=0,
            subskill="comprehension",
            stable_key=f"content:{marker}",
            source="content_seed",
            is_active=True,
            is_verified=True,
        )
        db.add(old_row)
        await db.commit()
        old_row_id = old_row.id

    async with postgres_session_factory() as db:
        summary, result = await activate_reading_mvp_v1_cutover(
            db,
            language_code=code,
            draft_path=path,
            enforce_batch_totals=False,
        )

    assert summary.errors == []
    assert result is not None
    assert result.inserted == 1
    assert result.activated_mvp_rows == 1
    assert result.retired_content_seed_rows == 1
    assert result.active_mvp_rows == 1
    assert result.active_content_seed_rows == 0
    assert result.boundary_inserted == 10
    assert result.boundary_updated == 0
    assert result.boundary_activated_rows == 10
    assert result.active_boundary_rows == 10

    async with postgres_session_factory() as db:
        mvp_row = (
            await db.execute(
                select(LanguagePlacementQuestionBankItem).where(
                    LanguagePlacementQuestionBankItem.stable_key == f"{STABLE_KEY_PREFIX}:{draft_id}"
                )
            )
        ).scalar_one()
        old_row = (
            await db.execute(
                select(LanguagePlacementQuestionBankItem).where(LanguagePlacementQuestionBankItem.id == old_row_id)
            )
        ).scalar_one()
        boundary_rows = (
            await db.execute(
                select(LanguagePlacementQuestionBankItem).where(
                    LanguagePlacementQuestionBankItem.language_id == language_id,
                    LanguagePlacementQuestionBankItem.source == BOUNDARY_SOURCE,
                )
            )
        ).scalars().all()

    assert mvp_row.is_active is True
    assert mvp_row.is_verified is True
    assert old_row.is_active is False
    assert old_row.is_verified is True
    assert len(boundary_rows) == 10
    assert all(row.is_active and row.is_verified for row in boundary_rows)


@pytest.mark.postgresql
async def test_cutover_is_idempotent(tmp_path, postgres_session_factory, seed_test_language):
    code, _language_id = seed_test_language
    draft_id = "RDG-A1-01"
    path = _write_draft(tmp_path, _reading_block(draft_id))

    async with postgres_session_factory() as db:
        _summary1, first = await activate_reading_mvp_v1_cutover(
            db,
            language_code=code,
            draft_path=path,
            enforce_batch_totals=False,
        )
    async with postgres_session_factory() as db:
        summary2, second = await activate_reading_mvp_v1_cutover(
            db,
            language_code=code,
            draft_path=path,
            enforce_batch_totals=False,
        )

    assert first is not None
    assert summary2.errors == []
    assert second is not None
    assert second.inserted == 0
    assert second.updated == 1
    assert second.activated_mvp_rows == 0
    assert second.retired_content_seed_rows == 0
    assert second.active_mvp_rows == 1
    assert second.boundary_inserted == 0
    assert second.boundary_updated == 10
    assert second.boundary_activated_rows == 0
    assert second.active_boundary_rows == 10
