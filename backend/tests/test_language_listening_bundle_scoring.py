"""Phase 6A: Listening task bundles (MCQ x3 subquestions, Gap Fill x3-blank note completion).

A bundle is still exactly one adaptive-pool item/passage -- the staircase moves one CEFR level
per passage exactly as before (adaptive_next_level/adaptive_result are untouched). Only the
*scoring* of that one passage now rolls up from several sub-answers via strict majority
(_majority_correct: sum(flags) * 2 > len(flags) -- a 1-1 tie on 2 items is NOT correct).

Two layers, matching this repo's established convention:
1. Pure unit tests (no DB) for _majority_correct and the bundle validity helpers.
2. Real-Postgres integration tests for the real answer_mcq()/_build_state_out() functions,
   using a synthetic exam session (mirrors gap_fill_exam_record in
   test_language_listening_gap_fill_scoring.py / mixed_exam_record in
   test_language_listening_mixed_selection.py) -- kept self-contained here.
"""

from __future__ import annotations

import copy
import uuid
from types import SimpleNamespace

import pytest
import pytest_asyncio
from fastapi import BackgroundTasks, HTTPException
from sqlalchemy import delete, select

from app.api import language_exam
from app.models.language.catalog import Language
from app.models.language.exam import LanguageExamSession
from app.models.user import User, UserRole
from app.schemas.language_exam import McqAnswerIn
from app.services.language_exam_service import adaptive_result

# ------------------------------------------------------------------------------------------
# Pure unit tests: _majority_correct
# ------------------------------------------------------------------------------------------


def test_majority_correct_3_of_3():
    assert language_exam._majority_correct([True, True, True]) is True


def test_majority_correct_2_of_3():
    assert language_exam._majority_correct([True, True, False]) is True


def test_majority_correct_1_of_3():
    assert language_exam._majority_correct([True, False, False]) is False


def test_majority_correct_0_of_3():
    assert language_exam._majority_correct([False, False, False]) is False


def test_majority_correct_2_of_2_tie_broken_true():
    assert language_exam._majority_correct([True, True]) is True


def test_majority_correct_1_of_2_is_a_tie_and_not_correct():
    assert language_exam._majority_correct([True, False]) is False


def test_majority_correct_0_of_2():
    assert language_exam._majority_correct([False, False]) is False


# ------------------------------------------------------------------------------------------
# Pure unit tests: _is_valid_mcq_bundle_item / _is_valid_gap_fill_bundle_item
# ------------------------------------------------------------------------------------------


def _valid_subquestion(correct_index=0):
    return {
        "question": "What time does the train leave?",
        "options": ["3pm", "4pm", "5pm", "6pm"],
        "correct_index": correct_index,
    }


def _valid_mcq_bundle_item():
    return {"subquestions": [_valid_subquestion(0), _valid_subquestion(1), _valid_subquestion(2)]}


def test_mcq_bundle_valid_item_passes():
    assert language_exam._is_valid_mcq_bundle_item(_valid_mcq_bundle_item()) is True


def test_mcq_bundle_rejects_wrong_subquestion_count():
    item = _valid_mcq_bundle_item()
    item["subquestions"] = item["subquestions"][:2]
    assert language_exam._is_valid_mcq_bundle_item(item) is False


def test_mcq_bundle_rejects_missing_question_text():
    item = _valid_mcq_bundle_item()
    item["subquestions"][0]["question"] = ""
    assert language_exam._is_valid_mcq_bundle_item(item) is False


def test_mcq_bundle_rejects_wrong_option_count():
    item = _valid_mcq_bundle_item()
    item["subquestions"][1]["options"] = ["a", "b", "c"]
    assert language_exam._is_valid_mcq_bundle_item(item) is False


def test_mcq_bundle_rejects_out_of_range_correct_index():
    item = _valid_mcq_bundle_item()
    item["subquestions"][2]["correct_index"] = 4
    assert language_exam._is_valid_mcq_bundle_item(item) is False


def test_mcq_bundle_rejects_bool_correct_index():
    item = _valid_mcq_bundle_item()
    item["subquestions"][0]["correct_index"] = True
    assert language_exam._is_valid_mcq_bundle_item(item) is False


def test_mcq_bundle_rejects_non_list_subquestions():
    assert language_exam._is_valid_mcq_bundle_item({"subquestions": "not-a-list"}) is False


def _valid_blank():
    return {"accepted_answers": ["3pm", "3 pm"], "max_words": 2, "case_sensitive": False}


def _valid_gap_fill_bundle_item():
    return {
        "note_template": "Departure: {{1}}. Platform: {{2}}. Price: {{3}}.",
        "blanks": [_valid_blank(), _valid_blank(), _valid_blank()],
    }


def test_gap_fill_bundle_valid_item_passes():
    assert language_exam._is_valid_gap_fill_bundle_item(_valid_gap_fill_bundle_item()) is True


def test_gap_fill_bundle_rejects_wrong_blank_count():
    item = _valid_gap_fill_bundle_item()
    item["blanks"] = item["blanks"][:2]
    assert language_exam._is_valid_gap_fill_bundle_item(item) is False


def test_gap_fill_bundle_rejects_missing_token():
    item = _valid_gap_fill_bundle_item()
    item["note_template"] = "Departure: {{1}}. Platform: {{2}}."  # missing {{3}}
    assert language_exam._is_valid_gap_fill_bundle_item(item) is False


def test_gap_fill_bundle_rejects_duplicated_token():
    item = _valid_gap_fill_bundle_item()
    item["note_template"] = "Departure: {{1}}. Platform: {{1}}. Price: {{3}}."
    assert language_exam._is_valid_gap_fill_bundle_item(item) is False


def test_gap_fill_bundle_rejects_malformed_blank_content():
    item = _valid_gap_fill_bundle_item()
    item["blanks"][1] = {"accepted_answers": [], "max_words": 2, "case_sensitive": False}
    assert language_exam._is_valid_gap_fill_bundle_item(item) is False


def test_gap_fill_bundle_rejects_missing_note_template():
    item = _valid_gap_fill_bundle_item()
    item["note_template"] = None
    assert language_exam._is_valid_gap_fill_bundle_item(item) is False


# ------------------------------------------------------------------------------------------
# adaptive_result still sees exactly one correct bool per passage, regardless of bundle shape.
# ------------------------------------------------------------------------------------------


def test_adaptive_result_reads_only_level_and_correct_for_bundle_entries():
    asked = [
        {"level": "A2", "correct": True, "chosen_indices": [0, 1, 2], "sub_correct": [True, True, False]},
        {"level": "B1", "correct": False, "answer_texts": ["x", "y", "z"], "sub_correct": [False, False, True]},
    ]
    level, pct = adaptive_result(asked)
    assert level.value == "A2"
    assert pct == 50.0


# ------------------------------------------------------------------------------------------
# Postgres-integration tests: the real answer_mcq()/_build_state_out() functions.
# ------------------------------------------------------------------------------------------

pytestmark = pytest.mark.postgresql


@pytest_asyncio.fixture
async def bundle_exam_record(postgres_session_factory):
    """Minimal isolated student/language/exam-session row, cleaned up after the test -- mirrors
    gap_fill_exam_record / mixed_exam_record in the sibling listening test files."""
    created: list[tuple[str, int, int]] = []

    async def create(*, state: dict, status: str = "in_progress") -> SimpleNamespace:
        marker = uuid.uuid4().hex
        async with postgres_session_factory() as db:
            student = User(
                email=f"bundle-{marker}@example.test",
                name="Bundle Test Student",
                hashed_password="not-used",
                role=UserRole.student,
            )
            language = Language(
                code=f"bn{marker[:10]}", name_en="English", name_ar="English", is_active=True
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


def _mcq_bundle_state(*, revision: int = 5) -> dict:
    item = {
        "level": "A2",
        "question_type": "mcq",
        "audio_url": "/uploads/language_exam_audio/bundle-mcq-clip.wav",
        "question_token": "bundle-mcq-token-00000000001",
        "subquestions": [
            {"question": "Main idea?", "options": ["a", "b", "c", "d"], "correct_index": 0},
            {"question": "Detail?", "options": ["a", "b", "c", "d"], "correct_index": 1},
            {"question": "Reason?", "options": ["a", "b", "c", "d"], "correct_index": 2},
        ],
    }
    return {
        "version": 3,
        "state_revision": revision,
        "sections": ["listening"],
        "cursor": 0,
        "listening": {
            "pool": {"A2": item},
            "current_level": "A2",
            "asked": [],
            "max_steps": 1,
            "ready": True,
            "done": False,
            "evidence_status": "missing_student_response",
        },
        "request_receipts": [],
    }


def _gap_fill_bundle_state(*, revision: int = 5) -> dict:
    item = {
        "level": "A2",
        "question_type": "gap_fill",
        "audio_url": "/uploads/language_exam_audio/bundle-gap-fill-clip.wav",
        "question_token": "bundle-gf-token-000000000001",
        "note_template": "Departure: {{1}}. Platform: {{2}}. Price: {{3}}.",
        "blanks": [
            {"accepted_answers": ["3pm", "3 pm"], "max_words": 2, "case_sensitive": False},
            {"accepted_answers": ["six"], "max_words": 1, "case_sensitive": False},
            {"accepted_answers": ["ten pounds"], "max_words": 2, "case_sensitive": False},
        ],
    }
    return {
        "version": 3,
        "state_revision": revision,
        "sections": ["listening"],
        "cursor": 0,
        "listening": {
            "pool": {"A2": item},
            "current_level": "A2",
            "asked": [],
            "max_steps": 1,
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


# --- MCQ bundle: state output never leaks correct_index ---
async def test_mcq_bundle_state_output_exposes_subquestions_without_correct_index(
    postgres_session_factory, bundle_exam_record
):
    state = _mcq_bundle_state()
    record = await bundle_exam_record(state=state)
    async with postgres_session_factory() as db:
        sess = (
            await db.execute(select(LanguageExamSession).where(LanguageExamSession.id == record.session_id))
        ).scalar_one()
        out = await language_exam._build_state_out(db, sess)
    assert out.mcq.question_type == "mcq"
    assert len(out.mcq.subquestions) == 3
    encoded = out.model_dump_json()
    assert "correct_index" not in encoded


# --- MCQ bundle scoring: 3/3, 2/3, 1/3, 0/3 ---
@pytest.mark.parametrize(
    "choice_indices,expected_correct,expected_sub_correct",
    [
        ([0, 1, 2], True, [True, True, True]),
        ([0, 1, 3], True, [True, True, False]),
        ([0, 3, 3], False, [True, False, False]),
        ([3, 3, 3], False, [False, False, False]),
    ],
)
async def test_mcq_bundle_scoring_majority(
    postgres_session_factory, bundle_exam_record, choice_indices, expected_correct, expected_sub_correct
):
    state = _mcq_bundle_state()
    record = await bundle_exam_record(state=state)
    body = McqAnswerIn(
        choice_indices=choice_indices,
        request_id=f"bundle-mcq-req-{uuid.uuid4().hex[:8]}",
        state_revision=state["state_revision"],
        question_token=state["listening"]["pool"]["A2"]["question_token"],
    )
    await _submit(postgres_session_factory, record, body)
    stored = await _stored(postgres_session_factory, record.session_id)
    entry = stored.exam_state["listening"]["asked"][0]
    assert entry["correct"] is expected_correct
    assert entry["sub_correct"] == expected_sub_correct
    assert entry["chosen_indices"] == choice_indices
    assert entry["question_type"] == "mcq"


async def test_mcq_bundle_rejects_choice_index_singular(postgres_session_factory, bundle_exam_record):
    state = _mcq_bundle_state()
    record = await bundle_exam_record(state=state)
    body = McqAnswerIn(
        choice_index=0,
        request_id="bundle-mcq-req-singular",
        state_revision=state["state_revision"],
        question_token=state["listening"]["pool"]["A2"]["question_token"],
    )
    with pytest.raises(HTTPException) as exc_info:
        await _submit(postgres_session_factory, record, body)
    assert exc_info.value.status_code == 400
    stored = await _stored(postgres_session_factory, record.session_id)
    assert stored.exam_state["listening"]["asked"] == []


async def test_mcq_bundle_rejects_wrong_length_choice_indices(postgres_session_factory, bundle_exam_record):
    state = _mcq_bundle_state()
    record = await bundle_exam_record(state=state)
    body = McqAnswerIn(
        choice_indices=[0, 1],
        request_id="bundle-mcq-req-shortlen",
        state_revision=state["state_revision"],
        question_token=state["listening"]["pool"]["A2"]["question_token"],
    )
    with pytest.raises(HTTPException) as exc_info:
        await _submit(postgres_session_factory, record, body)
    assert exc_info.value.status_code == 400
    stored = await _stored(postgres_session_factory, record.session_id)
    assert stored.exam_state["listening"]["asked"] == []


# --- Gap Fill bundle: state output never leaks accepted_answers/max_words ---
async def test_gap_fill_bundle_state_output_exposes_note_template_without_answers(
    postgres_session_factory, bundle_exam_record
):
    state = _gap_fill_bundle_state()
    record = await bundle_exam_record(state=state)
    async with postgres_session_factory() as db:
        sess = (
            await db.execute(select(LanguageExamSession).where(LanguageExamSession.id == record.session_id))
        ).scalar_one()
        out = await language_exam._build_state_out(db, sess)
    assert out.mcq.question_type == "gap_fill"
    assert out.mcq.note_template == "Departure: {{1}}. Platform: {{2}}. Price: {{3}}."
    assert out.mcq.blank_count == 3
    encoded = out.model_dump_json()
    assert "accepted_answers" not in encoded
    assert "max_words" not in encoded
    assert "ten pounds" not in encoded


# --- Gap Fill bundle scoring: 3/3, 2/3, 1/3, 0/3 ---
@pytest.mark.parametrize(
    "answer_texts,expected_correct,expected_sub_correct",
    [
        (["3pm", "six", "ten pounds"], True, [True, True, True]),
        (["3pm", "six", "wrong"], True, [True, True, False]),
        (["3pm", "wrong", "wrong"], False, [True, False, False]),
        (["wrong", "wrong", "wrong"], False, [False, False, False]),
    ],
)
async def test_gap_fill_bundle_scoring_majority(
    postgres_session_factory, bundle_exam_record, answer_texts, expected_correct, expected_sub_correct
):
    state = _gap_fill_bundle_state()
    record = await bundle_exam_record(state=state)
    body = McqAnswerIn(
        answer_texts=answer_texts,
        request_id=f"bundle-gf-req-{uuid.uuid4().hex[:8]}",
        state_revision=state["state_revision"],
        question_token=state["listening"]["pool"]["A2"]["question_token"],
    )
    await _submit(postgres_session_factory, record, body)
    stored = await _stored(postgres_session_factory, record.session_id)
    entry = stored.exam_state["listening"]["asked"][0]
    assert entry["correct"] is expected_correct
    assert entry["sub_correct"] == expected_sub_correct
    assert entry["question_type"] == "gap_fill"
    assert len(entry["answer_texts"]) == 3


async def test_gap_fill_bundle_over_max_words_rejected_without_mutation(
    postgres_session_factory, bundle_exam_record
):
    state = _gap_fill_bundle_state()
    record = await bundle_exam_record(state=state)
    body = McqAnswerIn(
        answer_texts=["3pm exactly now please", "six", "ten pounds"],
        request_id="bundle-gf-req-maxwords",
        state_revision=state["state_revision"],
        question_token=state["listening"]["pool"]["A2"]["question_token"],
    )
    with pytest.raises(HTTPException) as exc_info:
        await _submit(postgres_session_factory, record, body)
    assert exc_info.value.status_code == 422
    stored = await _stored(postgres_session_factory, record.session_id)
    assert stored.exam_state["listening"]["asked"] == []


async def test_gap_fill_bundle_wrong_length_answer_texts_rejected(postgres_session_factory, bundle_exam_record):
    state = _gap_fill_bundle_state()
    record = await bundle_exam_record(state=state)
    body = McqAnswerIn(
        answer_texts=["3pm", "six"],
        request_id="bundle-gf-req-shortlen",
        state_revision=state["state_revision"],
        question_token=state["listening"]["pool"]["A2"]["question_token"],
    )
    with pytest.raises(HTTPException) as exc_info:
        await _submit(postgres_session_factory, record, body)
    assert exc_info.value.status_code == 400
    stored = await _stored(postgres_session_factory, record.session_id)
    assert stored.exam_state["listening"]["asked"] == []


async def test_gap_fill_bundle_malformed_blank_fails_closed_without_mutation(
    postgres_session_factory, bundle_exam_record
):
    state = _gap_fill_bundle_state()
    state["listening"]["pool"]["A2"]["blanks"][1]["accepted_answers"] = []
    record = await bundle_exam_record(state=state)
    body = McqAnswerIn(
        answer_texts=["3pm", "six", "ten pounds"],
        request_id="bundle-gf-req-malformed",
        state_revision=state["state_revision"],
        question_token=state["listening"]["pool"]["A2"]["question_token"],
    )
    with pytest.raises(HTTPException) as exc_info:
        await _submit(postgres_session_factory, record, body)
    assert exc_info.value.status_code == 503
    assert exc_info.value.detail["code"] == "content_unavailable"
    stored = await _stored(postgres_session_factory, record.session_id)
    assert stored.exam_state["listening"]["asked"] == []


async def test_gap_fill_bundle_rejects_answer_text_singular(postgres_session_factory, bundle_exam_record):
    state = _gap_fill_bundle_state()
    record = await bundle_exam_record(state=state)
    body = McqAnswerIn(
        answer_text="3pm",
        request_id="bundle-gf-req-singular",
        state_revision=state["state_revision"],
        question_token=state["listening"]["pool"]["A2"]["question_token"],
    )
    with pytest.raises(HTTPException) as exc_info:
        await _submit(postgres_session_factory, record, body)
    assert exc_info.value.status_code == 400
    stored = await _stored(postgres_session_factory, record.session_id)
    assert stored.exam_state["listening"]["asked"] == []


# --- Legacy single MCQ / Gap Fill unaffected (regression, using the same bundle-capable code path) ---
async def test_legacy_single_mcq_still_works_after_bundle_support_added(
    postgres_session_factory, bundle_exam_record
):
    state = {
        "version": 3,
        "state_revision": 5,
        "sections": ["listening"],
        "cursor": 0,
        "listening": {
            "pool": {
                "A2": {
                    "level": "A2",
                    "question": "Which answer is correct?",
                    "options": ["correct", "wrong"],
                    "correct_index": 0,
                    "audio_url": "/uploads/language_exam_audio/legacy-mcq-clip.wav",
                    "question_token": "legacy-mcq-token-0000000001",
                }
            },
            "current_level": "A2",
            "asked": [],
            "max_steps": 1,
            "ready": True,
            "done": False,
            "evidence_status": "missing_student_response",
        },
        "request_receipts": [],
    }
    record = await bundle_exam_record(state=state)
    body = McqAnswerIn(
        choice_index=0,
        request_id="legacy-mcq-req-0000001",
        state_revision=state["state_revision"],
        question_token=state["listening"]["pool"]["A2"]["question_token"],
    )
    await _submit(postgres_session_factory, record, body)
    stored = await _stored(postgres_session_factory, record.session_id)
    entry = stored.exam_state["listening"]["asked"][0]
    assert entry["correct"] is True
    assert entry["chosen_index"] == 0
    assert "sub_correct" not in entry


async def test_legacy_single_gap_fill_still_works_after_bundle_support_added(
    postgres_session_factory, bundle_exam_record
):
    state = {
        "version": 3,
        "state_revision": 5,
        "sections": ["listening"],
        "cursor": 0,
        "listening": {
            "pool": {
                "A2": {
                    "level": "A2",
                    "question": "What time does the train leave? ___",
                    "question_type": "gap_fill",
                    "accepted_answers": ["3pm", "3 pm"],
                    "max_words": 2,
                    "case_sensitive": False,
                    "audio_url": "/uploads/language_exam_audio/legacy-gf-clip.wav",
                    "question_token": "legacy-gf-token-00000000001",
                }
            },
            "current_level": "A2",
            "asked": [],
            "max_steps": 1,
            "ready": True,
            "done": False,
            "evidence_status": "missing_student_response",
        },
        "request_receipts": [],
    }
    record = await bundle_exam_record(state=state)
    body = McqAnswerIn(
        answer_text="3pm",
        request_id="legacy-gf-req-0000001",
        state_revision=state["state_revision"],
        question_token=state["listening"]["pool"]["A2"]["question_token"],
    )
    await _submit(postgres_session_factory, record, body)
    stored = await _stored(postgres_session_factory, record.session_id)
    entry = stored.exam_state["listening"]["asked"][0]
    assert entry["correct"] is True
    assert entry["answer_text"] == "3pm"
    assert "sub_correct" not in entry


# --- Idempotency: a genuinely different bundle payload reusing request_id is rejected, not replayed ---
async def test_mcq_bundle_reused_request_id_with_different_payload_is_rejected(
    postgres_session_factory, bundle_exam_record
):
    state = _mcq_bundle_state()
    record = await bundle_exam_record(state=state)
    shared_request_id = "bundle-mcq-idempotency-req"
    first = McqAnswerIn(
        choice_indices=[0, 1, 2],
        request_id=shared_request_id,
        state_revision=state["state_revision"],
        question_token=state["listening"]["pool"]["A2"]["question_token"],
    )
    await _submit(postgres_session_factory, record, first)

    # A second, different bundle submission must not silently replay the first result.
    stored_after_first = await _stored(postgres_session_factory, record.session_id)
    second = McqAnswerIn(
        choice_indices=[3, 3, 3],
        request_id=shared_request_id,
        state_revision=stored_after_first.exam_state["state_revision"],
        question_token=stored_after_first.exam_state["listening"]["pool"]["A2"]["question_token"],
    )
    with pytest.raises(HTTPException) as exc_info:
        await _submit(postgres_session_factory, record, second)
    assert exc_info.value.status_code == 409
    assert exc_info.value.detail["code"] == "idempotency_conflict"
