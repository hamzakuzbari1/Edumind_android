"""Phase 6C (dry-run parse/validate) and apply-implementation (not yet run) tests for the bundled
Listening seed service.

Real-draft tests (guarded by _requires_real_draft, matching the established convention from
test_language_listening_bank_seed_service.py) never touch a database -- they exercise the pure
parse/validate logic in app/services/language_listening_bundle_seed_service.py against the real
backend/content_drafts/listening_bundles_v1_draft.md.

Synthetic-fixture tests exercise individual validation rules against small in-memory markdown
drafts, so they don't depend on the real 30-item content and run everywhere.

Postgres-integration tests (`@pytest.mark.postgresql`, near the end) exercise apply_seed_batch()
directly against the dedicated Postgres *_test* database -- never via the CLI script, never
against a real/dev database. Every test uses a throwaway Language row and unique synthetic
draft_ids so tests can never collide with each other or with any real bank row; real rows never
use source="listening_bundles_v1_draft" or a "listening_bundles_v1:" stable_key prefix from a test.
"""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy import delete, select

from app.models.language.catalog import Language
from app.models.language.question_bank import LanguagePlacementQuestionBankItem
from app.services.language_listening_bundle_seed_service import (
    DEFAULT_DRAFT_PATH,
    EXPECTED_ANSWER_POINTS,
    EXPECTED_DISTRIBUTION,
    EXPECTED_GAP_FILL_TOTAL,
    EXPECTED_MCQ_TOTAL,
    EXPECTED_TOTAL,
    STABLE_KEY_PREFIX,
    apply_seed_batch,
    build_dry_run_summary,
    parse_draft_file,
)

REPO_BACKEND_DIR = Path(__file__).resolve().parents[1]

# backend/content_drafts/ is authoring-time content, not app source, and is intentionally not
# copied into the test Docker image -- these tests still run wherever the file is actually present
# (host, dev container) and skip gracefully otherwise.
_requires_real_draft = pytest.mark.skipif(
    not DEFAULT_DRAFT_PATH.exists(), reason="backend/content_drafts/ is not present in this test environment"
)

_DISALLOWED_GAP_FILL_LISTENING_SKILLS = {"inference", "implied_meaning", "speaker_attitude", "following_argument"}


# ---------------------------------------------------------------------------
# Tests against the real draft file.
# ---------------------------------------------------------------------------


@_requires_real_draft
def test_parses_exactly_30_bundles():
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
def test_five_bundles_per_level_three_mcq_two_gap_fill():
    summary = build_dry_run_summary()
    for level in ("A1", "A2", "B1", "B2", "C1", "C2"):
        assert summary.distribution[(level, "mcq")] == 3
        assert summary.distribution[(level, "gap_fill")] == 2


@_requires_real_draft
def test_total_answer_points_is_90():
    summary = build_dry_run_summary()
    assert summary.answer_points == EXPECTED_ANSWER_POINTS


@_requires_real_draft
def test_real_draft_has_zero_validation_errors():
    summary = build_dry_run_summary()
    assert summary.errors == []


@_requires_real_draft
def test_candidates_default_to_inactive_and_unverified():
    summary = build_dry_run_summary()
    assert summary.candidates, "expected at least one candidate to check defaults on"
    for candidate in summary.candidates:
        assert candidate.is_active is False
        assert candidate.is_verified is False
        assert candidate.source == "listening_bundles_v1_draft"
        assert candidate.skill == "listening"


@_requires_real_draft
def test_stable_key_format_is_correct():
    summary = build_dry_run_summary()
    for candidate in summary.candidates:
        assert candidate.stable_key == f"{STABLE_KEY_PREFIX}:{candidate.draft_id}"
        assert candidate.stable_key.startswith("listening_bundles_v1:LSTB-")


@_requires_real_draft
def test_draft_id_never_used_as_a_database_id():
    summary = build_dry_run_summary()
    for candidate in summary.candidates:
        assert "id" not in candidate.body_json
        assert "bank_item_id" not in candidate.body_json
        assert "draft_id" not in candidate.body_json
        assert isinstance(candidate.draft_id, str)


@_requires_real_draft
def test_mcq_bundle_candidates_have_exactly_3_subquestions():
    summary = build_dry_run_summary()
    mcq_candidates = [c for c in summary.candidates if c.question_type == "mcq"]
    assert len(mcq_candidates) == EXPECTED_MCQ_TOTAL
    for candidate in mcq_candidates:
        subquestions = candidate.body_json.get("subquestions")
        assert isinstance(subquestions, list) and len(subquestions) == 3
        for sq in subquestions:
            assert isinstance(sq.get("options"), list) and len(sq["options"]) == 4
            ci = sq.get("correct_index")
            assert isinstance(ci, int) and not isinstance(ci, bool) and 0 <= ci < 4


@_requires_real_draft
def test_gap_fill_bundle_candidates_have_exactly_3_blanks_and_valid_note_template():
    summary = build_dry_run_summary()
    gap_fill_candidates = [c for c in summary.candidates if c.question_type == "gap_fill"]
    assert len(gap_fill_candidates) == EXPECTED_GAP_FILL_TOTAL
    for candidate in gap_fill_candidates:
        blanks = candidate.body_json.get("blanks")
        assert isinstance(blanks, list) and len(blanks) == 3
        note_template = candidate.body_json.get("note_template")
        assert isinstance(note_template, str) and note_template
        for token in ("{{1}}", "{{2}}", "{{3}}"):
            assert note_template.count(token) == 1
        for blank in blanks:
            assert isinstance(blank.get("accepted_answers"), list) and blank["accepted_answers"]
            assert isinstance(blank.get("max_words"), int) and blank["max_words"] > 0
            assert blank.get("case_sensitive") is False


@_requires_real_draft
def test_gap_fill_bundles_never_use_disallowed_listening_skill_tags():
    raw_items = parse_draft_file()
    gap_fill_items = [r for r in raw_items if r.get("question_type") == "gap_fill"]
    assert gap_fill_items, "expected at least one gap_fill bundle in the draft"
    offending = [
        r.get("draft_id") for r in gap_fill_items
        if set(r.get("listening_skill_tags") or []) & _DISALLOWED_GAP_FILL_LISTENING_SKILLS
    ]
    assert offending == []


# ---------------------------------------------------------------------------
# Synthetic-fixture tests for individual validation rules.
# ---------------------------------------------------------------------------


def _mcq_bundle_block(draft_id: str, *, level: str = "A1", correct_indices=(0, 1, 2)) -> str:
    ci0, ci1, ci2 = correct_indices
    return f"""### ITEM {draft_id}
- draft_id: {draft_id}
- level: {level}
- question_type: mcq
- title: Synthetic MCQ Bundle
- situation: A short synthetic bundle for testing.
- audio_transcript: "This is a short synthetic transcript for testing purposes only."
- listening_skill_tags: [situation, explicit_detail, reason_cause]
- estimated_audio_duration_seconds: 20

```json
{{
  "audio_transcript": "This is a short synthetic transcript for testing purposes only.",
  "subquestions": [
    {{"question": "Q1?", "options": ["a", "b", "c", "d"], "correct_index": {ci0}}},
    {{"question": "Q2?", "options": ["a", "b", "c", "d"], "correct_index": {ci1}}},
    {{"question": "Q3?", "options": ["a", "b", "c", "d"], "correct_index": {ci2}}}
  ]
}}
```
"""


def _gap_fill_bundle_block(draft_id: str, *, level: str = "A1", skill_tags: str = "explicit_detail, number_time_price") -> str:
    return f"""### ITEM {draft_id}
- draft_id: {draft_id}
- level: {level}
- question_type: gap_fill
- title: Synthetic Gap Fill Bundle
- situation: A short synthetic note-completion bundle for testing.
- audio_transcript: "The train leaves at three pm from platform six for ten pounds."
- listening_skill_tags: [{skill_tags}]
- estimated_audio_duration_seconds: 20

```json
{{
  "audio_transcript": "The train leaves at three pm from platform six for ten pounds.",
  "note_template": "Departure: {{{{1}}}}. Platform: {{{{2}}}}. Price: {{{{3}}}}.",
  "blanks": [
    {{"accepted_answers": ["3pm", "3 pm"], "max_words": 2, "case_sensitive": false}},
    {{"accepted_answers": ["six"], "max_words": 1, "case_sensitive": false}},
    {{"accepted_answers": ["ten pounds"], "max_words": 2, "case_sensitive": false}}
  ]
}}
```
"""


def _write_draft(tmp_path: Path, *item_blocks: str) -> Path:
    path = tmp_path / "synthetic_bundle_draft.md"
    path.write_text("# Synthetic Bundle Draft\n\n" + "\n".join(item_blocks), encoding="utf-8")
    return path


_BATCH_LEVEL_FIELDS = {"total_count", "distribution", "mcq_total", "gap_fill_total", "answer_points"}


def test_valid_synthetic_bundles_pass_with_no_per_item_errors(tmp_path):
    path = _write_draft(tmp_path, _mcq_bundle_block("LSTB-TEST-01"), _gap_fill_bundle_block("LSTB-TEST-02"))
    summary = build_dry_run_summary(draft_path=path, enforce_batch_totals=False)
    assert summary.total_parsed == 2
    per_item_errors = [i for i in summary.errors if i.field not in _BATCH_LEVEL_FIELDS]
    assert per_item_errors == []


def test_duplicate_draft_id_rejected(tmp_path):
    path = _write_draft(tmp_path, _mcq_bundle_block("LSTB-TEST-01"), _gap_fill_bundle_block("LSTB-TEST-01"))
    summary = build_dry_run_summary(draft_path=path, enforce_batch_totals=False)
    assert any(i.field == "draft_id" and "duplicate" in i.message for i in summary.errors)


def test_malformed_json_fence_rejected(tmp_path):
    bad = _mcq_bundle_block("LSTB-TEST-01").replace('"correct_index": 0', '"correct_index": 0,,')
    path = _write_draft(tmp_path, bad)
    summary = build_dry_run_summary(draft_path=path, enforce_batch_totals=False)
    assert any(i.field == "body_json_candidate" for i in summary.errors)


def test_invalid_mcq_correct_index_out_of_range_rejected(tmp_path):
    bad = _mcq_bundle_block("LSTB-TEST-01", correct_indices=(0, 1, 9))
    path = _write_draft(tmp_path, bad)
    summary = build_dry_run_summary(draft_path=path, enforce_batch_totals=False)
    assert any("correct_index" in i.field for i in summary.errors)


def test_mcq_bundle_with_fewer_than_3_subquestions_rejected(tmp_path):
    bad = _mcq_bundle_block("LSTB-TEST-01").replace(
        '{"question": "Q3?", "options": ["a", "b", "c", "d"], "correct_index": 2}\n  ]',
        "]",
    )
    path = _write_draft(tmp_path, bad)
    summary = build_dry_run_summary(draft_path=path, enforce_batch_totals=False)
    assert any(i.field == "subquestions" for i in summary.errors)


def test_mcq_bundle_with_more_than_3_subquestions_rejected(tmp_path):
    bad = _mcq_bundle_block("LSTB-TEST-01").replace(
        '{"question": "Q3?", "options": ["a", "b", "c", "d"], "correct_index": 2}\n  ]',
        '{"question": "Q3?", "options": ["a", "b", "c", "d"], "correct_index": 2},\n'
        '    {"question": "Q4?", "options": ["a", "b", "c", "d"], "correct_index": 0}\n  ]',
    )
    path = _write_draft(tmp_path, bad)
    summary = build_dry_run_summary(draft_path=path, enforce_batch_totals=False)
    assert any(i.field == "subquestions" for i in summary.errors)


def test_mcq_subquestion_missing_question_text_rejected(tmp_path):
    bad = _mcq_bundle_block("LSTB-TEST-01").replace('"question": "Q1?"', '"question": "  "')
    path = _write_draft(tmp_path, bad)
    summary = build_dry_run_summary(draft_path=path, enforce_batch_totals=False)
    assert any("question" in i.field for i in summary.errors)


def test_mcq_subquestion_wrong_option_count_rejected(tmp_path):
    bad = _mcq_bundle_block("LSTB-TEST-01").replace(
        '"options": ["a", "b", "c", "d"], "correct_index": 1', '"options": ["a", "b", "c"], "correct_index": 1'
    )
    path = _write_draft(tmp_path, bad)
    summary = build_dry_run_summary(draft_path=path, enforce_batch_totals=False)
    assert any("options" in i.field for i in summary.errors)


def test_gap_fill_bundle_missing_token_rejected(tmp_path):
    bad = _gap_fill_bundle_block("LSTB-TEST-02").replace(
        '"note_template": "Departure: {{1}}. Platform: {{2}}. Price: {{3}}."',
        '"note_template": "Departure: {{1}}. Platform: {{2}}."',
    )
    path = _write_draft(tmp_path, bad)
    summary = build_dry_run_summary(draft_path=path, enforce_batch_totals=False)
    assert any(i.field == "note_template" for i in summary.errors)


def test_gap_fill_bundle_duplicated_token_rejected(tmp_path):
    bad = _gap_fill_bundle_block("LSTB-TEST-02").replace(
        '"note_template": "Departure: {{1}}. Platform: {{2}}. Price: {{3}}."',
        '"note_template": "Departure: {{1}}. Platform: {{1}}. Price: {{3}}."',
    )
    path = _write_draft(tmp_path, bad)
    summary = build_dry_run_summary(draft_path=path, enforce_batch_totals=False)
    assert any(i.field == "note_template" for i in summary.errors)


def test_gap_fill_bundle_with_fewer_than_3_blanks_rejected(tmp_path):
    bad = _gap_fill_bundle_block("LSTB-TEST-02").replace(
        '{"accepted_answers": ["ten pounds"], "max_words": 2, "case_sensitive": false}\n  ]',
        "]",
    )
    path = _write_draft(tmp_path, bad)
    summary = build_dry_run_summary(draft_path=path, enforce_batch_totals=False)
    assert any(i.field == "blanks" for i in summary.errors)


def test_gap_fill_bundle_with_more_than_3_blanks_rejected(tmp_path):
    bad = _gap_fill_bundle_block("LSTB-TEST-02").replace(
        '{"accepted_answers": ["ten pounds"], "max_words": 2, "case_sensitive": false}\n  ]',
        '{"accepted_answers": ["ten pounds"], "max_words": 2, "case_sensitive": false},\n'
        '    {"accepted_answers": ["extra"], "max_words": 1, "case_sensitive": false}\n  ]',
    )
    path = _write_draft(tmp_path, bad)
    summary = build_dry_run_summary(draft_path=path, enforce_batch_totals=False)
    assert any(i.field == "blanks" for i in summary.errors)


def test_accepted_answer_exceeding_max_words_rejected(tmp_path):
    bad = _gap_fill_bundle_block("LSTB-TEST-02").replace(
        '"accepted_answers": ["ten pounds"], "max_words": 2', '"accepted_answers": ["ten British pounds exactly"], "max_words": 2'
    )
    path = _write_draft(tmp_path, bad)
    summary = build_dry_run_summary(draft_path=path, enforce_batch_totals=False)
    assert any("accepted_answers" in i.field and "exceeds max_words" in i.message for i in summary.errors)


def test_case_sensitive_true_rejected(tmp_path):
    bad = _gap_fill_bundle_block("LSTB-TEST-02").replace(
        '"accepted_answers": ["3pm", "3 pm"], "max_words": 2, "case_sensitive": false',
        '"accepted_answers": ["3pm", "3 pm"], "max_words": 2, "case_sensitive": true',
    )
    path = _write_draft(tmp_path, bad)
    summary = build_dry_run_summary(draft_path=path, enforce_batch_totals=False)
    assert any("case_sensitive" in i.field for i in summary.errors)


def test_missing_accepted_answers_rejected(tmp_path):
    bad = _gap_fill_bundle_block("LSTB-TEST-02").replace(
        '"accepted_answers": ["six"], "max_words": 1, "case_sensitive": false',
        '"accepted_answers": [], "max_words": 1, "case_sensitive": false',
    )
    path = _write_draft(tmp_path, bad)
    summary = build_dry_run_summary(draft_path=path, enforce_batch_totals=False)
    assert any("accepted_answers" in i.field for i in summary.errors)


def test_disallowed_gap_fill_listening_skill_tag_rejected(tmp_path):
    bad = _gap_fill_bundle_block("LSTB-TEST-02", skill_tags="inference")
    path = _write_draft(tmp_path, bad)
    summary = build_dry_run_summary(draft_path=path, enforce_batch_totals=False)
    assert any(i.field == "listening_skill_tags" for i in summary.errors)


def test_allowed_gap_fill_listening_skill_tags_pass(tmp_path):
    path = _write_draft(tmp_path, _gap_fill_bundle_block("LSTB-TEST-02", skill_tags="number_time_price"))
    summary = build_dry_run_summary(draft_path=path, enforce_batch_totals=False)
    assert not any(i.field == "listening_skill_tags" for i in summary.errors)


def test_missing_audio_transcript_rejected(tmp_path):
    bad = _mcq_bundle_block("LSTB-TEST-01").replace(
        '"audio_transcript": "This is a short synthetic transcript for testing purposes only.",\n  "subquestions"',
        '"subquestions"',
    )
    path = _write_draft(tmp_path, bad)
    summary = build_dry_run_summary(draft_path=path, enforce_batch_totals=False)
    assert any("audio_transcript" in i.field for i in summary.errors)


def test_unknown_question_type_rejected(tmp_path):
    bad = _mcq_bundle_block("LSTB-TEST-01").replace("- question_type: mcq", "- question_type: essay")
    path = _write_draft(tmp_path, bad)
    summary = build_dry_run_summary(draft_path=path, enforce_batch_totals=False)
    assert any(i.field == "question_type" for i in summary.errors)


def test_draft_id_never_copied_into_synthetic_candidate_body_json(tmp_path):
    path = _write_draft(tmp_path, _mcq_bundle_block("LSTB-TEST-01"))
    summary = build_dry_run_summary(draft_path=path, enforce_batch_totals=False)
    assert "draft_id" not in summary.candidates[0].body_json


def test_options_json_and_correct_index_columns_left_none_on_candidate(tmp_path):
    """Bundle rows never use the top-level options_json/correct_index columns -- confirmed by
    the SeedCandidate dataclass shape itself not carrying those fields at all."""
    path = _write_draft(tmp_path, _mcq_bundle_block("LSTB-TEST-01"))
    summary = build_dry_run_summary(draft_path=path, enforce_batch_totals=False)
    candidate = summary.candidates[0]
    assert not hasattr(candidate, "options_json")
    assert not hasattr(candidate, "correct_index")


def test_batch_totals_enforced_on_synthetic_2_item_draft(tmp_path):
    path = _write_draft(tmp_path, _mcq_bundle_block("LSTB-TEST-01"), _gap_fill_bundle_block("LSTB-TEST-02"))
    summary = build_dry_run_summary(draft_path=path)  # enforce_batch_totals defaults True
    assert any(i.field == "total_count" for i in summary.errors)
    assert any(i.field == "answer_points" for i in summary.errors)


# ---------------------------------------------------------------------------
# Postgres-integration tests: apply_seed_batch() against the dedicated test DB. Never run
# against a real/dev database. --apply is never invoked from the CLI in this phase.
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def seed_test_language(postgres_session_factory):
    marker = uuid.uuid4().hex[:8]
    code = f"lb{marker}"
    async with postgres_session_factory() as db:
        lang = Language(code=code, name_en="Listening bundle seed test", name_ar="Listening bundle seed test", is_active=True)
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
async def test_apply_inserts_bundles_as_inactive_and_unverified(tmp_path, postgres_session_factory, seed_test_language):
    code, _language_id = seed_test_language
    marker = uuid.uuid4().hex[:8]
    mcq_id, gf_id = f"LSTB-TEST-{marker}-01", f"LSTB-TEST-{marker}-02"
    path = _write_draft(tmp_path, _mcq_bundle_block(mcq_id), _gap_fill_bundle_block(gf_id))

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
        assert row.source == "listening_bundles_v1_draft"
        assert row.skill == "listening"
        assert row.audio_meta_json is None
        assert row.options_json is None
        assert row.correct_index is None
        assert "audio_transcript" in row.body_json


@pytest.mark.postgresql
async def test_apply_mcq_bundle_row_has_subquestions_in_body_json(tmp_path, postgres_session_factory, seed_test_language):
    code, _language_id = seed_test_language
    marker = uuid.uuid4().hex[:8]
    mcq_id = f"LSTB-TEST-{marker}-01"
    path = _write_draft(tmp_path, _mcq_bundle_block(mcq_id))

    async with postgres_session_factory() as db:
        _summary, result = await apply_seed_batch(
            db, language_code=code, apply=True, draft_path=path, enforce_batch_totals=False
        )
    async with postgres_session_factory() as db:
        row = (
            await db.execute(
                select(LanguagePlacementQuestionBankItem).where(
                    LanguagePlacementQuestionBankItem.stable_key == result.stable_keys[0]
                )
            )
        ).scalar_one()
    subquestions = row.body_json.get("subquestions")
    assert isinstance(subquestions, list) and len(subquestions) == 3


@pytest.mark.postgresql
async def test_apply_gap_fill_bundle_row_has_note_template_and_blanks(tmp_path, postgres_session_factory, seed_test_language):
    code, _language_id = seed_test_language
    marker = uuid.uuid4().hex[:8]
    gf_id = f"LSTB-TEST-{marker}-02"
    path = _write_draft(tmp_path, _gap_fill_bundle_block(gf_id))

    async with postgres_session_factory() as db:
        _summary, result = await apply_seed_batch(
            db, language_code=code, apply=True, draft_path=path, enforce_batch_totals=False
        )
    async with postgres_session_factory() as db:
        row = (
            await db.execute(
                select(LanguagePlacementQuestionBankItem).where(
                    LanguagePlacementQuestionBankItem.stable_key == result.stable_keys[0]
                )
            )
        ).scalar_one()
    assert row.body_json.get("note_template")
    blanks = row.body_json.get("blanks")
    assert isinstance(blanks, list) and len(blanks) == 3


@pytest.mark.postgresql
async def test_apply_is_idempotent_and_stable_key_prevents_duplicates(tmp_path, postgres_session_factory, seed_test_language):
    code, _language_id = seed_test_language
    marker = uuid.uuid4().hex[:8]
    mcq_id = f"LSTB-TEST-{marker}-01"
    path = _write_draft(tmp_path, _mcq_bundle_block(mcq_id))

    async with postgres_session_factory() as db:
        _summary1, result1 = await apply_seed_batch(
            db, language_code=code, apply=True, draft_path=path, enforce_batch_totals=False
        )
    async with postgres_session_factory() as db:
        _summary2, result2 = await apply_seed_batch(
            db, language_code=code, apply=True, draft_path=path, enforce_batch_totals=False
        )
    assert result1.inserted == 1 and result1.updated == 0
    assert result2.inserted == 0 and result2.updated == 1

    async with postgres_session_factory() as db:
        rows = (
            await db.execute(
                select(LanguagePlacementQuestionBankItem).where(
                    LanguagePlacementQuestionBankItem.stable_key == result1.stable_keys[0]
                )
            )
        ).scalars().all()
    assert len(rows) == 1


@pytest.mark.postgresql
async def test_apply_rerun_never_resets_is_active_or_is_verified_once_set(
    tmp_path, postgres_session_factory, seed_test_language
):
    code, _language_id = seed_test_language
    marker = uuid.uuid4().hex[:8]
    mcq_id = f"LSTB-TEST-{marker}-01"
    path = _write_draft(tmp_path, _mcq_bundle_block(mcq_id))

    async with postgres_session_factory() as db:
        _summary1, result1 = await apply_seed_batch(
            db, language_code=code, apply=True, draft_path=path, enforce_batch_totals=False
        )
    async with postgres_session_factory() as db:
        row = (
            await db.execute(
                select(LanguagePlacementQuestionBankItem).where(
                    LanguagePlacementQuestionBankItem.stable_key == result1.stable_keys[0]
                )
            )
        ).scalar_one()
        row.is_active = True
        row.is_verified = True
        await db.commit()

    async with postgres_session_factory() as db:
        await apply_seed_batch(db, language_code=code, apply=True, draft_path=path, enforce_batch_totals=False)

    async with postgres_session_factory() as db:
        row = (
            await db.execute(
                select(LanguagePlacementQuestionBankItem).where(
                    LanguagePlacementQuestionBankItem.stable_key == result1.stable_keys[0]
                )
            )
        ).scalar_one()
    assert row.is_active is True
    assert row.is_verified is True


@pytest.mark.postgresql
async def test_apply_refuses_when_validation_has_errors(tmp_path, postgres_session_factory, seed_test_language):
    code, _language_id = seed_test_language
    bad = _mcq_bundle_block("LSTB-TEST-01", correct_indices=(0, 1, 9))
    path = _write_draft(tmp_path, bad)

    async with postgres_session_factory() as db:
        summary, result = await apply_seed_batch(
            db, language_code=code, apply=True, draft_path=path, enforce_batch_totals=False
        )
    assert summary.errors != []
    assert result is None

    async with postgres_session_factory() as db:
        rows = (
            await db.execute(
                select(LanguagePlacementQuestionBankItem).where(
                    LanguagePlacementQuestionBankItem.stable_key == "listening_bundles_v1:LSTB-TEST-01"
                )
            )
        ).scalars().all()
    assert rows == []


def test_dry_run_never_opens_a_database_session(tmp_path):
    """build_dry_run_summary() takes no db/session argument at all -- structurally incapable of
    writing anything, confirmed by the function signature itself requiring no AsyncSession."""
    import inspect

    from app.services.language_listening_bundle_seed_service import build_dry_run_summary as fn

    params = inspect.signature(fn).parameters
    assert "db" not in params and "session" not in params
