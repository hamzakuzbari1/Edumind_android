"""Tests for validating persistent Listening bank-audio cache entries before the runtime accepts
and serves them (fix(listening): validate cached bank audio files).

Most tests operate directly on _resolve_listening_audio/_materialize_listening_audio with a plain
item dict and db=None -- exactly how the live _prepare_content flow calls them (the DB session is
already closed by the time these run; see _materialize_listening_audio's own docstring/call site).
No Postgres is needed for these. Runtime TTS synthesis is always mocked -- no real Supertonic call
is required to run this suite.
"""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest

from app.api import language_exam
from app.core.config import get_settings

VALID_BYTES = b"RIFF" + b"\x00" * 600  # clears the 512-byte floor
TOO_SMALL_BYTES = b"x" * 10  # below the floor -- simulates a truncated/corrupt write


def _make_item(
    *,
    bank_item_id: int = 1,
    audio_url: str | None = None,
    storage_key: str | None = None,
    audio_text: str | None = "A short listening passage.",
    content_id: int | None = None,
) -> dict:
    audio_meta: dict = {}
    if storage_key is not None:
        audio_meta["storage_key"] = storage_key
    if audio_url is not None:
        audio_meta["public_url"] = audio_url
    if audio_text is not None:
        audio_meta["voice"] = language_exam._listening_tts_voice_for_text(audio_text)
    return {
        "bank_item_id": bank_item_id,
        "audio_url": audio_url,
        "audio_meta": audio_meta,
        "audio_text": audio_text,
        "content_id": content_id,
    }


def _write_cache_file(relative_key: str, data: bytes = VALID_BYTES) -> Path:
    path = Path(get_settings().UPLOAD_DIR) / relative_key
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


def _cache_key(marker: str, filename: str = "clip.wav") -> str:
    return f"language_placement_bank_audio/{marker}/{filename}"


# 1. A valid cached bank-audio file is returned.
async def test_valid_cached_file_is_returned():
    marker = uuid.uuid4().hex[:12]
    storage_key = _cache_key(marker)
    path = _write_cache_file(storage_key)
    try:
        url = f"/uploads/{storage_key}"
        item = _make_item(bank_item_id=1, audio_url=url, storage_key=storage_key)
        result = await language_exam._resolve_listening_audio(None, item)
        assert result == url
    finally:
        path.unlink(missing_ok=True)


# 2. Runtime synthesis is not called for a valid cached file.
async def test_runtime_synthesis_not_called_for_valid_cache(monkeypatch):
    marker = uuid.uuid4().hex[:12]
    storage_key = _cache_key(marker)
    path = _write_cache_file(storage_key)
    try:
        url = f"/uploads/{storage_key}"
        item = _make_item(bank_item_id=2, audio_url=url, storage_key=storage_key)
        calls: list = []

        async def fake_synth(text, *, voice=None):
            calls.append(text)
            return "/uploads/language_exam_audio/should_not_be_called.wav"

        monkeypatch.setattr(language_exam, "synthesize_exam_audio", fake_synth)
        resolved_url, _resolved_text, created = await language_exam._materialize_listening_audio(None, item)
        assert resolved_url == url
        assert created is False
        assert calls == []
    finally:
        path.unlink(missing_ok=True)


# 3. Missing cached file causes fallback (resolution itself returns None).
async def test_missing_cached_file_resolves_to_none():
    marker = uuid.uuid4().hex[:12]
    storage_key = _cache_key(marker)  # deliberately never written
    url = f"/uploads/{storage_key}"
    item = _make_item(bank_item_id=3, audio_url=url, storage_key=storage_key)
    result = await language_exam._resolve_listening_audio(None, item)
    assert result is None


# 4. Empty cached file causes fallback.
async def test_empty_cached_file_falls_back():
    marker = uuid.uuid4().hex[:12]
    storage_key = _cache_key(marker)
    path = _write_cache_file(storage_key, data=b"")
    try:
        url = f"/uploads/{storage_key}"
        item = _make_item(bank_item_id=4, audio_url=url, storage_key=storage_key)
        result = await language_exam._resolve_listening_audio(None, item)
        assert result is None
    finally:
        path.unlink(missing_ok=True)


# 5. Truncated/below-threshold cached file causes fallback.
async def test_truncated_cached_file_falls_back():
    marker = uuid.uuid4().hex[:12]
    storage_key = _cache_key(marker)
    path = _write_cache_file(storage_key, data=TOO_SMALL_BYTES)
    try:
        url = f"/uploads/{storage_key}"
        item = _make_item(bank_item_id=5, audio_url=url, storage_key=storage_key)
        result = await language_exam._resolve_listening_audio(None, item)
        assert result is None
    finally:
        path.unlink(missing_ok=True)


# 6. Unsafe storage_key traversal is rejected.
async def test_unsafe_storage_key_traversal_is_rejected():
    item = _make_item(
        bank_item_id=6,
        audio_url="/uploads/language_placement_bank_audio/6/clip.wav",
        storage_key="../../../../etc/passwd",
    )
    result = await language_exam._resolve_listening_audio(None, item)
    assert result is None


# 7. Unsafe cached URL traversal is rejected (no storage_key present -- derived from the URL).
async def test_unsafe_url_traversal_is_rejected():
    item = _make_item(
        bank_item_id=7,
        audio_url="/uploads/language_placement_bank_audio/../../../../etc/passwd",
    )
    result = await language_exam._resolve_listening_audio(None, item)
    assert result is None


# 8. A valid path cannot resolve outside UPLOAD_DIR (direct test of the path-safety primitive).
def test_path_traversal_and_absolute_paths_cannot_escape_upload_dir():
    upload_root = Path(get_settings().UPLOAD_DIR).resolve()
    assert language_exam._safe_upload_relative_path(None) is None
    assert language_exam._safe_upload_relative_path("") is None
    assert language_exam._safe_upload_relative_path("../../etc/passwd") is None
    assert language_exam._safe_upload_relative_path("/etc/passwd") is None
    assert language_exam._safe_upload_relative_path("language_placement_bank_audio/../../../etc/passwd") is None
    safe = language_exam._safe_upload_relative_path("language_placement_bank_audio/1/clip.wav")
    assert safe is not None
    assert safe.is_relative_to(upload_root)


# 9. A missing cached file plus successful runtime synthesis returns the generated attempt audio.
async def test_missing_cache_with_successful_synthesis_returns_generated_audio(monkeypatch):
    marker = uuid.uuid4().hex[:12]
    storage_key = _cache_key(marker)  # never written
    url = f"/uploads/{storage_key}"
    item = _make_item(bank_item_id=9, audio_url=url, storage_key=storage_key, audio_text="Generate me fresh.")
    generated_url = "/uploads/language_exam_audio/generated-attempt.wav"

    async def fake_synth(text, *, voice=None):
        assert text == "Generate me fresh."
        assert voice == language_exam._listening_tts_voice_for_text("Generate me fresh.")
        return generated_url

    monkeypatch.setattr(language_exam, "synthesize_exam_audio", fake_synth)
    resolved_url, resolved_text, created = await language_exam._materialize_listening_audio(None, item)
    assert resolved_url == generated_url
    assert resolved_text == "Generate me fresh."
    assert created is True


async def test_dialogue_runtime_synthesis_uses_gender_aware_segments(monkeypatch):
    generated_url = "/uploads/language_exam_audio/generated-dialogue.wav"
    item = {
        "body": {
            "audio_transcript": "Sara: I am ready.\nOmar: I am ready too.",
        },
    }
    calls: dict[str, object] = {}

    async def fake_segment_synth(segments):
        calls["segments"] = segments
        return generated_url

    async def unexpected_single_synth(text, *, voice=None):
        raise AssertionError("dialogue should use segment synthesis")

    monkeypatch.setattr(language_exam, "synthesize_exam_audio_segments", fake_segment_synth)
    monkeypatch.setattr(language_exam, "synthesize_exam_audio", unexpected_single_synth)

    resolved_url, resolved_text, created = await language_exam._materialize_listening_audio(None, item)

    assert resolved_url == generated_url
    assert resolved_text == "Sara: I am ready.\nOmar: I am ready too."
    assert created is True
    assert calls["segments"] == [
        ("I am ready.", "F1"),
        ("I am ready too.", "M1"),
    ]


def test_uncued_single_speaker_placement_voice_defaults_to_male():
    assert language_exam._listening_tts_voice_for_text("Omar talks about his morning.") == "M1"


# 10. A missing cached file plus failed runtime synthesis degrades safely.
async def test_missing_cache_with_failed_synthesis_degrades_safely(monkeypatch):
    marker = uuid.uuid4().hex[:12]
    storage_key = _cache_key(marker)  # never written
    url = f"/uploads/{storage_key}"
    item = _make_item(bank_item_id=10, audio_url=url, storage_key=storage_key)

    async def failing_synth(text, *, voice=None):
        return None  # e.g. ENABLE_TTS=False, or any synthesis failure

    monkeypatch.setattr(language_exam, "synthesize_exam_audio", failing_synth)
    resolved_url, _resolved_text, created = await language_exam._materialize_listening_audio(None, item)
    assert resolved_url is None
    assert created is False


# 14. Existing valid remote/static URL behavior is unaffected by the new bank-cache validation.
async def test_remote_and_static_asset_urls_are_unaffected():
    remote_item = _make_item(bank_item_id=14, audio_url="https://cdn.example.test/clip.mp3")
    assert await language_exam._resolve_listening_audio(None, remote_item) == "https://cdn.example.test/clip.mp3"

    static_item = _make_item(
        bank_item_id=15, audio_url="/language-assets/en/placement/listening/q1.mp3"
    )
    assert (
        await language_exam._resolve_listening_audio(None, static_item)
        == "/language-assets/en/placement/listening/q1.mp3"
    )


# 11 & 12. The state API still never exposes the transcript or the correct answer, even in the
# new "cache was rejected, live synthesis provided a fresh URL" scenario.
@pytest.mark.postgresql
@pytest.mark.integration
async def test_state_api_still_hides_transcript_and_answer_after_a_cache_rejection_fallback(
    postgres_session_factory, api_client, asgi_app
):
    from types import SimpleNamespace

    from app.db.session import get_db
    from app.models.language.catalog import Language
    from app.models.language.exam import LanguageExamSession
    from app.models.user import User, UserRole

    marker = uuid.uuid4().hex[:12]
    transcript = "Secret transcript that must never reach the client after a cache-reject fallback."
    generated_url = "/uploads/language_exam_audio/post-fallback-generated.wav"

    async with postgres_session_factory() as db:
        language = Language(code=f"lbr-{marker}", name_en="English", name_ar="English", is_active=True)
        db.add(language)
        await db.flush()
        user = User(
            email=f"listening-resolve-{marker}@example.test",
            name="Resolution Test Student",
            hashed_password="not-used",
            role=UserRole.student,
        )
        db.add(user)
        await db.flush()
        state = {
            "version": 3,
            "state_revision": 1,
            "sections": ["listening"],
            "cursor": 0,
            "listening": {
                "ready": True,
                "pool": {
                    "A2": {
                        "level": "A2",
                        "question": "What is this text mainly about?",
                        "options": ["Daily life", "Space travel", "Ancient history", "Cooking"],
                        "correct_index": 0,
                        "audio_text": transcript,
                        # Simulates: the cache entry was rejected (missing/invalid file), and
                        # live synthesis produced this fresh URL instead -- exactly what
                        # _materialize_listening_audio would have written into this same pool
                        # item during _prepare_content.
                        "audio_url": generated_url,
                        "bank_item_id": 999001,
                        "question_token": "listening-resolution-test-token-0001",
                    }
                },
                "current_level": "A2",
                "asked": [],
                "max_steps": 1,
                "done": False,
            },
        }
        session = LanguageExamSession(student_id=user.id, language_id=language.id, exam_state=state, status="in_progress")
        db.add(session)
        await db.commit()
        student_id, session_id = user.id, session.id

    async def student_override():
        return SimpleNamespace(id=student_id, role=UserRole.student)

    async def db_override():
        async with postgres_session_factory() as db:
            yield db

    dependency_calls: set = set()
    for route in asgi_app.routes:
        if not getattr(route, "path", "").startswith("/api/student/languages/exam/"):
            continue
        for dep in getattr(route, "dependant", SimpleNamespace(dependencies=[])).dependencies:
            if dep.name == "student":
                dependency_calls.add(dep.call)
    for call in dependency_calls:
        asgi_app.dependency_overrides[call] = student_override
    asgi_app.dependency_overrides[get_db] = db_override
    try:
        response = await api_client.get(f"/api/student/languages/exam/{session_id}/state")
    finally:
        for call in dependency_calls:
            asgi_app.dependency_overrides.pop(call, None)
        asgi_app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 200
    body = response.json()
    assert body["mcq"]["audio_url"] == generated_url
    body_text = response.text
    assert transcript not in body_text
    assert "correct_index" not in body_text
