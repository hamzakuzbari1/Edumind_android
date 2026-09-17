"""Phase 1 (dry-run parse/validate) and Phase 2A (apply, DB-backed) tests for the Listening
draft-to-bank seed service.

Phase 1 tests never touch a database -- they only exercise the pure parse/validate logic in
app/services/language_listening_bank_seed_service.py, either against the real draft file (for the
count/distribution checks) or against small synthetic in-memory markdown fixtures (for individual
validation-rule checks), matching the existing repo convention of not requiring Postgres for
pure-logic tests.

Phase 2A tests (`@pytest.mark.postgresql`, near the end of this file) exercise apply_seed_batch()
directly against the dedicated Postgres *_test* database -- never via the CLI script, never
against a real/dev database. Every test uses a throwaway Language row and unique synthetic
draft_ids (stable_key has a global-uniqueness constraint, not namespaced by language) so tests can
never collide with each other or with any real bank row; real rows never use
source="listening_mvp_60_draft" or a "listening_mvp_60:" stable_key prefix.
"""

from __future__ import annotations

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
from app.services.language_listening_bank_audio_backfill_service import run_backfill
from app.services.language_listening_bank_seed_service import (
    DEFAULT_DRAFT_PATH,
    EXPECTED_DISTRIBUTION,
    EXPECTED_GAP_FILL_TOTAL,
    EXPECTED_MCQ_TOTAL,
    EXPECTED_TOTAL,
    STABLE_KEY_PREFIX,
    SeedCandidate,
    apply_seed_batch,
    build_dry_run_summary,
    parse_draft_file,
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
def test_parses_exactly_42_items():
    summary = build_dry_run_summary()
    assert summary.total_parsed == EXPECTED_TOTAL
    assert len(summary.candidates) == EXPECTED_TOTAL


@_requires_real_draft
def test_distribution_matches_spec():
    summary = build_dry_run_summary()
    assert summary.distribution == EXPECTED_DISTRIBUTION
    mcq_total = sum(v for (_lvl, qt), v in summary.distribution.items() if qt == "mcq")
    gap_fill_total = sum(v for (_lvl, qt), v in summary.distribution.items() if qt == "gap_fill")
    assert mcq_total == EXPECTED_MCQ_TOTAL
    assert gap_fill_total == EXPECTED_GAP_FILL_TOTAL


@_requires_real_draft
def test_candidates_default_to_inactive_and_unverified():
    summary = build_dry_run_summary()
    assert summary.candidates, "expected at least one candidate to check defaults on"
    for candidate in summary.candidates:
        assert candidate.is_active is False
        assert candidate.is_verified is False
        assert candidate.source == "listening_mvp_60_draft"
        assert candidate.skill == "listening"


@_requires_real_draft
def test_stable_key_format_is_correct():
    summary = build_dry_run_summary()
    for candidate in summary.candidates:
        assert candidate.stable_key == f"{STABLE_KEY_PREFIX}:{candidate.draft_id}"
        assert candidate.stable_key.startswith("listening_mvp_60:LST-")


@_requires_real_draft
def test_draft_id_never_used_as_a_database_id():
    summary = build_dry_run_summary()
    for candidate in summary.candidates:
        assert "id" not in candidate.body_json
        assert "bank_item_id" not in candidate.body_json
        assert "draft_id" not in candidate.body_json
        # draft_id itself is a plain string identifier, never coerced to/used as an integer id
        assert isinstance(candidate.draft_id, str)


# Phase 5C content invariant: Gap Fill must stay explicit/extractable (per the product rule),
# never used for nuanced inference, speaker attitude, implied meaning, or abstract argument --
# those listening_skill tags are reserved for MCQ items. Content itself is not modified by this
# phase; this only proves the already-authored 21 Gap Fill items still respect the rule, so a
# future content addition that violates it would fail this test rather than going unnoticed.
_DISALLOWED_GAP_FILL_LISTENING_SKILLS = {
    "inference",
    "implied_meaning",
    "speaker_attitude",
    "following_argument",
}


@_requires_real_draft
def test_gap_fill_items_never_use_inappropriate_listening_skill_tags():
    raw_items = parse_draft_file()
    gap_fill_items = [r for r in raw_items if r.get("question_type") == "gap_fill"]
    assert gap_fill_items, "expected at least one gap_fill item in the draft"
    offending = [
        r.get("draft_id") for r in gap_fill_items
        if r.get("listening_skill") in _DISALLOWED_GAP_FILL_LISTENING_SKILLS
    ]
    assert offending == []


# ---------------------------------------------------------------------------
# Synthetic-fixture tests for individual validation rules.
# ---------------------------------------------------------------------------

_VALID_MCQ_ITEM = """### ITEM LST-TEST-01
- draft_id: LST-TEST-01
- cefr_level: A1
- question_type: mcq
- listening_skill: explicit_detail
- secondary_skill: (none)
- audio_context: classroom
- discourse_type: dialogue
- speakers: 2 (teacher, student)
- transcript: "Hello, what is your name?" "My name is Sam."
- transcript_word_count: 10
- target_duration_seconds: 6
- situation: A short classroom exchange.
- prompt_or_question: What is the student's name?
- options: ["Sam", "Tom", "Ann", "Kim"]
- correct_index: 0
- correct_answer: Sam
- rationale: The student states his name directly.
- distractor_rationale: Other names are plausible but unsupported.
- review_status: mvp_approved_pending_full_review
- human_reviewed: false
- audio_generation_status: not_generated
- authoring_notes: Synthetic test fixture.
- estimated_cefr_justification: Simple, direct fact.
- body_json_candidate:
```json
{
  "question_type": "mcq",
  "transcript": "Hello, what is your name? My name is Sam.",
  "situation": "A short classroom exchange.",
  "question": "What is the student's name?",
  "options": ["Sam", "Tom", "Ann", "Kim"],
  "correct_index": 0,
  "review_status": "mvp_approved_pending_full_review",
  "human_reviewed": false,
  "audio_generation_status": "not_generated",
  "listening_skill": "explicit_detail",
  "secondary_skill": null,
  "audio_context": "classroom",
  "discourse_type": "dialogue",
  "rationale": "The student states his name directly.",
  "distractor_rationale": "Other names are plausible but unsupported."
}
```
"""

_VALID_GAP_FILL_ITEM = """### ITEM LST-TEST-02
- draft_id: LST-TEST-02
- cefr_level: A1
- question_type: gap_fill
- listening_skill: number_time_price
- secondary_skill: (none)
- audio_context: everyday conversation
- discourse_type: dialogue
- speakers: 2 (friends)
- transcript: "What time is it?" "It's five o'clock."
- transcript_word_count: 8
- target_duration_seconds: 5
- situation: Two friends check the time.
- prompt_or_question: What time is it?
- accepted_answers: ["five", "5"]
- max_words: 1
- case_sensitive: false
- word_bank: ["five", "six", "seven"]
- correct_answer: five
- rationale: The speaker states the time directly.
- review_status: mvp_approved_pending_full_review
- human_reviewed: false
- audio_generation_status: not_generated
- authoring_notes: Synthetic test fixture.
- estimated_cefr_justification: Simple, direct fact.
- body_json_candidate:
```json
{
  "question_type": "gap_fill",
  "transcript": "What time is it? It's five o'clock.",
  "situation": "Two friends check the time.",
  "prompt": "What time is it?",
  "accepted_answers": ["five", "5"],
  "max_words": 1,
  "case_sensitive": false,
  "word_bank": ["five", "six", "seven"],
  "review_status": "mvp_approved_pending_full_review",
  "human_reviewed": false,
  "audio_generation_status": "not_generated",
  "listening_skill": "number_time_price",
  "secondary_skill": null,
  "audio_context": "everyday_conversation",
  "discourse_type": "dialogue",
  "rationale": "The speaker states the time directly."
}
```
"""


def _write_draft(tmp_path: Path, *item_blocks: str) -> Path:
    path = tmp_path / "synthetic_draft.md"
    path.write_text("# Synthetic Draft\n\n" + "\n".join(item_blocks), encoding="utf-8")
    return path


_BATCH_LEVEL_FIELDS = {"total_count", "distribution", "mcq_total", "gap_fill_total"}


def test_valid_synthetic_items_pass_with_no_errors(tmp_path):
    # A 2-item synthetic fixture will always fail the 42-item/distribution batch-level checks --
    # this test only asserts that no *per-item* validation error was raised for well-formed items.
    path = _write_draft(tmp_path, _VALID_MCQ_ITEM, _VALID_GAP_FILL_ITEM)
    summary = build_dry_run_summary(draft_path=path)
    assert summary.total_parsed == 2
    per_item_errors = [i for i in summary.errors if i.field not in _BATCH_LEVEL_FIELDS]
    assert per_item_errors == []


def test_candidates_include_audio_transcript_copied_from_transcript(tmp_path):
    path = _write_draft(tmp_path, _VALID_MCQ_ITEM, _VALID_GAP_FILL_ITEM)
    summary = build_dry_run_summary(draft_path=path)
    assert len(summary.candidates) == 2
    for candidate in summary.candidates:
        assert candidate.body_json.get("audio_transcript") == candidate.body_json.get("transcript")


def test_candidates_audio_transcript_is_non_empty(tmp_path):
    path = _write_draft(tmp_path, _VALID_MCQ_ITEM, _VALID_GAP_FILL_ITEM)
    summary = build_dry_run_summary(draft_path=path)
    for candidate in summary.candidates:
        audio_transcript = candidate.body_json.get("audio_transcript")
        assert isinstance(audio_transcript, str) and audio_transcript.strip()


def test_candidates_preserve_original_transcript_key(tmp_path):
    path = _write_draft(tmp_path, _VALID_MCQ_ITEM, _VALID_GAP_FILL_ITEM)
    summary = build_dry_run_summary(draft_path=path)
    for candidate in summary.candidates:
        assert "transcript" in candidate.body_json
        assert candidate.body_json["transcript"]


def test_missing_or_empty_audio_transcript_is_flagged_as_an_error(tmp_path):
    # A candidate whose body_json_candidate never had a "transcript" key at all (and so gets no
    # audio_transcript mirrored either) must fail validation rather than silently seeding an
    # unusable row.
    bad = _VALID_MCQ_ITEM.replace(
        '  "transcript": "Hello, what is your name? My name is Sam.",\n', ""
    )
    path = _write_draft(tmp_path, bad)
    summary = build_dry_run_summary(draft_path=path)
    assert any(i.field == "body_json.audio_transcript" for i in summary.errors)


def test_duplicate_draft_id_rejected(tmp_path):
    duplicate = _VALID_MCQ_ITEM.replace("LST-TEST-01", "LST-TEST-02", 1).replace(
        "cefr_level: A1", "cefr_level: A1", 1
    )
    # Force an actual duplicate of the same draft_id, not a relabelled copy.
    duplicate_same_id = _VALID_GAP_FILL_ITEM.replace("LST-TEST-02", "LST-TEST-01")
    path = _write_draft(tmp_path, _VALID_MCQ_ITEM, duplicate_same_id)
    summary = build_dry_run_summary(draft_path=path)
    assert any(i.field == "draft_id" and "duplicate" in i.message for i in summary.errors)


def test_invalid_mcq_option_count_rejected(tmp_path):
    bad = _VALID_MCQ_ITEM.replace(
        '"options": ["Sam", "Tom", "Ann", "Kim"],',
        '"options": ["Sam", "Tom", "Ann"],',
    ).replace(
        '- options: ["Sam", "Tom", "Ann", "Kim"]',
        '- options: ["Sam", "Tom", "Ann"]',
    )
    path = _write_draft(tmp_path, bad)
    summary = build_dry_run_summary(draft_path=path)
    assert any(i.field == "options" for i in summary.errors)


def test_invalid_mcq_correct_index_rejected(tmp_path):
    bad = _VALID_MCQ_ITEM.replace("- correct_index: 0", "- correct_index: 7").replace(
        '"correct_index": 0,', '"correct_index": 7,'
    )
    path = _write_draft(tmp_path, bad)
    summary = build_dry_run_summary(draft_path=path)
    assert any(i.field == "correct_index" for i in summary.errors)


def test_gap_fill_missing_accepted_answers_rejected(tmp_path):
    bad = _VALID_GAP_FILL_ITEM.replace(
        '- accepted_answers: ["five", "5"]\n', ""
    ).replace(
        '  "accepted_answers": ["five", "5"],\n', ""
    )
    path = _write_draft(tmp_path, bad)
    summary = build_dry_run_summary(draft_path=path)
    assert any(i.field == "accepted_answers" for i in summary.errors)


def test_gap_fill_accepted_answer_exceeding_max_words_rejected(tmp_path):
    bad = _VALID_GAP_FILL_ITEM.replace(
        '- accepted_answers: ["five", "5"]', '- accepted_answers: ["five", "five o clock exactly"]'
    ).replace(
        '"accepted_answers": ["five", "5"],', '"accepted_answers": ["five", "five o clock exactly"],'
    )
    path = _write_draft(tmp_path, bad)
    summary = build_dry_run_summary(draft_path=path)
    assert any(i.field == "accepted_answers" and "exceeds max_words" in i.message for i in summary.errors)


def test_gap_fill_word_bank_option_exceeding_max_words_rejected(tmp_path):
    bad = _VALID_GAP_FILL_ITEM.replace(
        '- word_bank: ["five", "six", "seven"]', '- word_bank: ["five", "six", "seven o clock"]'
    ).replace(
        '"word_bank": ["five", "six", "seven"],', '"word_bank": ["five", "six", "seven o clock"],'
    )
    path = _write_draft(tmp_path, bad)
    summary = build_dry_run_summary(draft_path=path)
    assert any(i.field == "word_bank" and "exceeds max_words" in i.message for i in summary.errors)


def test_a1_a2_gap_fill_without_word_bank_rejected(tmp_path):
    bad = _VALID_GAP_FILL_ITEM.replace(
        '- word_bank: ["five", "six", "seven"]', "- word_bank: null"
    ).replace(
        '"word_bank": ["five", "six", "seven"],', '"word_bank": null,'
    )
    path = _write_draft(tmp_path, bad)
    summary = build_dry_run_summary(draft_path=path)
    assert any(i.field == "word_bank" and "require a non-empty word_bank" in i.message for i in summary.errors)


def test_b1_and_above_gap_fill_without_word_bank_is_allowed(tmp_path):
    ok = _VALID_GAP_FILL_ITEM.replace("cefr_level: A1", "cefr_level: B1").replace(
        '- word_bank: ["five", "six", "seven"]', "- word_bank: null"
    ).replace(
        '"word_bank": ["five", "six", "seven"],', '"word_bank": null,'
    )
    path = _write_draft(tmp_path, ok)
    summary = build_dry_run_summary(draft_path=path)
    assert not any(i.field == "word_bank" for i in summary.errors)


def test_case_sensitive_true_rejected(tmp_path):
    bad = _VALID_GAP_FILL_ITEM.replace("- case_sensitive: false", "- case_sensitive: true").replace(
        '"case_sensitive": false,', '"case_sensitive": true,'
    )
    path = _write_draft(tmp_path, bad)
    summary = build_dry_run_summary(draft_path=path)
    assert any(i.field == "case_sensitive" for i in summary.errors)


def test_body_json_mismatch_with_visible_fields_is_flagged(tmp_path):
    bad = _VALID_MCQ_ITEM.replace(
        '"audio_context": "classroom",', '"audio_context": "shopping",'
    )
    path = _write_draft(tmp_path, bad)
    summary = build_dry_run_summary(draft_path=path)
    assert any("audio_context" in i.field for i in summary.errors)


def test_total_count_mismatch_is_flagged(tmp_path):
    path = _write_draft(tmp_path, _VALID_MCQ_ITEM)
    summary = build_dry_run_summary(draft_path=path)
    assert any(i.field == "total_count" for i in summary.errors)
    assert any(i.field == "distribution" for i in summary.errors)


# ---------------------------------------------------------------------------
# CLI wrapper: --apply is now wired (Phase 2A), superseding Phase 1's "not implemented" rejection.
# This only checks --help/argument wiring -- it never opens a DB connection, so it cannot write
# anywhere. Actual --apply DB behavior is covered by the apply_seed_batch() tests below, called
# directly against the test database, never via this CLI script.
# ---------------------------------------------------------------------------


def test_cli_apply_flag_is_wired_not_rejected():
    script = REPO_BACKEND_DIR / "scripts" / "seed_listening_bank_expansion.py"
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
    assert "not implemented" not in result.stdout.lower()


def test_cli_dry_run_succeeds_against_real_draft():
    script = REPO_BACKEND_DIR / "scripts" / "seed_listening_bank_expansion.py"
    if not script.exists() or not DEFAULT_DRAFT_PATH.exists():
        pytest.skip("backend/scripts/ or backend/content_drafts/ is not present in this test environment")
    result = subprocess.run(
        [sys.executable, str(script)],
        cwd=str(REPO_BACKEND_DIR),
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert "DRY-RUN: parsed=42" in result.stdout


# ---------------------------------------------------------------------------
# Phase 2A: apply_seed_batch() DB-write behavior (imports consolidated at the top of this file).
# ---------------------------------------------------------------------------


def _mcq_block(draft_id: str) -> str:
    return f"""### ITEM {draft_id}
- draft_id: {draft_id}
- cefr_level: A1
- question_type: mcq
- listening_skill: explicit_detail
- secondary_skill: (none)
- audio_context: classroom
- discourse_type: dialogue
- speakers: 2 (teacher, student)
- transcript: "Hello, what is your name?" "My name is Sam."
- transcript_word_count: 10
- target_duration_seconds: 6
- situation: A short classroom exchange.
- prompt_or_question: What is the student's name?
- options: ["Sam", "Tom", "Ann", "Kim"]
- correct_index: 0
- correct_answer: Sam
- rationale: The student states his name directly.
- distractor_rationale: Other names are plausible but unsupported.
- review_status: mvp_approved_pending_full_review
- human_reviewed: false
- audio_generation_status: not_generated
- authoring_notes: Synthetic test fixture.
- estimated_cefr_justification: Simple, direct fact.
- body_json_candidate:
```json
{{
  "question_type": "mcq",
  "transcript": "Hello, what is your name? My name is Sam.",
  "situation": "A short classroom exchange.",
  "question": "What is the student's name?",
  "options": ["Sam", "Tom", "Ann", "Kim"],
  "correct_index": 0,
  "review_status": "mvp_approved_pending_full_review",
  "human_reviewed": false,
  "audio_generation_status": "not_generated",
  "listening_skill": "explicit_detail",
  "secondary_skill": null,
  "audio_context": "classroom",
  "discourse_type": "dialogue",
  "rationale": "The student states his name directly.",
  "distractor_rationale": "Other names are plausible but unsupported."
}}
```
"""


def _gap_fill_block(draft_id: str) -> str:
    return f"""### ITEM {draft_id}
- draft_id: {draft_id}
- cefr_level: A1
- question_type: gap_fill
- listening_skill: number_time_price
- secondary_skill: (none)
- audio_context: everyday conversation
- discourse_type: dialogue
- speakers: 2 (friends)
- transcript: "What time is it?" "It's five o'clock."
- transcript_word_count: 8
- target_duration_seconds: 5
- situation: Two friends check the time.
- prompt_or_question: What time is it?
- accepted_answers: ["five", "5"]
- max_words: 1
- case_sensitive: false
- word_bank: ["five", "six", "seven"]
- correct_answer: five
- rationale: The speaker states the time directly.
- review_status: mvp_approved_pending_full_review
- human_reviewed: false
- audio_generation_status: not_generated
- authoring_notes: Synthetic test fixture.
- estimated_cefr_justification: Simple, direct fact.
- body_json_candidate:
```json
{{
  "question_type": "gap_fill",
  "transcript": "What time is it? It's five o'clock.",
  "situation": "Two friends check the time.",
  "prompt": "What time is it?",
  "accepted_answers": ["five", "5"],
  "max_words": 1,
  "case_sensitive": false,
  "word_bank": ["five", "six", "seven"],
  "review_status": "mvp_approved_pending_full_review",
  "human_reviewed": false,
  "audio_generation_status": "not_generated",
  "listening_skill": "number_time_price",
  "secondary_skill": null,
  "audio_context": "everyday_conversation",
  "discourse_type": "dialogue",
  "rationale": "The speaker states the time directly."
}}
```
"""


@pytest_asyncio.fixture
async def seed_test_language(postgres_session_factory):
    marker = uuid.uuid4().hex[:8]
    code = f"ls{marker}"
    async with postgres_session_factory() as db:
        lang = Language(code=code, name_en="Listening seed test", name_ar="Listening seed test", is_active=True)
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
async def test_apply_inserts_candidates_as_inactive_and_unverified(tmp_path, postgres_session_factory, seed_test_language):
    code, _language_id = seed_test_language
    marker = uuid.uuid4().hex[:8]
    mcq_id, gf_id = f"LST-TEST-{marker}-01", f"LST-TEST-{marker}-02"
    path = _write_draft(tmp_path, _mcq_block(mcq_id), _gap_fill_block(gf_id))

    async with postgres_session_factory() as db:
        summary, result = await apply_seed_batch(
            db, language_code=code, apply=True, draft_path=path, enforce_batch_totals=False
        )
    assert summary.errors == []
    assert result is not None
    assert result.inserted == 2
    assert result.updated == 0

    async with postgres_session_factory() as db:
        rows = (
            await db.execute(
                select(LanguagePlacementQuestionBankItem).where(
                    LanguagePlacementQuestionBankItem.stable_key.in_(result.stable_keys)
                )
            )
        ).scalars().all()
    assert len(rows) == 2
    for row in rows:
        assert row.is_active is False
        assert row.is_verified is False
        assert row.source == "listening_mvp_60_draft"
        assert row.skill == "listening"
        assert row.audio_meta_json is None


@pytest.mark.postgresql
async def test_apply_is_idempotent_and_stable_key_prevents_duplicates(tmp_path, postgres_session_factory, seed_test_language):
    code, _language_id = seed_test_language
    marker = uuid.uuid4().hex[:8]
    mcq_id = f"LST-TEST-{marker}-01"
    path = _write_draft(tmp_path, _mcq_block(mcq_id))

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
                    LanguagePlacementQuestionBankItem.stable_key == f"{STABLE_KEY_PREFIX}:{mcq_id}"
                )
            )
        ).scalars().all()
    assert len(rows) == 1  # never duplicated on rerun


@pytest.mark.postgresql
async def test_apply_rerun_never_resets_is_active_or_is_verified_once_a_human_has_set_them(
    tmp_path, postgres_session_factory, seed_test_language
):
    code, _language_id = seed_test_language
    marker = uuid.uuid4().hex[:8]
    mcq_id = f"LST-TEST-{marker}-01"
    path = _write_draft(tmp_path, _mcq_block(mcq_id))

    async with postgres_session_factory() as db:
        await apply_seed_batch(db, language_code=code, apply=True, draft_path=path, enforce_batch_totals=False)

    # Simulate a later, separate, deliberate human activation step.
    async with postgres_session_factory() as db:
        row = (
            await db.execute(
                select(LanguagePlacementQuestionBankItem).where(
                    LanguagePlacementQuestionBankItem.stable_key == f"{STABLE_KEY_PREFIX}:{mcq_id}"
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
                    LanguagePlacementQuestionBankItem.stable_key == f"{STABLE_KEY_PREFIX}:{mcq_id}"
                )
            )
        ).scalar_one()
    assert row.is_active is True
    assert row.is_verified is True


@pytest.mark.postgresql
async def test_apply_maps_mcq_options_and_correct_index(tmp_path, postgres_session_factory, seed_test_language):
    code, _language_id = seed_test_language
    marker = uuid.uuid4().hex[:8]
    mcq_id = f"LST-TEST-{marker}-01"
    path = _write_draft(tmp_path, _mcq_block(mcq_id))

    async with postgres_session_factory() as db:
        await apply_seed_batch(db, language_code=code, apply=True, draft_path=path, enforce_batch_totals=False)
        row = (
            await db.execute(
                select(LanguagePlacementQuestionBankItem).where(
                    LanguagePlacementQuestionBankItem.stable_key == f"{STABLE_KEY_PREFIX}:{mcq_id}"
                )
            )
        ).scalar_one()

    assert row.options_json == ["Sam", "Tom", "Ann", "Kim"]
    assert row.correct_index == 0
    assert row.question_type == "mcq"
    assert row.stable_key == f"{STABLE_KEY_PREFIX}:{mcq_id}"
    assert "draft_id" not in (row.body_json or {})
    assert "id" not in (row.body_json or {})


@pytest.mark.postgresql
async def test_apply_preserves_gap_fill_fields_in_body_json_and_stays_inactive(
    tmp_path, postgres_session_factory, seed_test_language
):
    code, _language_id = seed_test_language
    marker = uuid.uuid4().hex[:8]
    gf_id = f"LST-TEST-{marker}-02"
    path = _write_draft(tmp_path, _gap_fill_block(gf_id))

    async with postgres_session_factory() as db:
        await apply_seed_batch(db, language_code=code, apply=True, draft_path=path, enforce_batch_totals=False)
        row = (
            await db.execute(
                select(LanguagePlacementQuestionBankItem).where(
                    LanguagePlacementQuestionBankItem.stable_key == f"{STABLE_KEY_PREFIX}:{gf_id}"
                )
            )
        ).scalar_one()

    assert row.question_type == "gap_fill"
    assert row.options_json is None
    assert row.correct_index is None
    assert row.is_active is False
    assert row.is_verified is False
    assert row.body_json["accepted_answers"] == ["five", "5"]
    assert row.body_json["max_words"] == 1
    assert row.body_json["case_sensitive"] is False
    assert row.body_json["word_bank"] == ["five", "six", "seven"]


@pytest.mark.postgresql
async def test_apply_refuses_when_validation_has_errors(tmp_path, postgres_session_factory, seed_test_language):
    code, _language_id = seed_test_language
    marker = uuid.uuid4().hex[:8]
    bad_id = f"LST-TEST-{marker}-01"
    bad = _mcq_block(bad_id).replace(
        '"options": ["Sam", "Tom", "Ann", "Kim"],', '"options": ["Sam", "Tom", "Ann"],'
    ).replace('- options: ["Sam", "Tom", "Ann", "Kim"]', '- options: ["Sam", "Tom", "Ann"]')
    path = _write_draft(tmp_path, bad)

    async with postgres_session_factory() as db:
        summary, result = await apply_seed_batch(
            db, language_code=code, apply=True, draft_path=path, enforce_batch_totals=False
        )
        rows = (
            await db.execute(
                select(LanguagePlacementQuestionBankItem).where(
                    LanguagePlacementQuestionBankItem.stable_key == f"{STABLE_KEY_PREFIX}:{bad_id}"
                )
            )
        ).scalars().all()

    assert not summary.is_valid
    assert result is None
    assert rows == []  # nothing was written


@pytest.mark.postgresql
async def test_apply_refuses_when_draft_id_is_duplicated(tmp_path, postgres_session_factory, seed_test_language):
    code, _language_id = seed_test_language
    marker = uuid.uuid4().hex[:8]
    dup_id = f"LST-TEST-{marker}-01"
    path = _write_draft(tmp_path, _mcq_block(dup_id), _gap_fill_block(dup_id))

    async with postgres_session_factory() as db:
        summary, result = await apply_seed_batch(
            db, language_code=code, apply=True, draft_path=path, enforce_batch_totals=False
        )
        rows = (
            await db.execute(
                select(LanguagePlacementQuestionBankItem).where(
                    LanguagePlacementQuestionBankItem.stable_key == f"{STABLE_KEY_PREFIX}:{dup_id}"
                )
            )
        ).scalars().all()

    assert not summary.is_valid
    assert any(i.field == "draft_id" and "duplicate" in i.message for i in summary.errors)
    assert result is None
    assert rows == []


@pytest.mark.postgresql
async def test_apply_updates_existing_row_missing_audio_transcript_without_duplicating(
    tmp_path, postgres_session_factory, seed_test_language
):
    """Simulates a row seeded before the audio_transcript fix existed: body_json has "transcript"
    but no "audio_transcript". Re-running apply with the current (fixed) code must add
    audio_transcript to that same row -- never insert a second row for the same stable_key."""
    code, language_id = seed_test_language
    marker = uuid.uuid4().hex[:8]
    mcq_id = f"LST-TEST-{marker}-01"
    stable_key = f"{STABLE_KEY_PREFIX}:{mcq_id}"

    async with postgres_session_factory() as db:
        pre_existing = LanguagePlacementQuestionBankItem(
            language_id=language_id,
            skill="listening",
            level=LanguageLevel.A1,
            question_type="mcq",
            prompt_text="What is the student's name?",
            options_json=["Sam", "Tom", "Ann", "Kim"],
            correct_index=0,
            stable_key=stable_key,
            source="listening_mvp_60_draft",
            is_active=False,
            is_verified=False,
            body_json={"transcript": "Hello, what is your name? My name is Sam."},  # no audio_transcript yet
        )
        db.add(pre_existing)
        await db.commit()

    path = _write_draft(tmp_path, _mcq_block(mcq_id))
    async with postgres_session_factory() as db:
        summary, result = await apply_seed_batch(
            db, language_code=code, apply=True, draft_path=path, enforce_batch_totals=False
        )
    assert summary.errors == []
    assert result is not None
    assert result.inserted == 0
    assert result.updated == 1

    async with postgres_session_factory() as db:
        rows = (
            await db.execute(
                select(LanguagePlacementQuestionBankItem).where(LanguagePlacementQuestionBankItem.stable_key == stable_key)
            )
        ).scalars().all()
    assert len(rows) == 1  # no duplicate created
    row = rows[0]
    assert row.body_json["transcript"] == "Hello, what is your name? My name is Sam."
    assert row.body_json["audio_transcript"] == row.body_json["transcript"]


@pytest.mark.postgresql
async def test_apply_does_not_change_audio_meta_json_on_existing_rows(
    tmp_path, postgres_session_factory, seed_test_language
):
    code, _language_id = seed_test_language
    marker = uuid.uuid4().hex[:8]
    mcq_id = f"LST-TEST-{marker}-01"
    stable_key = f"{STABLE_KEY_PREFIX}:{mcq_id}"
    path = _write_draft(tmp_path, _mcq_block(mcq_id))

    async with postgres_session_factory() as db:
        await apply_seed_batch(db, language_code=code, apply=True, draft_path=path, enforce_batch_totals=False)

    # Simulate audio already having been backfilled for this row by a separate, later process.
    fake_audio_meta = {"public_url": "/uploads/fake.wav", "storage_key": "fake", "engine": "supertonic"}
    async with postgres_session_factory() as db:
        row = (
            await db.execute(
                select(LanguagePlacementQuestionBankItem).where(LanguagePlacementQuestionBankItem.stable_key == stable_key)
            )
        ).scalar_one()
        row.audio_meta_json = fake_audio_meta
        await db.commit()

    # A routine content-sync re-run (e.g. this exact fix) must never touch audio_meta_json.
    async with postgres_session_factory() as db:
        await apply_seed_batch(db, language_code=code, apply=True, draft_path=path, enforce_batch_totals=False)

    async with postgres_session_factory() as db:
        row = (
            await db.execute(
                select(LanguagePlacementQuestionBankItem).where(LanguagePlacementQuestionBankItem.stable_key == stable_key)
            )
        ).scalar_one()
    assert row.audio_meta_json == fake_audio_meta


@pytest.mark.postgresql
async def test_seeded_rows_are_synthesis_candidates_for_the_scoped_audio_backfill_after_apply(
    tmp_path, postgres_session_factory, seed_test_language
):
    """End-to-end regression guard for the exact bug this fix addresses: after apply_seed_batch()
    writes a row's body_json, the scoped audio-backfill dry-run (stable_key_prefix + source) must
    see it as a real would_synthesize candidate, not no_transcript."""
    code, _language_id = seed_test_language
    marker = uuid.uuid4().hex[:8]
    mcq_id, gf_id = f"LST-TEST-{marker}-01", f"LST-TEST-{marker}-02"
    path = _write_draft(tmp_path, _mcq_block(mcq_id), _gap_fill_block(gf_id))

    async with postgres_session_factory() as db:
        _summary, result = await apply_seed_batch(
            db, language_code=code, apply=True, draft_path=path, enforce_batch_totals=False
        )
    assert result is not None and result.inserted == 2

    async with postgres_session_factory() as db:
        backfill_summary = await run_backfill(
            db,
            language_code=code,
            stable_key_prefix=f"{STABLE_KEY_PREFIX}:LST-TEST-{marker}",
            source="listening_mvp_60_draft",
        )

    matched_ids = {r.bank_item_id for r in backfill_summary.results}
    assert len(matched_ids) == 2
    assert backfill_summary.no_transcript == []
    assert len(backfill_summary.would_synthesize) == 2
