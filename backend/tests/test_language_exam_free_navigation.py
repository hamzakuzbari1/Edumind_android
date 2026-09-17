"""ASGI integration coverage for free (non-sequential) section navigation.

Students can now jump to any section tab -- answering it is allowed regardless of the
session's internal progress cursor. These tests exercise the actual HTTP endpoints (not just
the state-protocol helpers) to prove: (1) GET /state?section=X renders the requested section,
(2) completed_sections reports every done section independent of viewing order, (3) each
answer-submission endpoint (answer_mcq/submit_writing/speaking_turn) accepts an explicit
section that differs from the cursor's section without disturbing other sections or the
cursor, (4) invalid/foreign sections are still rejected, (5) writing's already-done guard still
blocks a second submission, and (6) an MCQ section finishing the exam out of order still
finalizes it (the _maybe_finalize gap this feature required fixing).
"""

from __future__ import annotations

import copy
from types import SimpleNamespace

import pytest

from app.api import language_exam
from app.models.language.exam import LanguageExamSession
from app.schemas.language_exam import CEFRLevel, SpeakingTurnAssessment
from tests.test_language_exam_api_integration import (
    _clear_exam_overrides,
    _install_exam_overrides,
    _seed_session,
)


def _multi_section_state() -> dict:
    """Cursor sits at "reading" (not done). "listening" and "grammar_vocab" are also ready but
    untouched, and "writing" is ready but untouched -- a student could jump to any of them."""
    def mcq_section(token, *, audio_url=None):
        item = {
            "level": "A2",
            "question": "Choose A.",
            "options": ["A", "B"],
            "correct_index": 0,
            "question_token": token,
        }
        if audio_url:
            item["audio_url"] = audio_url
        return {
            "ready": True,
            "pool": {"A2": item},
            "current_level": "A2",
            "asked": [],
            "max_steps": 1,
            "done": False,
            "evidence_status": "missing_student_response",
        }
    return {
        "version": 3,
        "state_revision": 1,
        "sections": ["reading", "listening", "grammar_vocab", "writing"],
        "cursor": 0,
        "reading": mcq_section("reading-question-token-nav-0001"),
        "listening": mcq_section(
            "listening-question-token-nav-0001",
            audio_url="/uploads/language_exam_audio/nav-test.wav",
        ),
        "grammar_vocab": mcq_section("grammar-question-token-nav-0001"),
        "writing": {
            "ready": True,
            "prompt": "Write.",
            "prompt_token": "writing-prompt-token-nav-0001",
            "min_words": 40,
            "response": None,
            "done": False,
            "evidence_status": "missing_student_response",
        },
    }


@pytest.mark.integration
@pytest.mark.postgresql
async def test_get_state_with_section_param_returns_requested_sections_content(
    api_client, asgi_app, postgres_session_factory
):
    student_id, _language_id, session_id = await _seed_session(
        postgres_session_factory, _multi_section_state()
    )
    dependencies = _install_exam_overrides(asgi_app, postgres_session_factory, student_id=student_id)
    try:
        default_resp = await api_client.get(f"/api/student/languages/exam/{session_id}/state")
        listening_resp = await api_client.get(
            f"/api/student/languages/exam/{session_id}/state", params={"section": "listening"}
        )
        grammar_resp = await api_client.get(
            f"/api/student/languages/exam/{session_id}/state", params={"section": "grammar_vocab"}
        )
    finally:
        _clear_exam_overrides(asgi_app, dependencies)

    assert default_resp.status_code == 200
    default_payload = default_resp.json()
    assert default_payload["mcq"]["question_token"] == "reading-question-token-nav-0001"
    assert default_payload["section_index"] == 0

    assert listening_resp.status_code == 200
    listening_payload = listening_resp.json()
    assert listening_payload["mcq"]["question_token"] == "listening-question-token-nav-0001"
    assert listening_payload["section_index"] == 1

    assert grammar_resp.status_code == 200
    grammar_payload = grammar_resp.json()
    assert grammar_payload["mcq"]["question_token"] == "grammar-question-token-nav-0001"
    assert grammar_payload["section_index"] == 2


@pytest.mark.integration
@pytest.mark.postgresql
async def test_completed_sections_reflects_done_regardless_of_viewed_section(
    api_client, asgi_app, postgres_session_factory
):
    """A "done" section stops exposing its (now stale) question -- mcq is None once done, by
    design (see _build_state_out). completed_sections must still report it as done whether the
    student is viewing that section, the cursor's own (still-open) section, or a third one."""
    state = _multi_section_state()
    state["reading"]["done"] = True
    state["reading"]["evidence_status"] = "completed"
    student_id, _language_id, session_id = await _seed_session(postgres_session_factory, state)
    dependencies = _install_exam_overrides(asgi_app, postgres_session_factory, student_id=student_id)
    try:
        default_resp = await api_client.get(f"/api/student/languages/exam/{session_id}/state")
        listening_resp = await api_client.get(
            f"/api/student/languages/exam/{session_id}/state", params={"section": "listening"}
        )
    finally:
        _clear_exam_overrides(asgi_app, dependencies)

    assert default_resp.status_code == 200
    assert default_resp.json()["completed_sections"] == ["reading"]
    assert default_resp.json()["section_index"] == 0

    assert listening_resp.status_code == 200
    assert listening_resp.json()["completed_sections"] == ["reading"]
    assert listening_resp.json()["mcq"]["question_token"] == "listening-question-token-nav-0001"
    assert listening_resp.json()["section_index"] == 1


@pytest.mark.integration
@pytest.mark.postgresql
async def test_answer_mcq_accepts_explicit_section_other_than_cursor_without_disturbing_others(
    api_client, asgi_app, postgres_session_factory
):
    student_id, _language_id, session_id = await _seed_session(
        postgres_session_factory, _multi_section_state()
    )
    dependencies = _install_exam_overrides(asgi_app, postgres_session_factory, student_id=student_id)
    try:
        response = await api_client.post(
            f"/api/student/languages/exam/{session_id}/answer",
            json={
                "choice_index": 0,
                "request_id": "nav-answer-grammar-0001",
                "state_revision": 1,
                "question_token": "grammar-question-token-nav-0001",
                "section": "grammar_vocab",
            },
        )
    finally:
        _clear_exam_overrides(asgi_app, dependencies)

    assert response.status_code == 200
    async with postgres_session_factory() as db:
        session = await db.get(LanguageExamSession, session_id)
        assert session.exam_state["grammar_vocab"]["done"] is True
        assert len(session.exam_state["grammar_vocab"]["asked"]) == 1
        # Untouched: reading (the cursor's own section) and listening were not answered.
        assert session.exam_state["reading"]["done"] is False
        assert session.exam_state["reading"]["asked"] == []
        assert session.exam_state["listening"]["done"] is False
        # The cursor must not have been pulled forward past "reading", which is still not done.
        assert session.exam_state["cursor"] == 0


@pytest.mark.integration
@pytest.mark.postgresql
async def test_answer_mcq_rejects_section_not_a_member_of_this_session(
    api_client, asgi_app, postgres_session_factory
):
    student_id, _language_id, session_id = await _seed_session(
        postgres_session_factory, _multi_section_state()
    )
    dependencies = _install_exam_overrides(asgi_app, postgres_session_factory, student_id=student_id)
    try:
        response = await api_client.post(
            f"/api/student/languages/exam/{session_id}/answer",
            json={
                "choice_index": 0,
                "request_id": "nav-answer-invalid-section-0001",
                "state_revision": 1,
                "question_token": "grammar-question-token-nav-0001",
                "section": "speaking",
            },
        )
    finally:
        _clear_exam_overrides(asgi_app, dependencies)

    assert response.status_code == 409
    assert response.json()["detail"] == "Not in an MCQ section"


@pytest.mark.integration
@pytest.mark.postgresql
async def test_submit_writing_accepts_submission_while_cursor_is_elsewhere(
    api_client, asgi_app, postgres_session_factory
):
    student_id, _language_id, session_id = await _seed_session(
        postgres_session_factory, _multi_section_state()
    )
    dependencies = _install_exam_overrides(asgi_app, postgres_session_factory, student_id=student_id)
    try:
        response = await api_client.post(
            f"/api/student/languages/exam/{session_id}/writing",
            json={
                "text": " ".join(f"word{i}" for i in range(40)),
                "request_id": "nav-writing-early-0001",
                "state_revision": 1,
                "prompt_token": "writing-prompt-token-nav-0001",
            },
        )
    finally:
        _clear_exam_overrides(asgi_app, dependencies)

    assert response.status_code in (200, 202)
    async with postgres_session_factory() as db:
        session = await db.get(LanguageExamSession, session_id)
        assert session.exam_state["writing"]["done"] is True
        assert session.exam_state["writing"]["response"] is not None
        # The cursor's own section (reading) is untouched by a writing jump-ahead.
        assert session.exam_state["reading"]["done"] is False


@pytest.mark.integration
@pytest.mark.postgresql
async def test_submit_writing_rejects_second_submission_once_already_done(
    api_client, asgi_app, postgres_session_factory
):
    state = _multi_section_state()
    state["writing"]["done"] = True
    state["writing"]["response"] = "Already submitted via free navigation earlier."
    state["writing"]["evidence_status"] = "completed"
    student_id, _language_id, session_id = await _seed_session(postgres_session_factory, state)
    dependencies = _install_exam_overrides(asgi_app, postgres_session_factory, student_id=student_id)
    try:
        response = await api_client.post(
            f"/api/student/languages/exam/{session_id}/writing",
            json={
                "text": " ".join(f"overwrite{i}" for i in range(40)),
                "request_id": "nav-writing-overwrite-0001",
                "state_revision": 1,
                "prompt_token": "writing-prompt-token-nav-0001",
            },
        )
    finally:
        _clear_exam_overrides(asgi_app, dependencies)

    assert response.status_code == 409
    assert response.json()["detail"] == "Not in the writing section"
    async with postgres_session_factory() as db:
        session = await db.get(LanguageExamSession, session_id)
        assert session.exam_state["writing"]["response"] == "Already submitted via free navigation earlier."


def _speaking_and_reading_state() -> dict:
    """Cursor sits at "reading" (not done); "speaking" is untouched and reachable via free nav."""
    return {
        "version": 3,
        "state_revision": 2,
        "sections": ["reading", "speaking", "writing"],
        "cursor": 0,
        "reading": {
            "ready": True,
            "pool": {
                "A2": {
                    "level": "A2",
                    "question": "Choose A.",
                    "options": ["A", "B"],
                    "correct_index": 0,
                    "question_token": "reading-question-token-speak-nav-0001",
                }
            },
            "current_level": "A2",
            "asked": [],
            "max_steps": 1,
            "done": False,
        },
        "speaking": {
            "scenario": {"scenario": "School", "setting": "Class"},
            "total_turns": 2,
            "turn": 1,
            "pending_question": "Tell me about school.",
            "turn_token": "speaking-turn-token-nav-0001",
            "results": [],
            "done": False,
        },
        "writing": {
            "ready": True,
            "prompt": "Write.",
            "prompt_token": "writing-prompt-token-speak-nav-0001",
            "min_words": 40,
            "response": None,
            "done": False,
        },
    }


@pytest.mark.integration
@pytest.mark.postgresql
async def test_speaking_turn_accepts_explicit_section_while_cursor_is_elsewhere(
    api_client, asgi_app, postgres_session_factory, monkeypatch
):
    student_id, _language_id, session_id = await _seed_session(
        postgres_session_factory, _speaking_and_reading_state()
    )
    dependencies = _install_exam_overrides(asgi_app, postgres_session_factory, student_id=student_id)

    async def fake_read(_file):
        return SimpleNamespace(
            data=b"server-audio",
            suffix=".webm",
            sha256="b" * 64,
            duration_seconds=5.0,
            mime_type="audio/webm",
        )

    async def fake_stt(_audio):
        return SimpleNamespace(text="A real transcript.", engine="server-test", model="server-model")

    async def fake_assessment(**_kwargs):
        return SpeakingTurnAssessment(
            transcription="A real transcript.",
            grammar_vocab_feedback="Feedback",
            pronunciation_feedback="Feedback",
            fluency_note="Coherent",
            estimated_level=CEFRLevel.B1,
            next_question="What subjects do you enjoy?",
        )

    monkeypatch.setattr(language_exam, "_read_speaking_audio", fake_read)
    monkeypatch.setattr(language_exam, "_verified_server_transcription", fake_stt)
    monkeypatch.setattr(language_exam.ai_engine, "assess_speaking", fake_assessment)
    try:
        response = await api_client.post(
            f"/api/student/languages/exam/{session_id}/speaking/turn",
            data={
                "request_id": "nav-speaking-early-0001",
                "state_revision": "2",
                "turn_token": "speaking-turn-token-nav-0001",
                "section": "speaking",
            },
            files={"file": ("answer.webm", b"not-used-by-mock", "audio/webm")},
        )
    finally:
        _clear_exam_overrides(asgi_app, dependencies)

    assert response.status_code == 200
    assert response.json()["phase"] == "speaking"
    async with postgres_session_factory() as db:
        session = await db.get(LanguageExamSession, session_id)
        assert len(session.exam_state["speaking"]["results"]) == 1
        assert session.exam_state["speaking"]["results"][0]["transcription"] == "A real transcript."
        # The cursor's own section (reading) is untouched by a speaking jump-ahead.
        assert session.exam_state["reading"]["done"] is False


@pytest.mark.integration
@pytest.mark.postgresql
async def test_submit_writing_idempotent_task_transition_returns_writing_section(
    api_client, asgi_app, postgres_session_factory
):
    state = _multi_section_state()
    state["writing"].update(
        {
            "mode": "adaptive_two_task",
            "task_index": 2,
            "task_total": 2,
            "prompt": "Describe a memorable day. Write 60-90 words.",
            "prompt_token": "writing-prompt-token-nav-0002",
            "min_words": 60,
            "max_words": 90,
            "tasks": [
                {
                    "prompt": "Task 1",
                    "response": " ".join(f"first{i}" for i in range(50)),
                    "min_words": 50,
                    "max_words": 80,
                },
                {
                    "prompt": "Describe a memorable day. Write 60-90 words.",
                    "min_words": 60,
                    "max_words": 90,
                },
            ],
            "done": False,
            "evidence_status": "missing_student_response",
        }
    )
    text = " ".join(f"second{i}" for i in range(60))
    request_id = "nav-writing-idempotent-0001"
    token = "writing-prompt-token-nav-0002"
    student_id, _language_id, session_id = await _seed_session(postgres_session_factory, state)
    payload_hash = language_exam.canonical_payload_hash(
        kind="writing_answer",
        payload={
            "session_id": session_id,
            "state_revision": 1,
            "prompt_token": token,
            "text_sha256": language_exam.hashlib.sha256(
                language_exam._normalise_writing_text(text).encode("utf-8")
            ).hexdigest(),
        },
    )
    async with postgres_session_factory() as db:
        session = await db.get(LanguageExamSession, session_id)
        exam_state = copy.deepcopy(session.exam_state)
        language_exam._record_request(
            exam_state,
            kind="writing_answer",
            request_id=request_id,
            payload_hash=payload_hash,
            request_revision=1,
            token=token,
            result_reference="writing:revision:2",
        )
        session.exam_state = exam_state
        await db.commit()

    dependencies = _install_exam_overrides(asgi_app, postgres_session_factory, student_id=student_id)
    try:
        response = await api_client.post(
            f"/api/student/languages/exam/{session_id}/writing",
            json={
                "text": text,
                "request_id": request_id,
                "state_revision": 1,
                "prompt_token": token,
            },
        )
    finally:
        _clear_exam_overrides(asgi_app, dependencies)

    assert response.status_code == 200
    assert response.json()["phase"] == "writing"


def _out_of_order_mcq_finalize_state() -> dict:
    """Free navigation lets a student finish writing before the last MCQ section. Before the
    _maybe_finalize fix, answer_mcq never scheduled evaluation -- the exam could complete every
    section yet stay stuck "in_progress" forever if the very last section done happened to be an
    MCQ section rather than writing.

    Every section besides grammar_vocab already has full evidence (mirrors
    test_language_exam_api_integration._finalizing_writing_state's done_objective shape) so that
    _ensure_exam_evidence_complete passes cleanly once grammar_vocab is answered -- the cursor
    sits at grammar_vocab (index 3) because _advance_if_section_done never walks past a not-done
    section, even though "writing" (index 4, after it) was already completed out of order via
    free navigation.
    """
    done_mcq_section = {
        "ready": True,
        "pool": {
            "A2": {
                "level": "A2",
                "question": "Choose A.",
                "options": ["A", "B"],
                "correct_index": 0,
                "question_token": "finalize-done-question-token-0001",
            }
        },
        "current_level": "A2",
        "asked": [{"level": "A2", "correct": True, "chosen_index": 0}],
        "max_steps": 1,
        "done": True,
        "evidence_status": "completed",
    }
    return {
        "version": 3,
        "state_revision": 1,
        "sections": ["speaking", "listening", "reading", "grammar_vocab", "writing"],
        "cursor": 3,
        "listening": copy.deepcopy(done_mcq_section),
        "reading": copy.deepcopy(done_mcq_section),
        "grammar_vocab": {
            "ready": True,
            "pool": {
                "A2": {
                    "level": "A2",
                    "question": "Choose A.",
                    "options": ["A", "B"],
                    "correct_index": 0,
                    "question_token": "grammar-question-token-finalize-0001",
                }
            },
            "current_level": "A2",
            "asked": [],
            "max_steps": 1,
            "done": False,
            "evidence_status": "missing_student_response",
        },
        "speaking": {
            "total_turns": 1,
            "results": [
                {
                    "question": "Tell me about your day.",
                    "transcription": "A complete verified answer.",
                    "audio_sha256": "c" * 64,
                }
            ],
            "done": True,
            "evidence_status": "completed",
        },
        "writing": {
            "ready": True,
            "prompt": "Write.",
            "prompt_token": "writing-prompt-token-finalize-0001",
            "min_words": 40,
            "response": " ".join(f"word{i}" for i in range(40)),
            "done": True,
            "evidence_status": "completed",
        },
    }


@pytest.mark.integration
@pytest.mark.postgresql
async def test_out_of_order_mcq_completion_still_finalizes_the_exam(
    api_client, asgi_app, postgres_session_factory, monkeypatch
):
    # _run_evaluation itself (the actual AI grading pipeline) is irrelevant to what this test
    # proves -- that _maybe_finalize fires from answer_mcq at all -- and it opens its own DB
    # session via the module-level AsyncSessionLocal engine rather than this test's fixture-scoped
    # one, which is prone to cross-event-loop pool flakiness under pytest-asyncio's per-test event
    # loop. Stub it out so this test only exercises the synchronous part of finalization.
    async def fake_run_evaluation(_session_id):
        return None

    monkeypatch.setattr(language_exam, "_run_evaluation", fake_run_evaluation)

    student_id, _language_id, session_id = await _seed_session(
        postgres_session_factory, _out_of_order_mcq_finalize_state()
    )
    dependencies = _install_exam_overrides(asgi_app, postgres_session_factory, student_id=student_id)
    try:
        response = await api_client.post(
            f"/api/student/languages/exam/{session_id}/answer",
            json={
                "choice_index": 0,
                "request_id": "nav-finalize-via-mcq-0001",
                "state_revision": 1,
                "question_token": "grammar-question-token-finalize-0001",
            },
        )
    finally:
        _clear_exam_overrides(asgi_app, dependencies)

    assert response.status_code == 200
    assert response.json()["phase"] == "evaluating"
    async with postgres_session_factory() as db:
        session = await db.get(LanguageExamSession, session_id)
        assert session.exam_state["grammar_vocab"]["done"] is True
        # Regardless of how _run_evaluation's background task resolves in this test environment,
        # the session must have LEFT "in_progress" -- proving _maybe_finalize actually fired from
        # answer_mcq (this is the exact gap the fix closes).
        assert session.status != "in_progress"
