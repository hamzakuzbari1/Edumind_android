from pathlib import Path

import pytest

from app.models.language.enums import LanguageSkill
from app.services import language_tts_service
from app.services.language_listening_tts.renderer import listening_cache_filename
from app.services.language_listening_tts.speakers import build_synthesis_segments
from app.services.language_listening_tts.voice_config import default_voice, voice_for_gender


def test_default_language_tts_voice_is_female():
    assert default_voice() == "F1"
    assert voice_for_gender("female") == "F1"
    assert voice_for_gender("male") == "M1"


def test_listening_synthesis_segments_use_speaker_gender():
    body = {
        "audio_transcript": "Sara: I am ready.\nOmar: I am ready too.",
        "speakers": [
            {"id": "speaker_1", "name": "Sara", "gender": "female"},
            {"id": "speaker_2", "name": "Omar", "gender": "male"},
        ],
    }

    assert build_synthesis_segments(body) == [
        ("I am ready.", "F1"),
        ("I am ready too.", "M1"),
    ]


def test_listening_synthesis_segments_infer_common_speaker_name_gender():
    body = {
        "audio_transcript": "Sara: I am ready.\nOmar: I am ready too.",
    }

    assert build_synthesis_segments(body) == [
        ("I am ready.", "F1"),
        ("I am ready too.", "M1"),
    ]


def test_listening_cache_filename_includes_voice():
    assert listening_cache_filename([("I am ready.", "F1")]) == "supertonic_F1.wav"
    assert listening_cache_filename([("Hi.", "F1"), ("Hello.", "M1")]) == "supertonic_multivoice_F1_M1.wav"


@pytest.mark.asyncio
async def test_listening_lesson_audio_uses_gender_aware_renderer(monkeypatch, tmp_path):
    captured: dict[str, object] = {}

    class Item:
        id = 123
        skill = LanguageSkill.listening
        title = "A listening lesson"
        body_json = {
            "audio_transcript": "Sara: I am a student.",
            "speakers": [{"id": "speaker_1", "name": "Sara", "gender": "female"}],
        }

    async def fake_renderer(body, *, output_path: Path, language: str = "en"):
        captured["body"] = body
        captured["output_path"] = output_path
        captured["language"] = language
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"RIFF" + b"0" * 600)
        return True

    async def fake_upsert(_db, **kwargs):
        class Row:
            public_url = kwargs["public_url"]
            duration_seconds = None
            voice_source = kwargs["voice_source"]

        return Row()

    monkeypatch.setattr(language_tts_service.settings, "ENABLE_TTS", True)
    monkeypatch.setattr(language_tts_service.settings, "UPLOAD_DIR", str(tmp_path))
    monkeypatch.setattr(language_tts_service, "synthesize_listening_lesson_audio", fake_renderer)
    monkeypatch.setattr(language_tts_service, "_upsert_cache", fake_upsert)

    out = await language_tts_service._synthesize_supertonic(None, item=Item(), text="Sara: I am a student.")

    assert captured["body"] == Item.body_json
    assert str(captured["output_path"]).endswith("supertonic_F1.wav")
    assert out == {
        "public_url": "/uploads/language_audio/123/supertonic_F1.wav",
        "duration_seconds": None,
        "voice_source": "supertonic",
    }


def test_legacy_supertonic_cache_is_stale():
    class Row:
        voice_source = "supertonic"
        audio_storage_key = "language_audio/123/supertonic.wav"

    assert language_tts_service._is_legacy_supertonic_cache(Row()) is True
