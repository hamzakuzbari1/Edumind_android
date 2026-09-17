"""ASGI integration coverage for the modern placement state protocol."""

from __future__ import annotations

import copy
import uuid
from types import SimpleNamespace

import pytest
from sqlalchemy import select

from app.api import language_exam
from app.db.session import get_db
from app.models.language.catalog import Language
from app.models.language.exam import LanguageExamSession
from app.models.user import User, UserRole
from app.schemas.language_exam import CEFRLevel, SpeakingTurnAssessment
from app.services import language_rate_limit_service as rate_limit


@pytest.mark.integration
def test_exam_has_no_second_preview_transcription_route(asgi_app):
    registered_paths = {getattr(route, "path", "") for route in asgi_app.routes}
    assert "/api/student/languages/exam/{session_id}/speaking/transcribe" not in registered_paths


@pytest.mark.integration
async def test_oversized_audio_is_rejected_before_multipart_or_authentication(api_client):
    response = await api_client.post(
        "/api/student/languages/exam/not-a-session/speaking/turn",
        content=b"not-a-multipart-body",
        headers={"Content-Length": str(100 * 1024 * 1024)},
    )

    assert response.status_code == 413
    assert response.json()["detail"]["code"] == "audio_request_too_large"


@pytest.mark.integration
async def test_streamed_audio_without_content_length_is_cut_off_before_multipart(api_client):
    boundary = "bounded-placement-audio"

    async def oversized_stream():
        yield (
            f"--{boundary}\r\n"
            'Content-Disposition: form-data; name="file"; filename="answer.wav"\r\n'
            "Content-Type: audio/wav\r\n\r\n"
        ).encode()
        for _ in range(12):
            yield b"x" * (1024 * 1024)
        yield f"\r\n--{boundary}--\r\n".encode()

    response = await api_client.post(
        "/api/student/languages/exam/not-a-session/speaking/turn",
        content=oversized_stream(),
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )

    assert response.status_code == 413
    assert response.json()["detail"]["code"] == "audio_request_too_large"


async def _seed_session(postgres_session_factory, state: dict, *, status: str = "in_progress"):
    marker = uuid.uuid4().hex[:12]
    async with postgres_session_factory() as db:
        user = User(
            email=f"placement-{marker}@example.test",
            name="Placement Student",
            hashed_password="not-used",
            role=UserRole.student,
        )
        language = Language(code=f"en-{marker}", name_en="English", name_ar="English")
        db.add_all([user, language])
        await db.flush()
        session = LanguageExamSession(
            student_id=user.id,
            language_id=language.id,
            exam_state=state,
            status=status,
        )
        db.add(session)
        await db.commit()
        return user.id, language.id, session.id


def _install_exam_overrides(asgi_app, postgres_session_factory, *, student_id: int):
    path_prefix = "/api/student/languages/exam/"
    dependency_calls: set[object] = set()
    for route in asgi_app.routes:
        if not getattr(route, "path", "").startswith(path_prefix):
            continue
        for dependency in getattr(route, "dependant", SimpleNamespace(dependencies=[])).dependencies:
            if dependency.name == "student":
                dependency_calls.add(dependency.call)

    async def student_override():
        return SimpleNamespace(id=student_id, role=UserRole.student)

    async def db_override():
        async with postgres_session_factory() as db:
            yield db

    for call in dependency_calls:
        asgi_app.dependency_overrides[call] = student_override
    asgi_app.dependency_overrides[get_db] = db_override
    return dependency_calls


def _clear_exam_overrides(asgi_app, dependency_calls):
    for call in dependency_calls:
        asgi_app.dependency_overrides.pop(call, None)
    asgi_app.dependency_overrides.pop(get_db, None)


def _writing_state() -> dict:
    return {
        "version": 3,
        "state_revision": 1,
        "sections": ["writing"],
        "cursor": 0,
        "writing": {
            "ready": True,
            "prompt": "Write at least forty words about school.",
            "prompt_token": "writing-prompt-token-0001",
            "min_words": 40,
            "response": None,
            "done": False,
            "evidence_status": "missing_student_response",
        },
        "reading": {"ready": True, "pool": {"A2": {}}, "asked": [], "done": False},
        "listening": {"ready": True, "pool": {"A2": {}}, "asked": [], "done": False},
        "grammar_vocab": {"ready": True, "pool": {"A2": {}}, "asked": [], "done": False},
        "speaking": {"total_turns": 1, "results": [], "done": False},
    }


@pytest.mark.integration
@pytest.mark.postgresql
async def test_empty_exam_cannot_finalize_through_actual_writing_endpoint(
    api_client, asgi_app, postgres_session_factory
):
    student_id, _language_id, session_id = await _seed_session(
        postgres_session_factory, _writing_state()
    )
    dependencies = _install_exam_overrides(
        asgi_app, postgres_session_factory, student_id=student_id
    )
    try:
        response = await api_client.post(
            f"/api/student/languages/exam/{session_id}/writing",
            json={
                "text": " ".join(f"word{i}" for i in range(40)),
                "request_id": "empty-finalize-0001",
                "state_revision": 1,
                "prompt_token": "writing-prompt-token-0001",
            },
        )
    finally:
        _clear_exam_overrides(asgi_app, dependencies)

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "incomplete_exam"
    async with postgres_session_factory() as db:
        session = await db.get(LanguageExamSession, session_id)
        assert session.status == "in_progress"
        assert session.exam_state["writing"]["response"] is None


def _mcq_state() -> dict:
    return {
        "version": 3,
        "state_revision": 1,
        "sections": ["reading", "writing"],
        "cursor": 0,
        "reading": {
            "ready": True,
            "pool": {
                "A2": {
                    "level": "A2",
                    "question": "Choose A.",
                    "options": ["A", "B"],
                    "correct_index": 0,
                    "question_token": "reading-question-token-0001",
                }
            },
            "current_level": "A2",
            "asked": [],
            "max_steps": 1,
            "done": False,
            "evidence_status": "missing_student_response",
        },
        "writing": {
            "ready": True,
            "prompt": "Write.",
            "prompt_token": "writing-prompt-token-0002",
            "min_words": 40,
            "response": None,
            "done": False,
        },
    }


@pytest.mark.integration
@pytest.mark.postgresql
async def test_stale_mcq_and_idempotency_conflict_are_enforced_by_api(
    api_client, asgi_app, postgres_session_factory
):
    student_id, _language_id, session_id = await _seed_session(
        postgres_session_factory, _mcq_state()
    )
    dependencies = _install_exam_overrides(
        asgi_app, postgres_session_factory, student_id=student_id
    )
    body = {
        "choice_index": 0,
        "request_id": "mcq-request-0001",
        "state_revision": 1,
        "question_token": "reading-question-token-0001",
    }
    try:
        first = await api_client.post(
            f"/api/student/languages/exam/{session_id}/answer", json=body
        )
        duplicate = await api_client.post(
            f"/api/student/languages/exam/{session_id}/answer", json=body
        )
        conflict = await api_client.post(
            f"/api/student/languages/exam/{session_id}/answer",
            json={**body, "choice_index": 1},
        )
        stale = await api_client.post(
            f"/api/student/languages/exam/{session_id}/answer",
            json={**body, "request_id": "mcq-request-0002"},
        )
    finally:
        _clear_exam_overrides(asgi_app, dependencies)

    assert first.status_code == 200
    assert duplicate.status_code == 200
    assert conflict.status_code == 409
    assert conflict.json()["detail"]["code"] == "idempotency_conflict"
    assert stale.status_code == 409
    assert stale.json()["detail"]["code"] == "stale_exam_state"


@pytest.mark.integration
@pytest.mark.postgresql
async def test_state_api_never_returns_correct_answer_or_listening_transcript(
    api_client, asgi_app, postgres_session_factory
):
    state = {
        "version": 3,
        "state_revision": 3,
        "sections": ["listening"],
        "cursor": 0,
        "listening": {
            "ready": True,
            "pool": {
                "A2": {
                    "level": "A2",
                    "question": "What was selected?",
                    "options": ["A", "B"],
                    "correct_index": 1,
                    "audio_text": "The private listening transcript.",
                    "audio_url": "/uploads/language_exam_audio/test.wav",
                    "question_token": "listening-question-token-0001",
                }
            },
            "current_level": "A2",
            "asked": [],
            "max_steps": 1,
            "done": False,
        },
    }
    student_id, _language_id, session_id = await _seed_session(postgres_session_factory, state)
    dependencies = _install_exam_overrides(
        asgi_app, postgres_session_factory, student_id=student_id
    )
    try:
        response = await api_client.get(f"/api/student/languages/exam/{session_id}/state")
    finally:
        _clear_exam_overrides(asgi_app, dependencies)

    assert response.status_code == 200
    payload = response.json()
    encoded = response.text
    assert payload["mcq"]["question_token"] == "listening-question-token-0001"
    assert "correct_index" not in encoded
    assert "audio_text" not in encoded
    assert "private listening transcript" not in encoded.lower()


@pytest.mark.integration
@pytest.mark.postgresql
async def test_client_transcript_field_is_ignored_by_actual_speaking_endpoint(
    api_client, asgi_app, postgres_session_factory, monkeypatch
):
    state = {
        "version": 3,
        "state_revision": 2,
        "sections": ["speaking", "writing"],
        "cursor": 0,
        "learner_grade": 8,
        "speaking": {
            "scenario": {"scenario": "School", "setting": "Class"},
            "total_turns": 2,
            "turn": 1,
            "pending_question": "Tell me about school.",
            "turn_token": "speaking-turn-token-0001",
            "results": [],
            "done": False,
        },
        "writing": {
            "ready": True,
            "prompt": "Write.",
            "prompt_token": "writing-prompt-token-0003",
            "min_words": 40,
            "response": None,
            "done": False,
        },
    }
    student_id, _language_id, session_id = await _seed_session(postgres_session_factory, state)
    dependencies = _install_exam_overrides(
        asgi_app, postgres_session_factory, student_id=student_id
    )

    async def fake_read(_file):
        return SimpleNamespace(
            data=b"server-audio",
            suffix=".webm",
            sha256="a" * 64,
            duration_seconds=5.0,
            mime_type="audio/webm",
        )

    stt_calls = 0

    async def fake_stt(_audio):
        nonlocal stt_calls
        stt_calls += 1
        return SimpleNamespace(
            text="This is the transcript produced by the server.",
            engine="server-test",
            model="server-model",
        )

    async def fake_assessment(**_kwargs):
        return SpeakingTurnAssessment(
            transcription="LLM attempted rewrite",
            grammar_vocab_feedback="Feedback",
            pronunciation_feedback="Must not be trusted",
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
                "request_id": "speaking-request-0001",
                "state_revision": "2",
                "turn_token": "speaking-turn-token-0001",
                "transcription": "A forged client C2 transcript that must be ignored.",
            },
            files={"file": ("answer.webm", b"not-used-by-mock", "audio/webm")},
        )
    finally:
        _clear_exam_overrides(asgi_app, dependencies)

    assert response.status_code == 200
    assert stt_calls == 1
    assert response.json()["last_feedback"]["transcription"] == "This is the transcript produced by the server."
    async with postgres_session_factory() as db:
        session = await db.get(LanguageExamSession, session_id)
        result = session.exam_state["speaking"]["results"][0]
        assert result["transcription"] == "This is the transcript produced by the server."
        assert "forged" not in result["transcription"].lower()
        assert result["pronunciation_status"] == "unassessed"


async def _seed_student(postgres_session_factory) -> int:
    marker = uuid.uuid4().hex[:12]
    async with postgres_session_factory() as db:
        user = User(
            email=f"placement-other-{marker}@example.test",
            name="Other Student",
            hashed_password="not-used",
            role=UserRole.student,
        )
        db.add(user)
        await db.commit()
        return user.id


def _ownership_state() -> dict:
    return {
        "version": 3,
        "state_revision": 1,
        "sections": ["speaking", "reading", "writing"],
        "cursor": 0,
        "reading": {
            "ready": True,
            "pool": {
                "A2": {
                    "level": "A2",
                    "question": "Choose A.",
                    "options": ["A", "B"],
                    "correct_index": 0,
                    "question_token": "reading-question-token-0001",
                }
            },
            "current_level": "A2",
            "asked": [],
            "max_steps": 1,
            "done": False,
        },
        "writing": {
            "ready": True,
            "prompt": "Write.",
            "prompt_token": "writing-prompt-token-0001",
            "min_words": 40,
            "response": None,
            "done": False,
        },
        "speaking": {
            "total_turns": 1,
            "turn": 1,
            "pending_question": "Tell me about your day.",
            "turn_token": "speaking-turn-token-0001",
            "results": [],
            "done": False,
        },
    }


@pytest.mark.integration
@pytest.mark.postgresql
async def test_student_cannot_access_or_mutate_another_students_exam_session(
    api_client, asgi_app, postgres_session_factory
):
    """Student B must get 404 from every exam route when addressing student A's session_id."""
    owner_id, _language_id, session_id = await _seed_session(
        postgres_session_factory, _ownership_state()
    )
    other_student_id = await _seed_student(postgres_session_factory)
    assert other_student_id != owner_id

    dependencies = _install_exam_overrides(
        asgi_app, postgres_session_factory, student_id=other_student_id
    )
    try:
        state_resp = await api_client.get(f"/api/student/languages/exam/{session_id}/state")
        answer_resp = await api_client.post(
            f"/api/student/languages/exam/{session_id}/answer",
            json={
                "choice_index": 0,
                "request_id": "owner-check-answer-0001",
                "state_revision": 1,
                "question_token": "reading-question-token-0001",
            },
        )
        writing_resp = await api_client.post(
            f"/api/student/languages/exam/{session_id}/writing",
            json={
                "text": " ".join(f"word{i}" for i in range(40)),
                "request_id": "owner-check-writing-0001",
                "state_revision": 1,
                "prompt_token": "writing-prompt-token-0001",
            },
        )
        speaking_resp = await api_client.post(
            f"/api/student/languages/exam/{session_id}/speaking/turn",
            data={
                "request_id": "owner-check-speaking-0001",
                "state_revision": "1",
                "turn_token": "speaking-turn-token-0001",
            },
            files={"file": ("answer.webm", b"unused-ownership-fails-first", "audio/webm")},
        )
        abandon_resp = await api_client.post(f"/api/student/languages/exam/{session_id}/abandon")
        report_resp = await api_client.get(f"/api/student/languages/exam/{session_id}/report")
    finally:
        _clear_exam_overrides(asgi_app, dependencies)

    for label, response in (
        ("state", state_resp),
        ("answer", answer_resp),
        ("writing", writing_resp),
        ("speaking/turn", speaking_resp),
        ("abandon", abandon_resp),
        ("report", report_resp),
    ):
        assert response.status_code == 404, f"{label}: expected 404, got {response.status_code}: {response.text}"

    async with postgres_session_factory() as db:
        session = await db.get(LanguageExamSession, session_id)
        assert session.status == "in_progress"
        assert session.exam_state["state_revision"] == 1
        assert session.exam_state["writing"]["response"] is None
        assert session.exam_state["speaking"]["results"] == []


@pytest.mark.integration
@pytest.mark.postgresql
async def test_rate_limit_header_is_returned_by_actual_state_endpoint(
    api_client, asgi_app, postgres_session_factory, monkeypatch
):
    student_id, _language_id, session_id = await _seed_session(
        postgres_session_factory, _mcq_state()
    )
    dependencies = _install_exam_overrides(
        asgi_app, postgres_session_factory, student_id=student_id
    )
    monkeypatch.setitem(rate_limit.RATE_LIMITS, "placement_poll", (1, 60.0))
    rate_limit._hits.clear()
    try:
        first = await api_client.get(f"/api/student/languages/exam/{session_id}/state")
        second = await api_client.get(f"/api/student/languages/exam/{session_id}/state")
    finally:
        rate_limit._hits.clear()
        _clear_exam_overrides(asgi_app, dependencies)

    assert first.status_code == 200
    assert second.status_code == 429
    assert int(second.headers["Retry-After"]) >= 1
    assert second.json()["detail"]["code"] == "rate_limit_exceeded"


def _finalizing_writing_state() -> dict:
    """A no-interview session (no "interview" in its own sections) with every other section
    already complete — submitting writing here should finalize straight to evaluation, not
    attempt to transition into an interview phase."""
    done_objective = {
        "ready": True,
        "pool": {
            "A2": {
                "level": "A2",
                "question": "Choose A.",
                "options": ["A", "B"],
                "correct_index": 0,
                "question_token": "finalize-question-token-0001",
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
        "state_revision": 5,
        "sections": ["speaking", "listening", "reading", "grammar_vocab", "writing"],
        "cursor": 4,
        "listening": copy.deepcopy(done_objective),
        "reading": copy.deepcopy(done_objective),
        "grammar_vocab": copy.deepcopy(done_objective),
        "speaking": {
            "total_turns": 1,
            "results": [
                {
                    "question": "Tell me about your day.",
                    "transcription": "A complete verified answer.",
                    "audio_sha256": "a" * 64,
                }
            ],
            "done": True,
            "evidence_status": "completed",
        },
        "writing": {
            "ready": True,
            "prompt": "Write about your day.",
            "prompt_token": "writing-prompt-token-finalize-0001",
            "min_words": 40,
            "response": None,
            "done": False,
            "evidence_status": "missing_student_response",
        },
    }


@pytest.mark.integration
@pytest.mark.postgresql
async def test_submit_writing_finalizes_directly_without_transitioning_into_interview(
    api_client, asgi_app, postgres_session_factory
):
    """A no-interview session must finalize straight to evaluation when writing completes,
    not attempt to transition into an interview phase (product decision: guided interview
    removed; speaking stays mandatory and unaffected)."""
    student_id, _language_id, session_id = await _seed_session(
        postgres_session_factory, _finalizing_writing_state()
    )
    dependencies = _install_exam_overrides(
        asgi_app, postgres_session_factory, student_id=student_id
    )
    try:
        response = await api_client.post(
            f"/api/student/languages/exam/{session_id}/writing",
            json={
                "text": " ".join(f"word{i}" for i in range(40)),
                "request_id": "finalize-no-interview-0001",
                "state_revision": 5,
                "prompt_token": "writing-prompt-token-finalize-0001",
            },
        )
    finally:
        _clear_exam_overrides(asgi_app, dependencies)

    assert response.status_code == 202
    async with postgres_session_factory() as db:
        session = await db.get(LanguageExamSession, session_id)
        # _maybe_finalize triggered (not stuck "in_progress"/never-advancing on a phantom
        # interview requirement). The background evaluation itself runs for real here (AI engine
        # is not mocked in this HTTP-level test) and fails closed under this test environment's
        # default mocked-AI-unavailable config (LANGUAGE_CONVERSATION_MOCK_AI=true) — that failure
        # is expected and unrelated to interview removal; see
        # test_no_interview_exam_completes_without_live_phase_unavailable_penalty in
        # test_language_exam_postgresql_concurrency.py for the mocked-success evaluation path.
        assert session.status != "in_progress"
        assert "interview" not in session.exam_state
        assert session.exam_state["writing"]["response"] is not None
