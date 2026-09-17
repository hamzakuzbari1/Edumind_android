"""Durable question_type selection guard (Phase 5A).

select_placement_bank_items() gained an `allow_gap_fill: bool = False` parameter -- a
code-level guard independent of is_active/is_verified, since those two flags alone were never
meant to be the only thing preventing an unsupported question_type (Gap Fill, before frontend
rendering exists) from reaching a student. This guard does not change is_active/is_verified
behavior and does not activate any row; it only narrows which question_type the query can return.

These tests use synthetic, isolated bank rows (own throwaway Language row per test) -- no
real listening_mvp_60 data is touched or required.
"""

from __future__ import annotations

import uuid

import pytest
import pytest_asyncio
from sqlalchemy import delete

from app.models.language.catalog import Language
from app.models.language.enums import LanguageLevel
from app.models.language.question_bank import LanguagePlacementQuestionBankItem
from app.services.language_placement_question_bank_service import select_placement_bank_items

pytestmark = pytest.mark.postgresql


@pytest_asyncio.fixture
async def guard_test_language(postgres_session_factory):
    marker = uuid.uuid4().hex[:8]
    code = f"gg{marker}"
    async with postgres_session_factory() as db:
        lang = Language(code=code, name_en="Gap fill guard test", name_ar="Gap fill guard test", is_active=True)
        db.add(lang)
        await db.commit()
        language_id = lang.id
    yield language_id
    async with postgres_session_factory() as db:
        await db.execute(
            delete(LanguagePlacementQuestionBankItem).where(
                LanguagePlacementQuestionBankItem.language_id == language_id
            )
        )
        await db.execute(delete(Language).where(Language.id == language_id))
        await db.commit()


async def _seed_pair(postgres_session_factory, *, language_id: int, skill: str = "listening") -> dict:
    """Insert one active+verified mcq row and one active+verified gap_fill row at A2, same skill."""
    async with postgres_session_factory() as db:
        mcq = LanguagePlacementQuestionBankItem(
            language_id=language_id,
            skill=skill,
            level=LanguageLevel.A2,
            question_type="mcq",
            prompt_text="Which answer is correct?",
            options_json=["correct", "wrong"],
            correct_index=0,
            source="seed",
            is_verified=True,
            is_active=True,
        )
        gap_fill = LanguagePlacementQuestionBankItem(
            language_id=language_id,
            skill=skill,
            level=LanguageLevel.A2,
            question_type="gap_fill",
            prompt_text="What time does the train leave? ___",
            body_json={"accepted_answers": ["3pm"], "max_words": 2, "case_sensitive": False},
            source="seed",
            is_verified=True,
            is_active=True,
        )
        db.add_all([mcq, gap_fill])
        await db.commit()
        return {"mcq_id": mcq.id, "gap_fill_id": gap_fill.id}


# 5. Default behavior (allow_gap_fill not passed) excludes gap_fill rows entirely.
async def test_default_selection_excludes_gap_fill_rows(postgres_session_factory, guard_test_language):
    ids = await _seed_pair(postgres_session_factory, language_id=guard_test_language)
    async with postgres_session_factory() as db:
        results = await select_placement_bank_items(
            db, language_id=guard_test_language, skill="listening", level=LanguageLevel.A2, count=10
        )
    returned_ids = {row.id for row in results}
    assert ids["gap_fill_id"] not in returned_ids
    assert ids["mcq_id"] in returned_ids
    assert all(row.question_type == "mcq" for row in results)


# 6. Explicit allow_gap_fill=False excludes gap_fill even though it is active AND verified.
async def test_allow_gap_fill_false_excludes_active_verified_gap_fill(
    postgres_session_factory, guard_test_language
):
    ids = await _seed_pair(postgres_session_factory, language_id=guard_test_language)
    async with postgres_session_factory() as db:
        results = await select_placement_bank_items(
            db,
            language_id=guard_test_language,
            skill="listening",
            level=LanguageLevel.A2,
            count=10,
            allow_gap_fill=False,
        )
    returned_ids = {row.id for row in results}
    assert ids["gap_fill_id"] not in returned_ids
    assert ids["mcq_id"] in returned_ids


# 7. allow_gap_fill=True can return gap_fill rows (alongside mcq, both still active+verified).
async def test_allow_gap_fill_true_can_return_gap_fill_rows(postgres_session_factory, guard_test_language):
    ids = await _seed_pair(postgres_session_factory, language_id=guard_test_language)
    async with postgres_session_factory() as db:
        results = await select_placement_bank_items(
            db,
            language_id=guard_test_language,
            skill="listening",
            level=LanguageLevel.A2,
            count=10,
            allow_gap_fill=True,
        )
    returned_ids = {row.id for row in results}
    assert ids["gap_fill_id"] in returned_ids
    assert ids["mcq_id"] in returned_ids


# 8. Existing MCQ-only selection behavior is unchanged by the new parameter's default.
async def test_mcq_only_selection_behavior_unchanged_by_default_guard(
    postgres_session_factory, guard_test_language
):
    async with postgres_session_factory() as db:
        mcq_only = LanguagePlacementQuestionBankItem(
            language_id=guard_test_language,
            skill="listening",
            level=LanguageLevel.B1,
            question_type="mcq",
            prompt_text="Pick the right one.",
            options_json=["a", "b"],
            correct_index=1,
            source="seed",
            is_verified=True,
            is_active=True,
        )
        db.add(mcq_only)
        await db.commit()
        mcq_only_id = mcq_only.id

    async with postgres_session_factory() as db:
        results = await select_placement_bank_items(
            db, language_id=guard_test_language, skill="listening", level=LanguageLevel.B1, count=10
        )
    assert {row.id for row in results} == {mcq_only_id}


# 9. Real Listening MCQ rows (any is_active/is_verified mcq row) remain selectable through the guard.
async def test_existing_active_verified_mcq_rows_remain_selectable(
    postgres_session_factory, guard_test_language
):
    ids = await _seed_pair(postgres_session_factory, language_id=guard_test_language)
    async with postgres_session_factory() as db:
        results = await select_placement_bank_items(
            db, language_id=guard_test_language, skill="listening", level=LanguageLevel.A2, count=10
        )
    assert any(row.id == ids["mcq_id"] and row.is_active and row.is_verified for row in results)


# 10. Other callers/skills (reading, grammar_vocab) are unaffected by the new default guard -- a
# gap_fill row seeded under a different skill is excluded by default there too, and existing mcq
# rows for those skills are returned exactly as before (guard is skill-agnostic, not listening-only).
@pytest.mark.parametrize("skill", ["reading", "grammar_vocab"])
async def test_default_guard_applies_generically_without_affecting_other_skill_callers(
    postgres_session_factory, guard_test_language, skill
):
    ids = await _seed_pair(postgres_session_factory, language_id=guard_test_language, skill=skill)
    async with postgres_session_factory() as db:
        results = await select_placement_bank_items(
            db, language_id=guard_test_language, skill=skill, level=LanguageLevel.A2, count=10
        )
    returned_ids = {row.id for row in results}
    assert ids["gap_fill_id"] not in returned_ids
    assert ids["mcq_id"] in returned_ids
