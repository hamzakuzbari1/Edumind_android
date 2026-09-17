"""Deterministic Gap Fill backend scoring (feat(listening): add deterministic gap fill scoring).

Two layers:
1. Pure unit tests (no DB) for the normalization/validation helpers in
   app/services/language_gap_fill_service.py.
2. Real-Postgres integration tests (mirroring test_language_exam_postgresql_concurrency.py's own
   conventions -- exam_record_factory-style fixture, answer_mcq called directly) for the actual
   submission endpoint: request-contract rejection, scoring, adaptive continuation, state-mutation
   safety on rejection, and public-response hiding.

All items here are synthetic fixtures constructed in-memory -- no real bank rows, no real audio,
no TTS/model download required.
"""

from __future__ import annotations

import copy
import uuid
from types import SimpleNamespace

import pytest
import pytest_asyncio
from fastapi import BackgroundTasks, HTTPException
from pydantic import ValidationError
from sqlalchemy import delete, select

from app.api import language_exam
from app.models.language.catalog import Language
from app.models.language.exam import LanguageExamSession
from app.models.user import User, UserRole
from app.schemas.language_exam import McqAnswerIn
from app.services.language_gap_fill_service import (
    gap_fill_content_error,
    normalize_gap_fill_text,
    score_gap_fill_answer,
)

# ------------------------------------------------------------------------------------------
# Pure unit tests: normalize_gap_fill_text
# ------------------------------------------------------------------------------------------


def test_normalize_lowercases_by_default():
    assert normalize_gap_fill_text("LONDON") == "london"


def test_normalize_case_sensitive_preserves_case():
    assert normalize_gap_fill_text("London", case_sensitive=True) == "London"


def test_normalize_strips_leading_and_trailing_whitespace():
    assert normalize_gap_fill_text("   ten   ") == "ten"


def test_normalize_collapses_repeated_internal_whitespace():
    assert normalize_gap_fill_text("three   pm") == "three pm"


def test_normalize_removes_trailing_punctuation():
    assert normalize_gap_fill_text("ten.") == "ten"
    assert normalize_gap_fill_text("ten!") == "ten"
    assert normalize_gap_fill_text("ten?") == "ten"
    assert normalize_gap_fill_text("ten,") == "ten"


def test_normalize_curly_and_straight_apostrophes_match():
    assert normalize_gap_fill_text("don’t") == normalize_gap_fill_text("don't")
    assert normalize_gap_fill_text("don’t") == "don't"


def test_normalize_preserves_internal_punctuation_like_colons_and_hyphens():
    assert normalize_gap_fill_text("3:00") == "3:00"
    assert normalize_gap_fill_text("well-known") == "well-known"


# ------------------------------------------------------------------------------------------
# Pure unit tests: gap_fill_content_error (malformed content detection)
# ------------------------------------------------------------------------------------------


def _valid_item(**overrides) -> dict:
    item = {
        "question_type": "gap_fill",
        "question": "What time does the train leave? ___",
        "accepted_answers": ["3pm", "3 pm"],
        "max_words": 2,
        "case_sensitive": False,
    }
    item.update(overrides)
    return item


def test_content_error_none_for_well_formed_item():
    assert gap_fill_content_error(_valid_item()) is None


def test_content_error_missing_accepted_answers():
    item = _valid_item()
    del item["accepted_answers"]
    assert gap_fill_content_error(item) == "accepted_answers"


def test_content_error_non_list_accepted_answers():
    assert gap_fill_content_error(_valid_item(accepted_answers="3pm")) == "accepted_answers"


def test_content_error_empty_accepted_answers():
    assert gap_fill_content_error(_valid_item(accepted_answers=[])) == "accepted_answers"


def test_content_error_non_string_accepted_answer_entries():
    assert gap_fill_content_error(_valid_item(accepted_answers=["3pm", 300])) == "accepted_answers"


def test_content_error_all_accepted_answers_normalize_to_empty():
    assert gap_fill_content_error(_valid_item(accepted_answers=["...", "!?", "  "])) == "accepted_answers"


def test_content_error_missing_max_words():
    item = _valid_item()
    del item["max_words"]
    assert gap_fill_content_error(item) == "max_words"


def test_content_error_zero_max_words():
    assert gap_fill_content_error(_valid_item(max_words=0)) == "max_words"


def test_content_error_negative_max_words():
    assert gap_fill_content_error(_valid_item(max_words=-1)) == "max_words"


def test_content_error_non_integer_max_words():
    assert gap_fill_content_error(_valid_item(max_words="two")) == "max_words"
    assert gap_fill_content_error(_valid_item(max_words=2.5)) == "max_words"


def test_content_error_bool_max_words_rejected_despite_bool_being_an_int_subclass():
    assert gap_fill_content_error(_valid_item(max_words=True)) == "max_words"


def test_content_error_non_bool_case_sensitive_is_malformed():
    assert gap_fill_content_error(_valid_item(case_sensitive="false")) == "case_sensitive"


# ------------------------------------------------------------------------------------------
# Pure unit tests: score_gap_fill_answer (exact-match semantics, no fuzzy matching)
# ------------------------------------------------------------------------------------------


def test_score_exact_accepted_answer_is_correct():
    item = _valid_item(accepted_answers=["10", "ten"])
    assert score_gap_fill_answer(item, "ten") is True
    assert score_gap_fill_answer(item, "10") is True


def test_score_unaccepted_answer_is_incorrect():
    item = _valid_item(accepted_answers=["10", "ten"])
    assert score_gap_fill_answer(item, "eleven") is False


def test_score_numeric_variant_not_accepted_unless_authored():
    item = _valid_item(accepted_answers=["ten"])
    assert score_gap_fill_answer(item, "10") is False


def test_score_time_variant_not_accepted_unless_authored():
    item = _valid_item(accepted_answers=["3pm"])
    assert score_gap_fill_answer(item, "three o'clock") is False
    item_both = _valid_item(accepted_answers=["3pm", "three o'clock"])
    assert score_gap_fill_answer(item_both, "three o'clock") is True


def test_score_unauthored_spelling_variant_not_accepted():
    item = _valid_item(accepted_answers=["colour"])
    assert score_gap_fill_answer(item, "color") is False


def test_score_similar_misspelling_not_accepted_no_fuzzy_matching():
    item = _valid_item(accepted_answers=["library"])
    assert score_gap_fill_answer(item, "libary") is False


# ------------------------------------------------------------------------------------------
# Request-schema tests (McqAnswerIn): ambiguous/blank submissions rejected before any DB work.
# ------------------------------------------------------------------------------------------

_BASE_ANSWER_FIELDS = {
    "request_id": "gap-fill-request-0000001",
    "state_revision": 1,
    "question_token": "gap-fill-question-token-0000001",
}


def test_schema_accepts_choice_index_only():
    body = McqAnswerIn(choice_index=0, **_BASE_ANSWER_FIELDS)
    assert body.choice_index == 0
    assert body.answer_text is None


def test_schema_accepts_answer_text_only():
    body = McqAnswerIn(answer_text="ten", **_BASE_ANSWER_FIELDS)
    assert body.answer_text == "ten"
    assert body.choice_index is None


def test_schema_rejects_both_fields_present():
    with pytest.raises(ValidationError):
        McqAnswerIn(choice_index=0, answer_text="ten", **_BASE_ANSWER_FIELDS)


def test_schema_rejects_neither_field_present():
    with pytest.raises(ValidationError):
        McqAnswerIn(**_BASE_ANSWER_FIELDS)


def test_schema_rejects_blank_answer_text():
    with pytest.raises(ValidationError):
        McqAnswerIn(answer_text="   ", **_BASE_ANSWER_FIELDS)


def test_schema_does_not_require_or_accept_question_type():
    assert "question_type" not in McqAnswerIn.model_fields


# ------------------------------------------------------------------------------------------
# Postgres-integration tests: the real answer_mcq endpoint. Only these need the marker (see
# conftest.py's pytest_collection_modifyitems) -- the pure unit tests above run anywhere.
# ------------------------------------------------------------------------------------------

pytestmark = pytest.mark.postgresql


@pytest_asyncio.fixture
async def gap_fill_exam_record(postgres_session_factory):
    """Minimal isolated student/language/exam-session row, cleaned up after the test -- mirrors
    exam_record_factory in test_language_exam_postgresql_concurrency.py but kept local to this
    file so this feature's tests are self-contained."""

    created: list[tuple[str, int, int]] = []

    async def create(*, state: dict, status: str = "in_progress") -> SimpleNamespace:
        marker = uuid.uuid4().hex
        async with postgres_session_factory() as db:
            student = User(
                email=f"gap-fill-{marker}@example.test",
                name="Gap Fill Test Student",
                hashed_password="not-used",
                role=UserRole.student,
            )
            language = Language(
                code=f"gf{marker[:10]}", name_en="English", name_ar="English", is_active=True
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


def _mcq_state(*, revision: int = 5) -> dict:
    return {
        "version": 3,
        "state_revision": revision,
        "sections": ["listening"],
        "cursor": 0,
        "listening": {
            "pool": {
                "A2": {
                    "level": "A2",
                    "question": "Which answer is correct?",
                    "options": ["correct", "wrong"],
                    "correct_index": 0,
                    "question_token": "mcq-question-token-0000000001",
                },
                "B1": {
                    "level": "B1",
                    "question": "This must remain unanswered.",
                    "options": ["next correct", "next wrong"],
                    "correct_index": 0,
                    "question_token": "mcq-question-token-0000000002",
                },
            },
            "current_level": "A2",
            "asked": [],
            "max_steps": 2,
            "ready": True,
            "done": False,
            "evidence_status": "missing_student_response",
        },
        "request_receipts": [],
    }


def _gap_fill_state(
    *, revision: int = 5, accepted_answers=None, max_words: int = 2, case_sensitive: bool = False,
    question_type: str = "gap_fill",
) -> dict:
    item: dict = {
        "level": "A2",
        "question": "What time does the train leave? ___",
        "question_type": question_type,
        # _build_state_out requires a usable audio_url for the listening section regardless of
        # question_type (unrelated to this feature) -- included so state-serialization tests
        # reach the mcq branch instead of the (correct, unrelated) content_unavailable short-circuit.
        "audio_url": "/uploads/language_exam_audio/gap-fill-test-clip.wav",
        "question_token": "gap-fill-question-token-0000001",
    }
    if accepted_answers is not None:
        item["accepted_answers"] = accepted_answers
    if question_type == "gap_fill":
        item.setdefault("accepted_answers", ["3pm", "3 pm"])
    item["max_words"] = max_words
    item["case_sensitive"] = case_sensitive
    return {
        "version": 3,
        "state_revision": revision,
        "sections": ["listening"],
        "cursor": 0,
        "listening": {
            "pool": {"A2": item, "B1": dict(item, level="B1")},
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


# 1-2. Existing MCQ submission (correct / incorrect) still scores correctly.
async def test_mcq_correct_choice_index_still_scores_correctly(
    monkeypatch, postgres_session_factory, gap_fill_exam_record
):
    monkeypatch.setattr(language_exam, "check_or_raise", lambda *_a, **_k: None)
    state = _mcq_state()
    record = await gap_fill_exam_record(state=state)
    body = McqAnswerIn(
        choice_index=0,
        request_id="mcq-req-0000001",
        state_revision=state["state_revision"],
        question_token=state["listening"]["pool"]["A2"]["question_token"],
    )
    await _submit(postgres_session_factory, record, body)
    stored = await _stored(postgres_session_factory, record.session_id)
    assert stored.exam_state["listening"]["asked"][0]["correct"] is True


async def test_mcq_incorrect_choice_index_still_scores_incorrectly(
    monkeypatch, postgres_session_factory, gap_fill_exam_record
):
    monkeypatch.setattr(language_exam, "check_or_raise", lambda *_a, **_k: None)
    state = _mcq_state()
    record = await gap_fill_exam_record(state=state)
    body = McqAnswerIn(
        choice_index=1,
        request_id="mcq-req-0000002",
        state_revision=state["state_revision"],
        question_token=state["listening"]["pool"]["A2"]["question_token"],
    )
    await _submit(postgres_session_factory, record, body)
    stored = await _stored(postgres_session_factory, record.session_id)
    assert stored.exam_state["listening"]["asked"][0]["correct"] is False


# 3. MCQ submission with answer_text is rejected without state mutation.
async def test_mcq_submission_with_answer_text_is_rejected_without_mutation(
    monkeypatch, postgres_session_factory, gap_fill_exam_record
):
    monkeypatch.setattr(language_exam, "check_or_raise", lambda *_a, **_k: None)
    state = _mcq_state()
    record = await gap_fill_exam_record(state=state)
    body = McqAnswerIn(
        answer_text="correct",
        request_id="mcq-req-0000003",
        state_revision=state["state_revision"],
        question_token=state["listening"]["pool"]["A2"]["question_token"],
    )
    with pytest.raises(HTTPException) as exc_info:
        await _submit(postgres_session_factory, record, body)
    assert exc_info.value.status_code == 400
    stored = await _stored(postgres_session_factory, record.session_id)
    assert stored.exam_state["listening"]["asked"] == []


# 4. MCQ submission without choice_index (schema-level -- covered above by
# test_schema_rejects_neither_field_present) -- confirm it also cannot reach the endpoint at all.
async def test_mcq_submission_without_choice_index_is_rejected_at_schema_level():
    with pytest.raises(ValidationError):
        McqAnswerIn(request_id="mcq-req-0000004", state_revision=1, question_token="x" * 20)


# 5. Gap Fill exact accepted answer scores correctly.
async def test_gap_fill_exact_accepted_answer_scores_correctly(
    monkeypatch, postgres_session_factory, gap_fill_exam_record
):
    monkeypatch.setattr(language_exam, "check_or_raise", lambda *_a, **_k: None)
    state = _gap_fill_state()
    record = await gap_fill_exam_record(state=state)
    body = McqAnswerIn(
        answer_text="3pm",
        request_id="gf-req-0000001",
        state_revision=state["state_revision"],
        question_token=state["listening"]["pool"]["A2"]["question_token"],
    )
    await _submit(postgres_session_factory, record, body)
    stored = await _stored(postgres_session_factory, record.session_id)
    entry = stored.exam_state["listening"]["asked"][0]
    assert entry["correct"] is True


# 6. Gap Fill unaccepted answer scores incorrectly.
async def test_gap_fill_unaccepted_answer_scores_incorrectly(
    monkeypatch, postgres_session_factory, gap_fill_exam_record
):
    monkeypatch.setattr(language_exam, "check_or_raise", lambda *_a, **_k: None)
    state = _gap_fill_state()
    record = await gap_fill_exam_record(state=state)
    body = McqAnswerIn(
        answer_text="midnight",
        request_id="gf-req-0000002",
        state_revision=state["state_revision"],
        question_token=state["listening"]["pool"]["A2"]["question_token"],
    )
    await _submit(postgres_session_factory, record, body)
    stored = await _stored(postgres_session_factory, record.session_id)
    assert stored.exam_state["listening"]["asked"][0]["correct"] is False


# 7. Case-insensitive matching when case_sensitive=false.
async def test_gap_fill_case_insensitive_matching(
    monkeypatch, postgres_session_factory, gap_fill_exam_record
):
    monkeypatch.setattr(language_exam, "check_or_raise", lambda *_a, **_k: None)
    state = _gap_fill_state(accepted_answers=["London"], case_sensitive=False)
    record = await gap_fill_exam_record(state=state)
    body = McqAnswerIn(
        answer_text="LONDON",
        request_id="gf-req-0000003",
        state_revision=state["state_revision"],
        question_token=state["listening"]["pool"]["A2"]["question_token"],
    )
    await _submit(postgres_session_factory, record, body)
    stored = await _stored(postgres_session_factory, record.session_id)
    assert stored.exam_state["listening"]["asked"][0]["correct"] is True


# 8. case_sensitive=true is supported and behaves correctly (the current contract permits it).
async def test_gap_fill_case_sensitive_true_is_supported_and_enforced(
    monkeypatch, postgres_session_factory, gap_fill_exam_record
):
    monkeypatch.setattr(language_exam, "check_or_raise", lambda *_a, **_k: None)
    state = _gap_fill_state(accepted_answers=["London"], case_sensitive=True)
    record = await gap_fill_exam_record(state=state)
    body = McqAnswerIn(
        answer_text="london",
        request_id="gf-req-0000004",
        state_revision=state["state_revision"],
        question_token=state["listening"]["pool"]["A2"]["question_token"],
    )
    await _submit(postgres_session_factory, record, body)
    stored = await _stored(postgres_session_factory, record.session_id)
    # Wrong case under case_sensitive=true must not match.
    assert stored.exam_state["listening"]["asked"][0]["correct"] is False


# 9-12. Normalization edge cases exercised end-to-end through the real endpoint.
async def test_gap_fill_whitespace_and_punctuation_normalize_through_endpoint(
    monkeypatch, postgres_session_factory, gap_fill_exam_record
):
    monkeypatch.setattr(language_exam, "check_or_raise", lambda *_a, **_k: None)
    state = _gap_fill_state(accepted_answers=["three pm"], max_words=3)
    record = await gap_fill_exam_record(state=state)
    body = McqAnswerIn(
        answer_text="  three   pm.  ",
        request_id="gf-req-0000005",
        state_revision=state["state_revision"],
        question_token=state["listening"]["pool"]["A2"]["question_token"],
    )
    await _submit(postgres_session_factory, record, body)
    stored = await _stored(postgres_session_factory, record.session_id)
    assert stored.exam_state["listening"]["asked"][0]["correct"] is True


async def test_gap_fill_curly_apostrophe_normalizes_through_endpoint(
    monkeypatch, postgres_session_factory, gap_fill_exam_record
):
    monkeypatch.setattr(language_exam, "check_or_raise", lambda *_a, **_k: None)
    state = _gap_fill_state(accepted_answers=["don't know"], max_words=3)
    record = await gap_fill_exam_record(state=state)
    body = McqAnswerIn(
        answer_text="don’t know",
        request_id="gf-req-0000006",
        state_revision=state["state_revision"],
        question_token=state["listening"]["pool"]["A2"]["question_token"],
    )
    await _submit(postgres_session_factory, record, body)
    stored = await _stored(postgres_session_factory, record.session_id)
    assert stored.exam_state["listening"]["asked"][0]["correct"] is True


# 13. A Gap Fill submission using choice_index is rejected.
async def test_gap_fill_submission_using_choice_index_is_rejected(
    monkeypatch, postgres_session_factory, gap_fill_exam_record
):
    monkeypatch.setattr(language_exam, "check_or_raise", lambda *_a, **_k: None)
    state = _gap_fill_state()
    record = await gap_fill_exam_record(state=state)
    body = McqAnswerIn(
        choice_index=0,
        request_id="gf-req-0000007",
        state_revision=state["state_revision"],
        question_token=state["listening"]["pool"]["A2"]["question_token"],
    )
    with pytest.raises(HTTPException) as exc_info:
        await _submit(postgres_session_factory, record, body)
    assert exc_info.value.status_code == 400
    stored = await _stored(postgres_session_factory, record.session_id)
    assert stored.exam_state["listening"]["asked"] == []


# 14. A response exceeding max_words is rejected without state mutation.
async def test_gap_fill_over_max_words_rejected_without_mutation(
    monkeypatch, postgres_session_factory, gap_fill_exam_record
):
    monkeypatch.setattr(language_exam, "check_or_raise", lambda *_a, **_k: None)
    state = _gap_fill_state(accepted_answers=["three pm exactly"], max_words=2)
    record = await gap_fill_exam_record(state=state)
    body = McqAnswerIn(
        answer_text="three pm exactly now",
        request_id="gf-req-0000008",
        state_revision=state["state_revision"],
        question_token=state["listening"]["pool"]["A2"]["question_token"],
    )
    with pytest.raises(HTTPException) as exc_info:
        await _submit(postgres_session_factory, record, body)
    assert exc_info.value.status_code == 422
    stored = await _stored(postgres_session_factory, record.session_id)
    assert stored.exam_state["listening"]["asked"] == []
    assert stored.exam_state["listening"]["current_level"] == "A2"


# 15. A response equal to max_words is accepted for grading.
async def test_gap_fill_answer_equal_to_max_words_is_graded(
    monkeypatch, postgres_session_factory, gap_fill_exam_record
):
    monkeypatch.setattr(language_exam, "check_or_raise", lambda *_a, **_k: None)
    state = _gap_fill_state(accepted_answers=["three pm"], max_words=2)
    record = await gap_fill_exam_record(state=state)
    body = McqAnswerIn(
        answer_text="three pm",
        request_id="gf-req-0000009",
        state_revision=state["state_revision"],
        question_token=state["listening"]["pool"]["A2"]["question_token"],
    )
    await _submit(postgres_session_factory, record, body)
    stored = await _stored(postgres_session_factory, record.session_id)
    assert stored.exam_state["listening"]["asked"][0]["correct"] is True


# 16-21. Malformed gap_fill content fails closed without ever mutating state.
@pytest.mark.parametrize(
    "mutate",
    [
        lambda item: item.pop("accepted_answers"),
        lambda item: item.__setitem__("accepted_answers", "not-a-list"),
        lambda item: item.__setitem__("accepted_answers", []),
        lambda item: item.__setitem__("accepted_answers", ["ok", 123]),
        lambda item: item.__setitem__("accepted_answers", ["...", "  "]),
        lambda item: item.pop("max_words"),
        lambda item: item.__setitem__("max_words", 0),
        lambda item: item.__setitem__("max_words", -1),
        lambda item: item.__setitem__("max_words", "two"),
    ],
)
async def test_malformed_gap_fill_content_fails_closed_without_mutation(
    monkeypatch, postgres_session_factory, gap_fill_exam_record, mutate
):
    monkeypatch.setattr(language_exam, "check_or_raise", lambda *_a, **_k: None)
    state = _gap_fill_state()
    mutate(state["listening"]["pool"]["A2"])
    record = await gap_fill_exam_record(state=state)
    body = McqAnswerIn(
        answer_text="3pm",
        request_id="gf-req-malformed",
        state_revision=state["state_revision"],
        question_token=state["listening"]["pool"]["A2"]["question_token"],
    )
    with pytest.raises(HTTPException) as exc_info:
        await _submit(postgres_session_factory, record, body)
    assert exc_info.value.status_code == 503
    assert exc_info.value.detail["code"] == "content_unavailable"
    stored = await _stored(postgres_session_factory, record.session_id)
    assert stored.exam_state["listening"]["asked"] == []
    assert stored.exam_state["listening"]["current_level"] == "A2"


# 22. Unknown question_type fails closed.
async def test_unknown_question_type_fails_closed(
    monkeypatch, postgres_session_factory, gap_fill_exam_record
):
    monkeypatch.setattr(language_exam, "check_or_raise", lambda *_a, **_k: None)
    state = _gap_fill_state(question_type="essay_response")
    record = await gap_fill_exam_record(state=state)
    body = McqAnswerIn(
        answer_text="anything",
        request_id="gf-req-unknown-type",
        state_revision=state["state_revision"],
        question_token=state["listening"]["pool"]["A2"]["question_token"],
    )
    with pytest.raises(HTTPException) as exc_info:
        await _submit(postgres_session_factory, record, body)
    assert exc_info.value.status_code == 503
    assert exc_info.value.detail["code"] == "content_unavailable"
    stored = await _stored(postgres_session_factory, record.session_id)
    assert stored.exam_state["listening"]["asked"] == []


# 23. Missing internal question_type remains backward-compatible as MCQ.
async def test_missing_internal_question_type_defaults_to_mcq_in_submission(
    monkeypatch, postgres_session_factory, gap_fill_exam_record
):
    monkeypatch.setattr(language_exam, "check_or_raise", lambda *_a, **_k: None)
    state = _mcq_state()
    assert "question_type" not in state["listening"]["pool"]["A2"]
    record = await gap_fill_exam_record(state=state)
    body = McqAnswerIn(
        choice_index=0,
        request_id="mcq-req-legacy-0001",
        state_revision=state["state_revision"],
        question_token=state["listening"]["pool"]["A2"]["question_token"],
    )
    await _submit(postgres_session_factory, record, body)
    stored = await _stored(postgres_session_factory, record.session_id)
    assert stored.exam_state["listening"]["asked"][0]["correct"] is True


# 24. Valid Gap Fill scoring appends the adaptive fields expected by existing logic.
async def test_valid_gap_fill_scoring_appends_expected_adaptive_fields(
    monkeypatch, postgres_session_factory, gap_fill_exam_record
):
    monkeypatch.setattr(language_exam, "check_or_raise", lambda *_a, **_k: None)
    state = _gap_fill_state()
    record = await gap_fill_exam_record(state=state)
    body = McqAnswerIn(
        answer_text="3pm",
        request_id="gf-req-adaptive-fields",
        state_revision=state["state_revision"],
        question_token=state["listening"]["pool"]["A2"]["question_token"],
    )
    await _submit(postgres_session_factory, record, body)
    stored = await _stored(postgres_session_factory, record.session_id)
    entry = stored.exam_state["listening"]["asked"][0]
    assert entry["level"] == "A2"
    assert entry["correct"] is True
    assert entry["bank_item_id"] is None
    assert entry["question_type"] == "gap_fill"
    assert entry["chosen_index"] is None


# 25-26. Correct/incorrect Gap Fill drives the same adaptive next-level behavior as MCQ.
async def test_correct_gap_fill_causes_same_next_level_behavior_as_correct_mcq(
    monkeypatch, postgres_session_factory, gap_fill_exam_record
):
    monkeypatch.setattr(language_exam, "check_or_raise", lambda *_a, **_k: None)
    state = _gap_fill_state()
    record = await gap_fill_exam_record(state=state)
    body = McqAnswerIn(
        answer_text="3pm",
        request_id="gf-req-nextlevel-correct",
        state_revision=state["state_revision"],
        question_token=state["listening"]["pool"]["A2"]["question_token"],
    )
    await _submit(postgres_session_factory, record, body)
    stored = await _stored(postgres_session_factory, record.session_id)

    # Identical pool shape (levels/max_steps), an MCQ correct answer, for direct comparison.
    mcq_state = _mcq_state(revision=state["state_revision"])
    mcq_state["listening"]["max_steps"] = 1
    mcq_record = await gap_fill_exam_record(state=mcq_state)
    await _submit(
        postgres_session_factory,
        mcq_record,
        McqAnswerIn(
            choice_index=0,  # correct_index=0 in _mcq_state's A2 item
            request_id="mcq-req-nextlevel-correct",
            state_revision=mcq_state["state_revision"],
            question_token=mcq_state["listening"]["pool"]["A2"]["question_token"],
        ),
    )
    mcq_stored = await _stored(postgres_session_factory, mcq_record.session_id)

    assert (
        stored.exam_state["listening"]["current_level"]
        == mcq_stored.exam_state["listening"]["current_level"]
        == "B1"
    )
    assert stored.exam_state["listening"]["done"] == mcq_stored.exam_state["listening"]["done"]


async def test_incorrect_gap_fill_causes_same_next_level_behavior_as_incorrect_mcq(
    monkeypatch, postgres_session_factory, gap_fill_exam_record
):
    monkeypatch.setattr(language_exam, "check_or_raise", lambda *_a, **_k: None)
    state = _gap_fill_state()
    record = await gap_fill_exam_record(state=state)
    body = McqAnswerIn(
        answer_text="midnight",
        request_id="gf-req-nextlevel-incorrect",
        state_revision=state["state_revision"],
        question_token=state["listening"]["pool"]["A2"]["question_token"],
    )
    await _submit(postgres_session_factory, record, body)
    stored = await _stored(postgres_session_factory, record.session_id)

    # Identical pool shape, an MCQ incorrect answer, for direct comparison. adaptive_next_level
    # wants A1 (not in this pool); with asked_count=1 < MIN_MCQ_EVIDENCE_ITEMS the evidence floor
    # (P1.2) then continues probing at the nearest unasked pool level (B1) for both question types.
    mcq_state = _mcq_state(revision=state["state_revision"])
    mcq_state["listening"]["max_steps"] = 1
    mcq_record = await gap_fill_exam_record(state=mcq_state)
    await _submit(
        postgres_session_factory,
        mcq_record,
        McqAnswerIn(
            choice_index=1,  # incorrect (correct_index=0)
            request_id="mcq-req-nextlevel-incorrect",
            state_revision=mcq_state["state_revision"],
            question_token=mcq_state["listening"]["pool"]["A2"]["question_token"],
        ),
    )
    mcq_stored = await _stored(postgres_session_factory, mcq_record.session_id)

    assert (
        stored.exam_state["listening"]["current_level"]
        == mcq_stored.exam_state["listening"]["current_level"]
    )
    assert (
        stored.exam_state["listening"]["done"]
        == mcq_stored.exam_state["listening"]["done"]
    )


# 27. Secure question-token validation still rejects a mismatched token for a Gap Fill item.
async def test_gap_fill_mismatched_question_token_is_rejected(
    monkeypatch, postgres_session_factory, gap_fill_exam_record
):
    monkeypatch.setattr(language_exam, "check_or_raise", lambda *_a, **_k: None)
    state = _gap_fill_state()
    record = await gap_fill_exam_record(state=state)
    body = McqAnswerIn(
        answer_text="3pm",
        request_id="gf-req-bad-token",
        state_revision=state["state_revision"],
        question_token="the-wrong-token-entirely-000",
    )
    with pytest.raises(HTTPException) as exc_info:
        await _submit(postgres_session_factory, record, body)
    assert exc_info.value.status_code == 409
    assert exc_info.value.detail["code"] == "stale_exam_state"
    stored = await _stored(postgres_session_factory, record.session_id)
    assert stored.exam_state["listening"]["asked"] == []


# 28. Secure state-revision validation still rejects a stale submission for a Gap Fill item.
async def test_gap_fill_stale_state_revision_is_rejected(
    monkeypatch, postgres_session_factory, gap_fill_exam_record
):
    monkeypatch.setattr(language_exam, "check_or_raise", lambda *_a, **_k: None)
    state = _gap_fill_state()
    record = await gap_fill_exam_record(state=state)
    body = McqAnswerIn(
        answer_text="3pm",
        request_id="gf-req-stale-revision",
        state_revision=state["state_revision"] - 1,
        question_token=state["listening"]["pool"]["A2"]["question_token"],
    )
    with pytest.raises(HTTPException) as exc_info:
        await _submit(postgres_session_factory, record, body)
    assert exc_info.value.status_code == 409
    stored = await _stored(postgres_session_factory, record.session_id)
    assert stored.exam_state["listening"]["asked"] == []


# 29-30. Accepted answers/transcript/correct answer never appear in the public state response,
# even for a session whose current item is a Gap Fill item.
async def test_public_state_response_never_exposes_gap_fill_accepted_answers(
    postgres_session_factory, gap_fill_exam_record
):
    state = _gap_fill_state(accepted_answers=["3pm", "three o'clock", "the-secret-answer"])
    record = await gap_fill_exam_record(state=state)
    async with postgres_session_factory() as db:
        sess = (
            await db.execute(
                select(LanguageExamSession).where(LanguageExamSession.id == record.session_id)
            )
        ).scalar_one()
        out = await language_exam._build_state_out(db, sess)
    encoded = out.model_dump_json()
    assert "the-secret-answer" not in encoded
    assert "accepted_answers" not in encoded
    assert "max_words" not in encoded
    assert "case_sensitive" not in encoded
    assert out.mcq.question_type == "gap_fill"


# 31. word_bank is surfaced in the public state response for a Gap Fill item that has one
# (A1/A2 rows always author one) -- display-only, safe to expose (unlike accepted_answers/max_words).
async def test_public_state_response_exposes_word_bank_for_gap_fill_item(
    postgres_session_factory, gap_fill_exam_record
):
    state = _gap_fill_state()
    state["listening"]["pool"]["A2"]["word_bank"] = ["3pm", "midnight", "noon"]
    record = await gap_fill_exam_record(state=state)
    async with postgres_session_factory() as db:
        sess = (
            await db.execute(
                select(LanguageExamSession).where(LanguageExamSession.id == record.session_id)
            )
        ).scalar_one()
        out = await language_exam._build_state_out(db, sess)
    assert out.mcq.word_bank == ["3pm", "midnight", "noon"]


# 32. A Gap Fill item without a word_bank (permitted for B1+) surfaces word_bank=None, not an error.
async def test_public_state_response_word_bank_is_null_when_absent_for_gap_fill_item(
    postgres_session_factory, gap_fill_exam_record
):
    state = _gap_fill_state()
    assert "word_bank" not in state["listening"]["pool"]["A2"]
    record = await gap_fill_exam_record(state=state)
    async with postgres_session_factory() as db:
        sess = (
            await db.execute(
                select(LanguageExamSession).where(LanguageExamSession.id == record.session_id)
            )
        ).scalar_one()
        out = await language_exam._build_state_out(db, sess)
    assert out.mcq.word_bank is None


# 33. An MCQ item never surfaces a word_bank, even if the field were somehow present internally.
async def test_public_state_response_word_bank_is_null_for_mcq_item(
    postgres_session_factory, gap_fill_exam_record
):
    state = _mcq_state()
    # _build_state_out short-circuits to content_unavailable without a usable audio_url
    # (unrelated to this feature) -- set one so state-building reaches the mcq branch.
    state["listening"]["pool"]["A2"]["audio_url"] = "/uploads/language_exam_audio/mcq-test-clip.wav"
    record = await gap_fill_exam_record(state=state)
    async with postgres_session_factory() as db:
        sess = (
            await db.execute(
                select(LanguageExamSession).where(LanguageExamSession.id == record.session_id)
            )
        ).scalar_one()
        out = await language_exam._build_state_out(db, sess)
    assert out.mcq.question_type == "mcq"
    assert out.mcq.word_bank is None
