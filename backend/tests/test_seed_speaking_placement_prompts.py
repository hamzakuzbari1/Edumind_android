"""Tests for the offline speaking-placement prompt seed content and logic (Blueprint Phase A0+A1,
MVP activation).

Static tests validate the authored SPEAKING_PROMPT_SEEDS content itself (no DB needed).
Postgres-marked tests validate the actual insert/update/idempotency/activation behavior against a
real database. These 30 items are used for MVP placement without a completed human-review pass
(explicit product decision) -- tests here confirm every item carries a clear, machine-readable
"not human-reviewed yet" marker, and that no code path ever claims a review was done. Wiring
skill="speaking_prompt" selection into the live exam is covered separately in
test_language_exam_postgresql_concurrency.py.
"""

from __future__ import annotations

import types
import uuid

import pytest
from sqlalchemy import select

from app.models.language.catalog import Language
from app.models.language.enums import LanguageLevel
from app.models.language.question_bank import LanguagePlacementQuestionBankItem
from app.services.language_speaking_placement_seed_service import (
    GRADE_BANDS,
    MVP_REVIEW_STATUS,
    SPEAKING_PROMPT_SEEDS,
    TASK_TYPES,
    _apply_content_fields,
    activate_mvp_drafts,
    db_stable_key,
    seed_speaking_prompts,
)


_CEFR_ORDER = ["A1", "A2", "B1", "B2", "C1", "C2"]
# 30 original (24 base + 6 boundary) + 6-item A1/A2 diversity top-up + 30-item cross-level
# diversity top-up added to reduce repeated placement speaking prompts.
_EXPECTED_TOTAL_SEEDS = 72
_EXPECTED_BASE_SEEDS = 66
_EXPECTED_BOUNDARY_SEEDS = 6


# ---------------------------------------------------------------------------
# Static content tests -- no database required.
# ---------------------------------------------------------------------------


def test_seed_count_matches_expected_matrix():
    """Coarse sanity check: catches an authoring mistake (duplicated level, missing level)."""
    assert len(SPEAKING_PROMPT_SEEDS) == _EXPECTED_TOTAL_SEEDS

    boundary = [s for s in SPEAKING_PROMPT_SEEDS if s.boundary_low_level and s.boundary_high_level]
    base = [s for s in SPEAKING_PROMPT_SEEDS if not (s.boundary_low_level and s.boundary_high_level)]
    assert len(boundary) == _EXPECTED_BOUNDARY_SEEDS
    assert len(base) == _EXPECTED_BASE_SEEDS

    by_level: dict[str, int] = {}
    for seed in SPEAKING_PROMPT_SEEDS:
        by_level[seed.level.value] = by_level.get(seed.level.value, 0) + 1
    assert set(by_level) == set(_CEFR_ORDER)
    assert all(count > 0 for count in by_level.values())


def test_every_seed_has_nonempty_prompt_text():
    for seed in SPEAKING_PROMPT_SEEDS:
        assert isinstance(seed.prompt_text, str)
        assert seed.prompt_text.strip(), f"{seed.content_key} has empty prompt_text"


def test_every_seed_has_valid_cefr_level():
    for seed in SPEAKING_PROMPT_SEEDS:
        assert isinstance(seed.level, LanguageLevel)
        assert seed.level.value in _CEFR_ORDER


def test_every_seed_has_allowed_task_type():
    for seed in SPEAKING_PROMPT_SEEDS:
        assert seed.subskill in TASK_TYPES, f"{seed.content_key} has unknown task type {seed.subskill!r}"


def test_every_seed_has_grade_band_in_body_json():
    for seed in SPEAKING_PROMPT_SEEDS:
        body = seed.body_json()
        grade_bands = body.get("grade_band")
        assert isinstance(grade_bands, list) and grade_bands, f"{seed.content_key} missing grade_band"
        assert all(band in GRADE_BANDS for band in grade_bands)


def test_every_seed_has_plausible_expected_response_seconds():
    for seed in SPEAKING_PROMPT_SEEDS:
        duration = seed.body_json()["expected_response_seconds"]
        assert set(duration) == {"min", "target", "max"}
        assert 0 < duration["min"] <= duration["target"] <= duration["max"]
        # Sanity ceiling matching the placement exam's own audio-duration cap.
        assert duration["max"] <= 180


def test_every_seed_has_content_key_and_they_are_unique():
    keys = [seed.content_key for seed in SPEAKING_PROMPT_SEEDS]
    assert all(isinstance(k, str) and k.strip() for k in keys)
    assert len(keys) == len(set(keys)), "duplicate content_key found among seeds"


def test_db_stable_key_is_namespaced_by_language_and_content():
    """The DB column's unique constraint is global, not per-language, so the persisted
    stable_key must incorporate the language code -- otherwise seeding a second language would
    collide with (or silently steal) the first language's rows. Also keeps this bank's keys from
    colliding with the generic script's "content:<id>" keys."""
    assert db_stable_key("en", "A1:self_intro:01") == "speaking_prompt:en:A1:self_intro:01"
    assert db_stable_key("fr", "A1:self_intro:01") == "speaking_prompt:fr:A1:self_intro:01"
    assert db_stable_key("en", "A1:self_intro:01") != db_stable_key("fr", "A1:self_intro:01")
    for seed in SPEAKING_PROMPT_SEEDS:
        assert db_stable_key("en", seed.content_key).startswith("speaking_prompt:en:")


def test_boundary_items_have_valid_adjacent_boundary_levels():
    for seed in SPEAKING_PROMPT_SEEDS:
        if seed.boundary_low_level is None and seed.boundary_high_level is None:
            continue
        assert seed.boundary_low_level is not None and seed.boundary_high_level is not None, (
            f"{seed.content_key} has only one of boundary_low_level/boundary_high_level set"
        )
        low_rank = _CEFR_ORDER.index(seed.boundary_low_level.value)
        high_rank = _CEFR_ORDER.index(seed.boundary_high_level.value)
        assert high_rank - low_rank == 1, f"{seed.content_key} boundary levels are not adjacent"


def test_non_boundary_items_have_no_boundary_levels_set():
    boundary_keys = {s.content_key for s in SPEAKING_PROMPT_SEEDS if s.boundary_low_level}
    assert len(boundary_keys) == _EXPECTED_BOUNDARY_SEEDS
    for seed in SPEAKING_PROMPT_SEEDS:
        if seed.content_key not in boundary_keys:
            assert seed.boundary_low_level is None
            assert seed.boundary_high_level is None


def test_every_seed_has_nonempty_reference_notes_for_the_reviewer():
    for seed in SPEAKING_PROMPT_SEEDS:
        notes = seed.body_json()["reference_notes"]
        assert isinstance(notes, str) and notes.strip()
        assert "Reviewer check" in notes


def test_every_seed_body_json_carries_mvp_pending_review_marker():
    """Test B: every item must clearly, machine-readably record that it is MVP-approved but NOT
    human-reviewed -- this module must never write or imply a completed human review."""
    for seed in SPEAKING_PROMPT_SEEDS:
        body = seed.body_json()
        assert body["review_status"] == MVP_REVIEW_STATUS == "mvp_approved_pending_full_review"
        assert body["human_reviewed"] is False
        assert "MVP" in body["reference_notes"]


def test_apply_content_fields_always_sets_speaking_prompt_skill_and_question_type():
    """Pure unit check on the row-population helper using a lightweight fake row, independent
    of any database -- confirms skill/question_type are hardcoded, not seed-dependent."""
    fake_row = types.SimpleNamespace()
    seed = SPEAKING_PROMPT_SEEDS[0]
    _apply_content_fields(fake_row, seed, language_id=999)
    assert fake_row.skill == "speaking_prompt"
    assert fake_row.question_type == "speaking_prompt"
    assert fake_row.language_id == 999
    assert fake_row.prompt_text == seed.prompt_text


# ---------------------------------------------------------------------------
# Postgres-backed behavior tests.
# ---------------------------------------------------------------------------


async def _make_language(postgres_session_factory) -> tuple[int, str]:
    marker = uuid.uuid4().hex[:12]
    code = f"sp-{marker}"
    async with postgres_session_factory() as db:
        language = Language(
            code=code,
            name_en=f"Speaking prompt test language {marker}",
            name_ar=f"Speaking prompt test language {marker}",
            is_active=True,
        )
        db.add(language)
        await db.commit()
        return language.id, code


async def _all_items_for_language(postgres_session_factory, language_id: int) -> list[LanguagePlacementQuestionBankItem]:
    async with postgres_session_factory() as db:
        rows = (
            await db.execute(
                select(LanguagePlacementQuestionBankItem).where(
                    LanguagePlacementQuestionBankItem.language_id == language_id,
                    LanguagePlacementQuestionBankItem.skill == "speaking_prompt",
                )
            )
        ).scalars().all()
        return list(rows)


@pytest.mark.postgresql
async def test_dry_run_does_not_write_anything(postgres_session_factory):
    language_id, language_code = await _make_language(postgres_session_factory)
    async with postgres_session_factory() as db:
        inserts, updates = await seed_speaking_prompts(
            db, language_id=language_id, language_code=language_code, apply=False
        )
    assert inserts == _EXPECTED_TOTAL_SEEDS
    assert updates == 0

    rows = await _all_items_for_language(postgres_session_factory, language_id)
    assert rows == []


@pytest.mark.postgresql
async def test_apply_inserts_all_seeds_as_mvp_verified_active_items(postgres_session_factory):
    """Test A: fresh inserts default to is_verified=True/is_active=True, reflecting the explicit
    MVP-approved-without-full-review product decision (no separate activation step needed for a
    brand new environment/language)."""
    language_id, language_code = await _make_language(postgres_session_factory)
    async with postgres_session_factory() as db:
        inserts, updates = await seed_speaking_prompts(
            db, language_id=language_id, language_code=language_code, apply=True
        )
    assert inserts == _EXPECTED_TOTAL_SEEDS
    assert updates == 0

    rows = await _all_items_for_language(postgres_session_factory, language_id)
    assert len(rows) == _EXPECTED_TOTAL_SEEDS
    expected_keys = {db_stable_key(language_code, s.content_key) for s in SPEAKING_PROMPT_SEEDS}
    for row in rows:
        assert row.is_verified is True
        assert row.is_active is True
        assert row.skill == "speaking_prompt"
        assert row.question_type == "speaking_prompt"
        assert row.source == "draft_seed"
        assert row.prompt_text.strip()
        assert (row.body_json or {}).get("grade_band")
        assert row.stable_key in expected_keys
        # Test B (integration level): the marker survives the real DB round-trip too.
        assert row.body_json.get("review_status") == MVP_REVIEW_STATUS
        assert row.body_json.get("human_reviewed") is False


@pytest.mark.postgresql
async def test_apply_twice_is_idempotent_and_does_not_duplicate_rows(postgres_session_factory):
    language_id, language_code = await _make_language(postgres_session_factory)
    async with postgres_session_factory() as db:
        first_inserts, first_updates = await seed_speaking_prompts(
            db, language_id=language_id, language_code=language_code, apply=True
        )
    assert first_inserts == _EXPECTED_TOTAL_SEEDS
    assert first_updates == 0

    rows_after_first = await _all_items_for_language(postgres_session_factory, language_id)
    assert len(rows_after_first) == _EXPECTED_TOTAL_SEEDS
    ids_after_first = sorted(row.id for row in rows_after_first)

    async with postgres_session_factory() as db:
        second_inserts, second_updates = await seed_speaking_prompts(
            db, language_id=language_id, language_code=language_code, apply=True
        )
    assert second_inserts == 0
    assert second_updates == _EXPECTED_TOTAL_SEEDS

    rows_after_second = await _all_items_for_language(postgres_session_factory, language_id)
    assert len(rows_after_second) == _EXPECTED_TOTAL_SEEDS
    ids_after_second = sorted(row.id for row in rows_after_second)
    assert ids_after_first == ids_after_second, "re-running the seed script duplicated rows"


@pytest.mark.postgresql
async def test_seeding_two_languages_does_not_collide(postgres_session_factory):
    """Directly proves the fix: the same authored content, seeded for two different languages,
    must produce two independent sets of rows -- not a stable_key collision/overwrite."""
    language_id_a, code_a = await _make_language(postgres_session_factory)
    language_id_b, code_b = await _make_language(postgres_session_factory)

    async with postgres_session_factory() as db:
        inserts_a, _ = await seed_speaking_prompts(db, language_id=language_id_a, language_code=code_a, apply=True)
    async with postgres_session_factory() as db:
        inserts_b, _ = await seed_speaking_prompts(db, language_id=language_id_b, language_code=code_b, apply=True)

    assert inserts_a == _EXPECTED_TOTAL_SEEDS
    assert inserts_b == _EXPECTED_TOTAL_SEEDS, "second language's seeding was treated as updates to the first"

    rows_a = await _all_items_for_language(postgres_session_factory, language_id_a)
    rows_b = await _all_items_for_language(postgres_session_factory, language_id_b)
    assert len(rows_a) == _EXPECTED_TOTAL_SEEDS
    assert len(rows_b) == _EXPECTED_TOTAL_SEEDS
    assert {r.id for r in rows_a}.isdisjoint({r.id for r in rows_b})


@pytest.mark.postgresql
async def test_rerun_does_not_reactivate_a_manually_deactivated_item(postgres_session_factory):
    """Simulates the real lifecycle now that fresh inserts default to is_verified=True: a human
    reviewer later decides one specific item is unsuitable and deactivates it, then a content
    author re-runs the script (e.g. to fix a typo or add more items). The reviewer's deactivation
    must survive that re-run untouched -- seed_speaking_prompts() never touches is_verified/
    is_active on an update, in either direction."""
    language_id, language_code = await _make_language(postgres_session_factory)
    async with postgres_session_factory() as db:
        await seed_speaking_prompts(db, language_id=language_id, language_code=language_code, apply=True)

    target_key = db_stable_key(language_code, SPEAKING_PROMPT_SEEDS[0].content_key)
    async with postgres_session_factory() as db:
        row = (
            await db.execute(
                select(LanguagePlacementQuestionBankItem).where(
                    LanguagePlacementQuestionBankItem.stable_key == target_key
                )
            )
        ).scalar_one()
        row.is_verified = False
        row.reviewer_note = "Deactivated by a human reviewer: culturally inappropriate scenario."
        await db.commit()

    async with postgres_session_factory() as db:
        await seed_speaking_prompts(db, language_id=language_id, language_code=language_code, apply=True)

    async with postgres_session_factory() as db:
        row = (
            await db.execute(
                select(LanguagePlacementQuestionBankItem).where(
                    LanguagePlacementQuestionBankItem.stable_key == target_key
                )
            )
        ).scalar_one()
        assert row.is_verified is False, "re-running the seed script reactivated a deliberately deactivated item"
        assert row.reviewer_note == "Deactivated by a human reviewer: culturally inappropriate scenario."

    # Every other item must still be an untouched, MVP-verified item.
    rows = await _all_items_for_language(postgres_session_factory, language_id)
    other_rows = [r for r in rows if r.stable_key != target_key]
    assert len(other_rows) == _EXPECTED_TOTAL_SEEDS - 1
    assert all(r.is_verified is True for r in other_rows)


@pytest.mark.postgresql
async def test_activate_mvp_drafts_upgrades_pristine_draft_rows(postgres_session_factory):
    """Covers the real-world upgrade path: rows already inserted by an older version of
    seed_speaking_prompts() (is_verified=False, source="draft_seed", exactly as this repo's prior
    commit left them) must be elevated to is_verified=True/is_active=True by the explicit,
    separate activation step."""
    language_id, language_code = await _make_language(postgres_session_factory)
    async with postgres_session_factory() as db:
        for seed in SPEAKING_PROMPT_SEEDS:
            row = LanguagePlacementQuestionBankItem(stable_key=db_stable_key(language_code, seed.content_key))
            _apply_content_fields(row, seed, language_id=language_id)
            row.is_verified = False  # the old pre-MVP default, simulated directly
            row.is_active = True
            db.add(row)
        await db.commit()

    rows_before = await _all_items_for_language(postgres_session_factory, language_id)
    assert all(r.is_verified is False for r in rows_before)

    async with postgres_session_factory() as db:
        activated = await activate_mvp_drafts(db, language_code=language_code)
    assert activated == _EXPECTED_TOTAL_SEEDS

    rows_after = await _all_items_for_language(postgres_session_factory, language_id)
    assert len(rows_after) == _EXPECTED_TOTAL_SEEDS
    assert all(r.is_verified is True and r.is_active is True for r in rows_after)


@pytest.mark.postgresql
async def test_activate_mvp_drafts_is_idempotent(postgres_session_factory):
    language_id, language_code = await _make_language(postgres_session_factory)
    async with postgres_session_factory() as db:
        row = LanguagePlacementQuestionBankItem(stable_key=db_stable_key(language_code, SPEAKING_PROMPT_SEEDS[0].content_key))
        _apply_content_fields(row, SPEAKING_PROMPT_SEEDS[0], language_id=language_id)
        row.is_verified = False
        row.is_active = True
        db.add(row)
        await db.commit()

    async with postgres_session_factory() as db:
        first_run = await activate_mvp_drafts(db, language_code=language_code)
    assert first_run == 1

    async with postgres_session_factory() as db:
        second_run = await activate_mvp_drafts(db, language_code=language_code)
    assert second_run == 0


@pytest.mark.postgresql
async def test_activate_mvp_drafts_does_not_touch_rows_a_human_has_modified(postgres_session_factory):
    """A row whose source is no longer "draft_seed" (a human/operator has reclassified it, e.g.
    during review) must never be touched by activation -- even if it happens to still read
    is_verified=False, that is treated as a deliberate decision, not a leftover pristine draft."""
    language_id, language_code = await _make_language(postgres_session_factory)
    seed = SPEAKING_PROMPT_SEEDS[0]
    async with postgres_session_factory() as db:
        row = LanguagePlacementQuestionBankItem(stable_key=db_stable_key(language_code, seed.content_key))
        _apply_content_fields(row, seed, language_id=language_id)
        row.source = "human_reviewed"  # no longer the pristine draft_seed state
        row.is_verified = False
        row.is_active = True
        db.add(row)
        await db.commit()

    async with postgres_session_factory() as db:
        activated = await activate_mvp_drafts(db, language_code=language_code)
    assert activated == 0

    rows = await _all_items_for_language(postgres_session_factory, language_id)
    assert len(rows) == 1
    assert rows[0].is_verified is False
    assert rows[0].source == "human_reviewed"
