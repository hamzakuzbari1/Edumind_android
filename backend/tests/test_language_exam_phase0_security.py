"""Regression tests for fail-closed placement scoring and evidence gates."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest
from fastapi import BackgroundTasks, HTTPException

from app.api.language_exam import (
    SECTIONS,
    _audio_hash_already_used,
    _ensure_exam_evidence_complete,
    _maybe_finalize,
    _record_request,
    _request_receipt,
    canonical_payload_hash,
    missing_exam_evidence,
)
from app.schemas.language_exam import McqPromptOut
from app.services import language_rate_limit_service as rate_limit
from app.services import language_exam_service
from app.services.language_exam_service import (
    AIEngineService,
    ExamAIError,
    build_verified_speaking_evidence,
)


def _objective() -> dict:
    return {
        "ready": True,
        "pool": {"A2": {"question": "Q", "question_token": "question-token-0001"}},
        "asked": [{"level": "A2", "correct": True, "chosen_index": 1}],
        "done": True,
        "evidence_status": "completed",
    }


def _spoken_result(number: int) -> dict:
    return {
        "question": "Tell me about your school.",
        "transcription": "My school is near my home and I enjoy studying there.",
        "audio_sha256": f"{number:064x}",
        "audio_duration_seconds": 5.0,
        "stt_engine": "server-test",
    }


def _complete_evidence_state() -> dict:
    return {
        "state_revision": 4,
        "listening": _objective(),
        "reading": _objective(),
        "grammar_vocab": _objective(),
        "writing": {
            "ready": True,
            "prompt": "Write about school.",
            "prompt_token": "writing-token-0001",
            "min_words": 40,
            "response": " ".join(f"word{i}" for i in range(40)),
            "done": True,
            "evidence_status": "completed",
        },
        "speaking": {
            "total_turns": 3,
            "results": [_spoken_result(number) for number in range(1, 4)],
            "done": True,
            "evidence_status": "completed",
        },
        # No "interview" section — this represents the current no-interview session design
        # (product decision: guided interview removed, kept only as dormant compatibility code
        # for sessions whose own persisted "sections" still lists it — see
        # test_evidence_statuses_is_sections_driven_for_speaking_and_interview in
        # test_language_exam_state_protocol.py for that compatibility path).
    }


def test_prepared_but_empty_attempt_is_student_missing_response():
    state = _complete_evidence_state()
    for section in ("listening", "reading", "grammar_vocab"):
        state[section]["asked"] = []
        state[section]["done"] = False
        state[section]["evidence_status"] = "missing_student_response"
    state["writing"]["response"] = None
    state["writing"]["done"] = False
    state["writing"]["evidence_status"] = "missing_student_response"
    state["speaking"]["results"] = []
    state["speaking"]["done"] = False
    state["speaking"]["evidence_status"] = "missing_student_response"

    with pytest.raises(HTTPException) as exc_info:
        _ensure_exam_evidence_complete(state)

    assert exc_info.value.status_code == 422
    assert exc_info.value.detail["code"] == "incomplete_exam"
    assert set(exc_info.value.detail["missing_sections"]) == {
        "listening", "reading", "grammar_vocab", "writing", "speaking"
    }


def test_complete_attempt_requires_server_graded_mcq_writing_and_bound_audio():
    state = _complete_evidence_state()
    assert missing_exam_evidence(state) == {}
    _ensure_exam_evidence_complete(state)


def test_client_transcript_without_bound_audio_hash_is_not_speaking_evidence():
    state = _complete_evidence_state()
    for result in state["speaking"]["results"]:
        result.pop("audio_sha256")
        result["transcription"] = "An excellent but client-forged C2 answer."
    state["speaking"]["evidence_status"] = "missing_student_response"
    assert "speaking" in missing_exam_evidence(state)


def test_request_receipt_is_payload_bound_and_bounded():
    state = {"state_revision": 2}
    payload_hash = canonical_payload_hash(kind="mcq_answer", payload={"choice": 1})
    _record_request(
        state,
        kind="mcq_answer",
        request_id="request-0001",
        payload_hash=payload_hash,
        request_revision=1,
        token="question-token-0001",
        result_reference="reading:A2:revision:2",
    )
    assert _request_receipt(
        state, kind="mcq_answer", request_id="request-0001", payload_hash=payload_hash
    )
    with pytest.raises(HTTPException) as exc_info:
        _request_receipt(
            state, kind="mcq_answer", request_id="request-0001", payload_hash="f" * 64
        )
    assert exc_info.value.detail["code"] == "idempotency_conflict"


def test_same_audio_hash_cannot_be_reused_for_another_spoken_question():
    state = _complete_evidence_state()
    used_hash = state["speaking"]["results"][0]["audio_sha256"]
    assert _audio_hash_already_used(state, used_hash) is True
    assert _audio_hash_already_used(state, "b" * 64) is False


def test_complete_evidence_transitions_once_to_pending_evaluation():
    state = _complete_evidence_state()
    state["sections"] = list(SECTIONS)
    state["cursor"] = len(state["sections"])
    session = SimpleNamespace(id="exam-session-1", status="in_progress")
    background_tasks = BackgroundTasks()

    assert _maybe_finalize(session, state, background_tasks) is True
    assert _maybe_finalize(session, state, background_tasks) is False
    assert session.status == "evaluating"
    assert state["evaluation"]["evaluation_status"] == "pending"
    assert len(background_tasks.tasks) == 1


def test_public_mcq_dto_drops_internal_correct_answer_and_listening_transcript():
    dto = McqPromptOut.model_validate(
        {
            "instructions": "Listen and answer.",
            "audio_url": "/uploads/language_exam_audio/clip.wav",
            "audio_text": "private transcript",
            "question": "What did the speaker choose?",
            "options": ["A", "B", "C", "D"],
            "correct_index": 3,
            "answer_key": "D",
            "item_index": 0,
            "item_total": 1,
            "question_token": "question-token-0001",
        }
    )
    payload = dto.model_dump(exclude_none=True)
    assert "correct_index" not in payload
    assert "answer_key" not in payload
    assert "audio_text" not in payload


@pytest.mark.parametrize("method_name", ["grade_writing", "grade_speaking"])
def test_unavailable_ai_grader_fails_closed_instead_of_awarding_a_level(method_name):
    engine = AIEngineService()
    engine._mock = True
    if method_name == "grade_writing":
        call = engine.grade_writing(
            prompt_text="Write about your school.",
            answer="A sufficiently long answer that must never receive a fabricated C-level score.",
            effective_level="C2",
        )
    else:
        call = engine.grade_speaking(
            evidence=build_verified_speaking_evidence([_spoken_result(1)], []),
            effective_level="C2",
        )
    with pytest.raises(ExamAIError):
        asyncio.run(call)


_WRITING_MALFORMED_JSON = {
    "missing_field": '{"task_achievement": 5.0, "coherence": 5.0, "lexical": 5.0, "grammar": 5.0, "score": 5.0}',
    "wrong_type": '{"level": "B1", "task_achievement": "high", "coherence": 5.0, "lexical": 5.0, "grammar": 5.0, "score": 5.0}',
    "out_of_range": '{"level": "B1", "task_achievement": 999.0, "coherence": 5.0, "lexical": 5.0, "grammar": 5.0, "score": 5.0}',
    "invalid_cefr": '{"level": "Z9", "task_achievement": 5.0, "coherence": 5.0, "lexical": 5.0, "grammar": 5.0, "score": 5.0}',
    "unparseable": "not json at all",
}
_SPEAKING_MALFORMED_JSON = {
    "missing_field": '{"fluency": 5.0, "lexical": 5.0, "grammar": 5.0, "pronunciation": 0.0, "score": 5.0}',
    "wrong_type": '{"level": "B1", "fluency": "high", "lexical": 5.0, "grammar": 5.0, "pronunciation": 0.0, "score": 5.0}',
    "out_of_range": '{"level": "B1", "fluency": 999.0, "lexical": 5.0, "grammar": 5.0, "pronunciation": 0.0, "score": 5.0}',
    "invalid_cefr": '{"level": "Z9", "fluency": 5.0, "lexical": 5.0, "grammar": 5.0, "pronunciation": 0.0, "score": 5.0}',
    "unparseable": "not json at all",
}


@pytest.mark.parametrize(
    "method_name,malformed_json",
    [
        (method_name, payload)
        for method_name, payloads in (
            ("grade_writing", _WRITING_MALFORMED_JSON),
            ("grade_speaking", _SPEAKING_MALFORMED_JSON),
        )
        for payload in payloads.values()
    ],
    ids=[
        f"{method_name}-{case_id}"
        for method_name, payloads in (
            ("grade_writing", _WRITING_MALFORMED_JSON),
            ("grade_speaking", _SPEAKING_MALFORMED_JSON),
        )
        for case_id in payloads
    ],
)
def test_malformed_ai_grading_json_fails_closed_instead_of_awarding_a_level(
    monkeypatch, method_name, malformed_json
):
    """Schema-invalid AI output must fail the same way "AI unavailable" already does.

    Unlike test_unavailable_ai_grader_fails_closed_instead_of_awarding_a_level (which forces
    ``_mock`` so the grader never calls the LLM at all), this forces ``_mock`` OFF so the real
    _parse_json/model_validate path actually runs against a malformed response. Each method gets
    its own schema-correct malformed payloads (WritingGradeSchema and SpeakingGradeSchema use
    different field names) — reusing one payload set for both let bad values land on fields the
    other schema doesn't have, where Pydantic silently ignores them instead of failing.
    """
    engine = AIEngineService()
    engine._mock = False

    async def fake_generate_llm_json(*_args, **_kwargs):
        return malformed_json

    monkeypatch.setattr(language_exam_service, "generate_llm_json", fake_generate_llm_json)

    if method_name == "grade_writing":
        call = engine.grade_writing(
            prompt_text="Write about your school.",
            answer="A sufficiently long answer that must never receive a fabricated score.",
            effective_level="C2",
        )
    else:
        call = engine.grade_speaking(
            evidence=build_verified_speaking_evidence([_spoken_result(1)], []),
            effective_level="C2",
        )
    with pytest.raises(ExamAIError):
        asyncio.run(call)


def test_rate_limiter_returns_remaining_retry_after(monkeypatch):
    monkeypatch.setitem(rate_limit.RATE_LIMITS, "placement_audio_turn", (2, 30.0))
    clock = iter([100.0, 101.0, 102.0, 103.0])
    monkeypatch.setattr(rate_limit.time, "time", lambda: next(clock))
    rate_limit._hits.clear()
    rate_limit.check_or_raise("placement_audio_turn", "user-1:session-a")
    rate_limit.check_or_raise("placement_audio_turn", "user-1:session-a")
    with pytest.raises(HTTPException) as exc_info:
        rate_limit.check_or_raise("placement_audio_turn", "user-1:session-a")
    assert exc_info.value.status_code == 429
    assert exc_info.value.headers["Retry-After"] == "28"
