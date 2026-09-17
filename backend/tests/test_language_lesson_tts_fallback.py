import pytest

from app.services import language_tts_service


class _FakeResponse:
    status_code = 200
    content = b"mp3-bytes"

    def raise_for_status(self) -> None:
        return None


class _FakeAsyncClient:
    last_requests = []

    def __init__(self, *args, **kwargs):
        self.requests = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None

    async def post(self, url, *, headers, json):
        self.requests.append((url, headers, json))
        self.__class__.last_requests.append((url, headers, json))
        return _FakeResponse()


@pytest.mark.asyncio
async def test_openai_lesson_tts_fallback_returns_audio_without_network(monkeypatch):
    _FakeAsyncClient.last_requests = []
    monkeypatch.setattr(language_tts_service.settings, "ENABLE_TTS", True)
    monkeypatch.setattr(language_tts_service.settings, "OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(language_tts_service.httpx, "AsyncClient", _FakeAsyncClient)

    result = await language_tts_service._synthesize_openai_bytes("I am ready.")

    assert result == (b"mp3-bytes", "mp3")
    assert _FakeAsyncClient.last_requests[0][2]["voice"] == "nova"


@pytest.mark.asyncio
async def test_openai_lesson_tts_fallback_requires_api_key(monkeypatch):
    monkeypatch.setattr(language_tts_service.settings, "ENABLE_TTS", True)
    monkeypatch.setattr(language_tts_service.settings, "OPENAI_API_KEY", "")

    result = await language_tts_service._synthesize_openai_bytes("I am ready.")

    assert result is None
