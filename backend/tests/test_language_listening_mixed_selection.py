"""Phase 5C: mixed Listening selection (dual-slot pool + position-based MCQ/Gap Fill mixing).

Two layers, matching this repo's established convention:
1. Pure unit tests (no DB) for _resolve_current_exam_item's position-based variant choice and
   fallback rules.
2. Real-Postgres integration tests for the dual-slot pool builders (_question_bank_pool +
   _gap_fill_listening_pool) and for end-to-end state/answer consistency through the real
   _build_state_out / answer_mcq functions.

All rows here are synthetic, isolated fixtures (own throwaway Language row per test) -- no real
listening_mvp_60 data is touched, and no real Gap Fill row is ever activated by these tests.
"""

from __future__ import annotations

import copy
import uuid
from types import SimpleNamespace

import pytest
import pytest_asyncio
from fastapi import BackgroundTasks
from sqlalchemy import delete, select

from app.api import language_exam
from app.models.language.catalog import Language
from app.models.language.enums import LanguageLevel
from app.models.language.exam import LanguageExamSession
from app.models.language.question_bank import LanguagePlacementQuestionBankItem
from app.models.user import User, UserRole
from app.schemas.language_exam import McqAnswerIn

# ------------------------------------------------------------------------------------------
# Pure unit tests: _resolve_current_exam_item (position-based choice + fallback)
# ------------------------------------------------------------------------------------------


def _dual_slot_sec(*, asked_count: int, mcq=None, gap_fill=None) -> dict:
    return {
        "pool": {"A2": {"mcq": mcq, "gap_fill": gap_fill}},
        "current_level": "A2",
        "asked": [{}] * asked_count,
    }


_MCQ_ITEM = {"question": "mcq?", "options": ["a", "b"], "correct_index": 0}
_GAP_FILL_ITEM = {"question": "gap fill?", "accepted_answers": ["x"], "max_words": 1}


def test_position_zero_prefers_mcq():
    sec = _dual_slot_sec(asked_count=0, mcq=_MCQ_ITEM, gap_fill=_GAP_FILL_ITEM)
    item = language_exam._resolve_current_exam_item(sec, "A2", dual_slot=True)
    assert item is _MCQ_ITEM


def test_position_one_prefers_mcq():
    sec = _dual_slot_sec(asked_count=1, mcq=_MCQ_ITEM, gap_fill=_GAP_FILL_ITEM)
    item = language_exam._resolve_current_exam_item(sec, "A2", dual_slot=True)
    assert item is _MCQ_ITEM


def test_position_two_prefers_gap_fill():
    sec = _dual_slot_sec(asked_count=2, mcq=_MCQ_ITEM, gap_fill=_GAP_FILL_ITEM)
    item = language_exam._resolve_current_exam_item(sec, "A2", dual_slot=True)
    assert item is _GAP_FILL_ITEM


def test_position_five_prefers_gap_fill_again():
    sec = _dual_slot_sec(asked_count=5, mcq=_MCQ_ITEM, gap_fill=_GAP_FILL_ITEM)
    item = language_exam._resolve_current_exam_item(sec, "A2", dual_slot=True)
    assert item is _GAP_FILL_ITEM


def test_fallback_to_mcq_when_gap_fill_missing():
    sec = _dual_slot_sec(asked_count=2, mcq=_MCQ_ITEM, gap_fill=None)
    item = language_exam._resolve_current_exam_item(sec, "A2", dual_slot=True)
    assert item is _MCQ_ITEM


def test_fallback_to_gap_fill_when_mcq_missing():
    sec = _dual_slot_sec(asked_count=0, mcq=None, gap_fill=_GAP_FILL_ITEM)
    item = language_exam._resolve_current_exam_item(sec, "A2", dual_slot=True)
    assert item is _GAP_FILL_ITEM


def test_both_missing_resolves_to_none():
    sec = _dual_slot_sec(asked_count=0, mcq=None, gap_fill=None)
    item = language_exam._resolve_current_exam_item(sec, "A2", dual_slot=True)
    assert item is None


def test_non_listening_flat_pool_unaffected_by_position(monkeypatch=None):
    """dual_slot=False (reading/grammar_vocab/legacy listening) is a plain lookup -- position
    never matters, and the item is returned exactly as stored, whatever its keys are."""
    flat_item = {"question": "reading?", "options": ["a", "b"], "correct_index": 1}
    sec = {"pool": {"A2": flat_item}, "current_level": "A2", "asked": [{}] * 5}
    item = language_exam._resolve_current_exam_item(sec, "A2", dual_slot=False)
    assert item is flat_item


def test_legacy_flat_listening_item_used_as_is_under_dual_slot_flag():
    """A pre-Phase-5C in-flight session's listening pool entry is a flat item (no "mcq"/
    "gap_fill" keys) -- _resolve_current_exam_item must not misread it as an empty dual-slot
    container and must return it directly, regardless of asked position."""
    flat_item = {"question": "legacy?", "options": ["a", "b"], "correct_index": 0}
    sec = {"pool": {"A2": flat_item}, "current_level": "A2", "asked": [{}] * 2}
    item = language_exam._resolve_current_exam_item(sec, "A2", dual_slot=True)
    assert item is flat_item


# ------------------------------------------------------------------------------------------
# Postgres-integration tests: dual-slot pool builders against real bank rows.
# ------------------------------------------------------------------------------------------

pytestmark = pytest.mark.postgresql


@pytest_asyncio.fixture
async def mixed_selection_language(postgres_session_factory):
    marker = uuid.uuid4().hex[:8]
    code = f"ms{marker}"
    async with postgres_session_factory() as db:
        lang = Language(code=code, name_en="Mixed selection test", name_ar="Mixed selection test", is_active=True)
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


def _mcq_row(*, language_id: int, level: LanguageLevel, active: bool = True, verified: bool = True):
    return LanguagePlacementQuestionBankItem(
        language_id=language_id,
        skill="listening",
        level=level,
        question_type="mcq",
        prompt_text="Which answer is correct?",
        options_json=["correct", "wrong"],
        correct_index=0,
        body_json={"audio_transcript": "A short listening clip transcript."},
        source="seed",
        is_verified=verified,
        is_active=active,
    )


def _gap_fill_row(*, language_id: int, level: LanguageLevel, active: bool = True, verified: bool = True):
    return LanguagePlacementQuestionBankItem(
        language_id=language_id,
        skill="listening",
        level=level,
        question_type="gap_fill",
        prompt_text="What time does the train leave? ___",
        body_json={
            "audio_transcript": "The train leaves at three pm.",
            "accepted_answers": ["3pm", "3 pm"],
            "max_words": 2,
            "case_sensitive": False,
        },
        source="seed",
        is_verified=verified,
        is_active=active,
    )


# 1. Existing MCQ-only behavior is unchanged while the real (here: synthetic) Gap Fill row is
# inactive -- the gap_fill pool comes back empty for that level, regardless of allow_gap_fill.
async def test_mcq_only_behavior_unchanged_while_gap_fill_row_is_inactive(
    postgres_session_factory, mixed_selection_language
):
    async with postgres_session_factory() as db:
        mcq = _mcq_row(language_id=mixed_selection_language, level=LanguageLevel.A2)
        gap_fill = _gap_fill_row(
            language_id=mixed_selection_language, level=LanguageLevel.A2, active=False, verified=False
        )
        db.add_all([mcq, gap_fill])
        await db.commit()
        mcq_id = mcq.id

    async with postgres_session_factory() as db:
        mcq_pool = await language_exam._question_bank_pool(
            db, language_id=mixed_selection_language, skill="listening", levels=["A2"]
        )
        gap_fill_pool = await language_exam._gap_fill_listening_pool(
            db, language_id=mixed_selection_language, levels=["A2"]
        )
    assert mcq_pool["A2"]["bank_item_id"] == mcq_id
    assert gap_fill_pool == {}


# 2. The dual-slot pool can hold both mcq and gap_fill candidates per level once both are active.
async def test_dual_slot_pool_holds_both_variants_when_both_active(
    postgres_session_factory, mixed_selection_language
):
    async with postgres_session_factory() as db:
        mcq = _mcq_row(language_id=mixed_selection_language, level=LanguageLevel.A2)
        gap_fill = _gap_fill_row(language_id=mixed_selection_language, level=LanguageLevel.A2)
        db.add_all([mcq, gap_fill])
        await db.commit()
        mcq_id, gap_fill_id = mcq.id, gap_fill.id

    async with postgres_session_factory() as db:
        mcq_pool = await language_exam._question_bank_pool(
            db, language_id=mixed_selection_language, skill="listening", levels=["A2"]
        )
        gap_fill_pool = await language_exam._gap_fill_listening_pool(
            db, language_id=mixed_selection_language, levels=["A2"]
        )
    dual_pool = {
        lvl: {"mcq": mcq_pool.get(lvl), "gap_fill": gap_fill_pool.get(lvl)}
        for lvl in set(mcq_pool) | set(gap_fill_pool)
    }
    assert dual_pool["A2"]["mcq"]["bank_item_id"] == mcq_id
    assert dual_pool["A2"]["gap_fill"]["bank_item_id"] == gap_fill_id


# 10. _new_adaptive_section's default (dual_slot=False) path is unaffected for flat MCQ skills:
# grammar_vocab still gets a flat, single-item-per-level pool, while reading now intentionally
# uses curated four-question bundles.
async def test_new_adaptive_section_default_path_is_flat_and_unaffected(
    postgres_session_factory, mixed_selection_language
):
    async with postgres_session_factory() as db:
        mcq = LanguagePlacementQuestionBankItem(
            language_id=mixed_selection_language,
            skill="grammar_vocab",
            level=LanguageLevel.A2,
            question_type="mcq",
            prompt_text="Which answer is correct?",
            passage="A short passage.",
            options_json=["correct", "wrong"],
            correct_index=0,
            source="seed",
            is_verified=True,
            is_active=True,
        )
        db.add(mcq)
        await db.commit()

    async with postgres_session_factory() as db:
        r_pool = await language_exam._question_bank_pool(
            db, language_id=mixed_selection_language, skill="grammar_vocab", levels=["A2"]
        )
    section = language_exam._new_adaptive_section(r_pool, "A2")
    item = section["pool"]["A2"]
    assert "mcq" not in item and "gap_fill" not in item
    assert item.get("question_token")
    assert item["question"] == "Which answer is correct?"


# ------------------------------------------------------------------------------------------
# Postgres-integration tests: end-to-end state/answer consistency through a synthetic session.
# ------------------------------------------------------------------------------------------


@pytest_asyncio.fixture
async def mixed_exam_record(postgres_session_factory):
    """Minimal isolated student/language/exam-session row, cleaned up after the test -- mirrors
    gap_fill_exam_record in test_language_listening_gap_fill_scoring.py, kept local here so this
    feature's tests are self-contained."""
    created: list[tuple[str, int, int]] = []

    async def create(*, state: dict, status: str = "in_progress") -> SimpleNamespace:
        marker = uuid.uuid4().hex
        async with postgres_session_factory() as db:
            student = User(
                email=f"mixed-sel-{marker}@example.test",
                name="Mixed Selection Test Student",
                hashed_password="not-used",
                role=UserRole.student,
            )
            language = Language(
                code=f"mx{marker[:10]}", name_en="English", name_ar="English", is_active=True
            )
            db.add_all([student, language])
            await db.flush()
            exam = LanguageExamSession(
                id=uuid.uuid4().hex,
                student_id=student.id,
                language_id=language.id,
                current_step=1,
                max_steps=max(1, len(state.get("sections") or [])),
                exam_state=copy.deepcopy(state),
                status=status,
                is_completed=False,
            )
            db.add(exam)
            await db.commit()
            created.append((exam.id, student.id, language.id))
            return SimpleNamespace(session_id=exam.id, student=SimpleNamespace(id=student.id))

    yield create

    async with postgres_session_factory() as db:
        for session_id, student_id, language_id in created:
            await db.execute(delete(LanguageExamSession).where(LanguageExamSession.id == session_id))
            await db.execute(delete(User).where(User.id == student_id))
            await db.execute(delete(Language).where(Language.id == language_id))
        await db.commit()


async def _stored(postgres_session_factory, session_id: str) -> LanguageExamSession:
    async with postgres_session_factory() as db:
        return (
            await db.execute(select(LanguageExamSession).where(LanguageExamSession.id == session_id))
        ).scalar_one()


def _dual_slot_state(*, asked_count: int, revision: int = 5) -> dict:
    """A Listening section whose A2 level holds both an mcq and a gap_fill candidate, with
    `asked_count` prior (synthetic) answers already recorded -- drives which variant
    _resolve_current_exam_item will pick."""
    mcq_item = {
        "level": "A2",
        "question": "Which answer is correct?",
        "question_type": "mcq",
        "options": ["correct", "wrong"],
        "correct_index": 0,
        "audio_url": "/uploads/language_exam_audio/mixed-mcq-clip.wav",
        "question_token": "mixed-mcq-token-0000000000001",
    }
    gap_fill_item = {
        "level": "A2",
        "question": "What time does the train leave? ___",
        "question_type": "gap_fill",
        "accepted_answers": ["3pm", "3 pm"],
        "max_words": 2,
        "case_sensitive": False,
        "audio_url": "/uploads/language_exam_audio/mixed-gap-fill-clip.wav",
        "question_token": "mixed-gap-fill-token-000000001",
    }
    return {
        "version": 3,
        "state_revision": revision,
        "sections": ["listening"],
        "cursor": 0,
        "listening": {
            "pool": {"A2": {"mcq": mcq_item, "gap_fill": gap_fill_item}},
            "current_level": "A2",
            # Minimal valid placeholder entries -- answer_mcq's adaptive-level logic reads
            # "level" off every entry in "asked", not just the one it's about to append.
            "asked": [{"level": "A2", "correct": True, "chosen_index": 0} for _ in range(asked_count)],
            "max_steps": 5,
            "ready": True,
            "done": False,
            "evidence_status": "missing_student_response",
        },
        "request_receipts": [],
    }


async def _submit(postgres_session_factory, record, body: McqAnswerIn):
    async with postgres_session_factory() as db:
        return await language_exam.answer_mcq(
            record.session_id, body, BackgroundTasks(), student=record.student, db=db
        )


# 6. _build_state_out and answer_mcq resolve the same current item (mcq at position 0).
async def test_build_state_out_and_answer_mcq_agree_at_position_zero_mcq(
    postgres_session_factory, mixed_exam_record
):
    state = _dual_slot_state(asked_count=0)
    record = await mixed_exam_record(state=state)
    async with postgres_session_factory() as db:
        sess = (
            await db.execute(select(LanguageExamSession).where(LanguageExamSession.id == record.session_id))
        ).scalar_one()
        out = await language_exam._build_state_out(db, sess)
    assert out.mcq.question_type == "mcq"
    assert out.mcq.question_token == "mixed-mcq-token-0000000000001"

    body = McqAnswerIn(
        choice_index=0,
        request_id="mixed-req-0000001",
        state_revision=state["state_revision"],
        question_token=out.mcq.question_token,
    )
    await _submit(postgres_session_factory, record, body)
    stored = await _stored(postgres_session_factory, record.session_id)
    entry = stored.exam_state["listening"]["asked"][0]
    assert entry["correct"] is True
    assert entry["chosen_index"] == 0
    assert "answer_text" not in entry


# 6-7. _build_state_out and answer_mcq resolve the same current item (gap_fill at position 2),
# and the Gap Fill answer_text is scored correctly through the mixed selection path.
async def test_build_state_out_and_answer_mcq_agree_at_position_two_gap_fill(
    postgres_session_factory, mixed_exam_record
):
    state = _dual_slot_state(asked_count=2)
    record = await mixed_exam_record(state=state)
    async with postgres_session_factory() as db:
        sess = (
            await db.execute(select(LanguageExamSession).where(LanguageExamSession.id == record.session_id))
        ).scalar_one()
        out = await language_exam._build_state_out(db, sess)
    assert out.mcq.question_type == "gap_fill"
    assert out.mcq.question_token == "mixed-gap-fill-token-000000001"

    body = McqAnswerIn(
        answer_text="3pm",
        request_id="mixed-req-0000002",
        state_revision=state["state_revision"],
        question_token=out.mcq.question_token,
    )
    await _submit(postgres_session_factory, record, body)
    stored = await _stored(postgres_session_factory, record.session_id)
    # asked grows from the 2 synthetic empty-dict placeholders to include this real entry at [2].
    entry = stored.exam_state["listening"]["asked"][2]
    assert entry["correct"] is True
    assert entry["question_type"] == "gap_fill"


# 8. asked-history records answer_text for Gap Fill (proven above) and chosen_index for MCQ
# (proven in test_build_state_out_and_answer_mcq_agree_at_position_zero_mcq) -- this test proves
# the incorrect-gap-fill-answer path too, so both correct/incorrect are covered for the mixed path.
async def test_gap_fill_incorrect_answer_recorded_with_answer_text_through_mixed_selection(
    postgres_session_factory, mixed_exam_record
):
    state = _dual_slot_state(asked_count=2)
    record = await mixed_exam_record(state=state)
    async with postgres_session_factory() as db:
        sess = (
            await db.execute(select(LanguageExamSession).where(LanguageExamSession.id == record.session_id))
        ).scalar_one()
        out = await language_exam._build_state_out(db, sess)
    body = McqAnswerIn(
        answer_text="midnight",
        request_id="mixed-req-0000003",
        state_revision=state["state_revision"],
        question_token=out.mcq.question_token,
    )
    await _submit(postgres_session_factory, record, body)
    stored = await _stored(postgres_session_factory, record.session_id)
    entry = stored.exam_state["listening"]["asked"][2]
    assert entry["correct"] is False
    assert entry["answer_text"] == "midnight"
    assert entry["chosen_index"] is None
