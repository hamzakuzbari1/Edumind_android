"""Backend coverage for Speaking's live transcript preview (Task K).

This feature is strictly UX -- a short-lived OpenAI Realtime ephemeral client secret, minted by
our own backend, that lets the frontend show a "Live transcript preview" while the student is
recording. It must never expose the server's real OPENAI_API_KEY, must require the same
authenticated-student access as the rest of the exam API, must fail safely (never raise) whenever
disabled/misconfigured/upstream fails, and must be completely invisible to every scoring/grading
code path -- the official transcript remains whatever the existing post-submit STT pipeline
returns after Submit.
"""

from __future__ import annotations

import inspect
import uuid
from types import SimpleNamespace

import httpx
import pytest

from app.api import language_exam
from app.db.session import get_db
from app.models.language.catalog import Language
from app.models.language.exam import LanguageExamSession
from app.models.user import User, UserRole
from app.services import language_exam_service, language_live_transcription_service


async def _seed_session(postgres_session_factory, *, status: str = "in_progress"):
    marker = uuid.uuid4().hex[:12]
    async with postgres_session_factory() as db:
        user = User(
            email=f"live-caption-{marker}@example.test",
            name="Live Caption Student",
            hashed_password="not-used",
            role=UserRole.student,
        )
        language = Language(code=f"lc-{marker}", name_en="English", name_ar="English")
        db.add_all([user, language])
        await db.flush()
        session = LanguageExamSession(
            student_id=user.id,
            language_id=language.id,
            exam_state={"version": 3, "state_revision": 1, "sections": ["speaking"], "cursor": 0},
            status=status,
        )
        db.add(session)
        await db.commit()
        return user.id, session.id


def _install_db_override(asgi_app, postgres_session_factory):
    async def db_override():
        async with postgres_session_factory() as db:
            yield db

    asgi_app.dependency_overrides[get_db] = db_override


def _install_student_override(asgi_app, *, student_id: int) -> set[object]:
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

    for call in dependency_calls:
        asgi_app.dependency_overrides[call] = student_override
    return dependency_calls


def _clear_overrides(asgi_app, dependency_calls: set[object] = frozenset()):
    for call in dependency_calls:
        asgi_app.dependency_overrides.pop(call, None)
    asgi_app.dependency_overrides.pop(get_db, None)


def _fake_settings(**overrides):
    base = dict(
        SPEAKING_LIVE_TRANSCRIPTION_ENABLED=True,
        SPEAKING_LIVE_TRANSCRIPTION_PROVIDER="openai_realtime",
        SPEAKING_LIVE_TRANSCRIPTION_MODEL="gpt-realtime-whisper",
        SPEAKING_LIVE_TRANSCRIPTION_TOKEN_TTL_SECONDS=60,
        OPENAI_API_KEY="sk-configured-but-unused-in-this-scenario",
    )
    base.update(overrides)
    return SimpleNamespace(**base)


class _FakeHttpxResponse:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload


def _fake_httpx_namespace(*, post_impl):
    """A stand-in for the ``httpx`` name as seen from inside
    language_live_transcription_service only. Patching real httpx.AsyncClient at the class level
    would also hijack the test's own ASGI api_client (same class, same bound method) -- rebinding
    the module-level name instead keeps the fake scoped to this one service's outbound call."""

    class _FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc_info):
            return False

        async def post(self, url, *, headers=None, json=None, **kwargs):
            return await post_impl(url, headers=headers, json=json)

    return SimpleNamespace(AsyncClient=_FakeAsyncClient, Timeout=httpx.Timeout)


async def test_create_live_transcription_session_requests_english_language_hint(monkeypatch):
    """The English placement exam's live preview must hint the transcription language explicitly
    -- without this, OpenAI sometimes guesses the script of a spoken name (e.g. transcribing a
    student's Arabic name in Arabic script) instead of transliterating it, which looks broken in
    an English-only exam. This is a pure unit test of the service's own payload construction, no
    DB/ASGI needed."""
    monkeypatch.setattr(
        language_live_transcription_service, "get_settings", lambda: _fake_settings()
    )

    captured_payloads = []

    async def fake_post(url, *, headers=None, json=None):
        captured_payloads.append(json)
        return _FakeHttpxResponse(200, {"value": "ek_fake_ephemeral_secret_xyz789", "expires_at": 1999999999})

    monkeypatch.setattr(
        language_live_transcription_service, "httpx", _fake_httpx_namespace(post_impl=fake_post)
    )

    result = await language_live_transcription_service.create_live_transcription_session()

    assert result is not None
    assert len(captured_payloads) == 1
    transcription = captured_payloads[0]["session"]["audio"]["input"]["transcription"]
    assert transcription["language"] == "en"
    assert transcription["model"] == "gpt-realtime-whisper"


@pytest.mark.integration
@pytest.mark.postgresql
async def test_live_transcription_session_endpoint_never_returns_the_real_api_key(
    api_client, asgi_app, postgres_session_factory, monkeypatch
):
    """Backend test 1/5: the server's real OPENAI_API_KEY must be used for the server-to-OpenAI
    request (that part is legitimate and expected) but must never come back in our own API's
    response -- only the short-lived ephemeral client_secret OpenAI mints should ever reach the
    frontend."""
    student_id, session_id = await _seed_session(postgres_session_factory)
    dependency_calls = _install_student_override(asgi_app, student_id=student_id)
    _install_db_override(asgi_app, postgres_session_factory)
    monkeypatch.setattr(language_exam, "check_or_raise", lambda *_a, **_k: None)

    real_key = "sk-REAL-SECRET-SHOULD-NEVER-LEAK-0000000000"
    monkeypatch.setattr(
        language_live_transcription_service,
        "get_settings",
        lambda: _fake_settings(OPENAI_API_KEY=real_key),
    )

    captured_auth_headers = []

    async def fake_post(url, *, headers=None, json=None):
        captured_auth_headers.append((headers or {}).get("Authorization"))
        return _FakeHttpxResponse(200, {"value": "ek_fake_ephemeral_secret_abc123", "expires_at": 1999999999})

    monkeypatch.setattr(
        language_live_transcription_service, "httpx", _fake_httpx_namespace(post_impl=fake_post)
    )

    try:
        response = await api_client.post(
            f"/api/student/languages/exam/{session_id}/speaking/live-transcription-session"
        )
    finally:
        _clear_overrides(asgi_app, dependency_calls)

    assert response.status_code == 200
    body = response.json()
    assert body["available"] is True
    assert body["client_secret"] == "ek_fake_ephemeral_secret_abc123"
    # The real key was legitimately used for the server-side call to OpenAI...
    assert captured_auth_headers == [f"Bearer {real_key}"]
    # ...but must never appear anywhere in what comes back to our own frontend.
    assert real_key not in response.text
    assert body["client_secret"] != real_key


@pytest.mark.integration
@pytest.mark.postgresql
async def test_live_transcription_session_endpoint_requires_authentication(
    api_client, asgi_app, postgres_session_factory
):
    """Backend test 2/5: with no Authorization header, the request must be rejected (401) before
    ever touching session lookup or minting a token -- proving this new route is wired to the
    same authenticated-student dependency as the rest of the exam API, not accidentally left
    open."""
    _install_db_override(asgi_app, postgres_session_factory)
    try:
        response = await api_client.post(
            "/api/student/languages/exam/not-a-real-session/speaking/live-transcription-session"
        )
    finally:
        _clear_overrides(asgi_app)

    assert response.status_code == 401


@pytest.mark.integration
@pytest.mark.postgresql
@pytest.mark.parametrize(
    "scenario",
    ["disabled_by_default", "enabled_but_missing_api_key", "enabled_but_upstream_call_fails"],
)
async def test_live_transcription_session_endpoint_fails_safe_never_raises(
    scenario, api_client, asgi_app, postgres_session_factory, monkeypatch
):
    """Backend test 3/5: whatever the reason -- feature disabled (the MVP default), misconfigured
    (no API key), or an upstream OpenAI failure -- the endpoint must degrade to a plain
    available=False response and must never surface a 500 or propagate an exception. The Speaking
    flow treats every one of these identically: silently skip the live preview and carry on."""
    student_id, session_id = await _seed_session(postgres_session_factory)
    dependency_calls = _install_student_override(asgi_app, student_id=student_id)
    _install_db_override(asgi_app, postgres_session_factory)
    monkeypatch.setattr(language_exam, "check_or_raise", lambda *_a, **_k: None)

    if scenario == "disabled_by_default":
        pass  # Real, unmodified settings -- SPEAKING_LIVE_TRANSCRIPTION_ENABLED defaults to False.
    elif scenario == "enabled_but_missing_api_key":
        monkeypatch.setattr(
            language_live_transcription_service,
            "get_settings",
            lambda: _fake_settings(OPENAI_API_KEY=""),
        )
    else:
        monkeypatch.setattr(
            language_live_transcription_service, "get_settings", lambda: _fake_settings()
        )

        async def failing_post(url, *, headers=None, json=None):
            raise httpx.ConnectTimeout("simulated upstream outage")

        monkeypatch.setattr(
            language_live_transcription_service, "httpx", _fake_httpx_namespace(post_impl=failing_post)
        )

    try:
        response = await api_client.post(
            f"/api/student/languages/exam/{session_id}/speaking/live-transcription-session"
        )
    finally:
        _clear_overrides(asgi_app, dependency_calls)

    assert response.status_code == 200
    body = response.json()
    assert body["available"] is False
    assert body.get("client_secret") is None


def test_no_speaking_scoring_path_reads_or_imports_live_transcription_anything():
    """Backend test 4/5: the real grading/report path -- the per-turn submit handler, the final
    evaluation orchestrator, grade_speaking itself, the verified-evidence allow-list, and the
    additive Speaking Assessment Core builder -- must never reference the live transcript
    preview's concepts. The live caption is display-only; nothing that decides a score may even
    know it exists."""
    from app.services.language_speaking_assessment_core_service import build_speaking_assessment_core

    forbidden = ("live_transcription", "client_secret", "realtime", "ephemeral")
    scoring_sources = {
        "speaking_turn": inspect.getsource(language_exam.speaking_turn),
        "_run_claimed_evaluation": inspect.getsource(language_exam._run_claimed_evaluation),
        "grade_speaking": inspect.getsource(language_exam_service.ai_engine.grade_speaking),
        "build_verified_speaking_evidence": inspect.getsource(
            language_exam_service.build_verified_speaking_evidence
        ),
        "_validated_speaking_evidence": inspect.getsource(
            language_exam_service._validated_speaking_evidence
        ),
        "build_speaking_assessment_core": inspect.getsource(build_speaking_assessment_core),
    }
    for name, source in scoring_sources.items():
        lowered = source.lower()
        for term in forbidden:
            assert term not in lowered, f"{name} unexpectedly references {term!r}"
