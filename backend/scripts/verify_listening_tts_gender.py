"""Verify gender-aware listening TTS voice selection.

Usage (from backend/):
    python scripts/verify_listening_tts_gender.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

BACKEND = Path(__file__).resolve().parents[1]


def _reload_app_modules() -> None:
    for mod in list(sys.modules):
        if mod == "app" or mod.startswith("app."):
            del sys.modules[mod]


def static_checks() -> dict[str, bool]:
    tts_src = (BACKEND / "app/services/language_tts_service.py").read_text(encoding="utf-8")
    supertonic_src = (BACKEND / "app/services/language_supertonic_service.py").read_text(encoding="utf-8")
    gen_src = (BACKEND / "app/services/language_lesson_generation_service.py").read_text(encoding="utf-8")
    runtime_src = (BACKEND / "app/services/language_cefr/listening_runtime.py").read_text(encoding="utf-8")
    config_src = (BACKEND / "app/core/config.py").read_text(encoding="utf-8")

    return {
        "listening_tts_package": (BACKEND / "app/services/language_listening_tts/__init__.py").is_file(),
        "voice_config_layer": (BACKEND / "app/services/language_listening_tts/voice_config.py").is_file(),
        "segment_synthesis_api": "synthesize_language_speech_segments" in supertonic_src,
        "listening_skill_routing": "LanguageSkill.listening" in tts_src and "synthesize_listening_lesson_audio" in tts_src,
        "generation_speakers_persist": 'body["speakers"]' in gen_src,
        "prompt_speakers_schema": '"speakers"' in runtime_src and "gender" in runtime_src,
        "female_voice_setting": "LANGUAGE_SUPERTONIC_VOICE_FEMALE" in config_src,
        "male_voice_setting": "LANGUAGE_SUPERTONIC_VOICE_MALE" in config_src,
        "labeled_turns_helper": "extract_labeled_turns" in (
            BACKEND / "app/services/language_cefr/transcript_format.py"
        ).read_text(encoding="utf-8"),
    }


def segment_checks() -> dict[str, bool]:
    from app.services.language_listening_tts.speakers import build_synthesis_segments
    from app.services.language_listening_tts.voice_config import default_voice, female_voice, male_voice
    from app.services.language_listening_tts.renderer import listening_cache_filename

    female = female_voice()
    male = male_voice()
    default = default_voice()

    female_body = {
        "audio_transcript": "Hello, welcome to today's lesson about travel.",
        "speakers": [{"id": "speaker_1", "name": "Anna", "gender": "female"}],
    }
    male_body = {
        "audio_transcript": "Good morning. In this lecture we will discuss history.",
        "speakers": [{"id": "speaker_1", "name": "James", "gender": "male"}],
    }
    mixed_transcript = (
        "Sarah:\nHi John, are you ready for the meeting?\n"
        "John:\nYes Sarah, I have the report with me.\n"
        "Sarah:\nGreat, let's start with the budget."
    )
    mixed_body = {
        "audio_transcript": mixed_transcript,
        "speakers": [
            {"id": "speaker_1", "name": "Sarah", "gender": "female"},
            {"id": "speaker_2", "name": "John", "gender": "male"},
        ],
    }
    unknown_body = {
        "audio_transcript": "Alex:\nHello there.\nJordan:\nHi Alex.",
        "speakers": [{"id": "speaker_1", "name": "Alex", "gender": ""}],
    }
    regression_body = {
        "audio_transcript": "This is a plain monologue without speaker labels or metadata.",
    }

    female_segments = build_synthesis_segments(female_body)
    male_segments = build_synthesis_segments(male_body)
    mixed_segments = build_synthesis_segments(mixed_body)
    unknown_segments = build_synthesis_segments(unknown_body)
    regression_segments = build_synthesis_segments(regression_body)

    mixed_voices = [voice for _, voice in mixed_segments]
    sarah_voices = {voice for _, voice in mixed_segments[::2]}
    john_voices = {voice for _, voice in mixed_segments[1::2]}

    return {
        "female_lesson_uses_female_voice": len(female_segments) == 1 and female_segments[0][1] == female,
        "male_lesson_uses_male_voice": len(male_segments) == 1 and male_segments[0][1] == male,
        "mixed_conversation_alternates": len(mixed_segments) == 3 and mixed_voices == [female, male, female],
        "mixed_speaker_identity_stable": sarah_voices == {female} and john_voices == {male},
        "unknown_speaker_falls_back": all(voice == default for _, voice in unknown_segments),
        "monologue_regression_default": len(regression_segments) == 1 and regression_segments[0][1] == default,
        "multivoice_cache_filename": listening_cache_filename(mixed_segments).startswith("supertonic_multivoice"),
        "single_voice_cache_filename": listening_cache_filename(regression_segments) == "supertonic.wav",
    }


async def renderer_checks() -> dict[str, bool]:
    from app.services.language_listening_tts.renderer import synthesize_listening_lesson_audio
    from app.services.language_listening_tts.voice_config import female_voice, male_voice

    captured: list[tuple[str, str]] = []

    async def _fake_segments(segments, *, language, output_path, pause_ms=350):
        captured.extend(segments)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"RIFFfake")
        return True

    body = {
        "audio_transcript": "Sarah:\nHello.\nJohn:\nHi.",
        "speakers": [
            {"id": "speaker_1", "name": "Sarah", "gender": "female"},
            {"id": "speaker_2", "name": "John", "gender": "male"},
        ],
    }
    out_path = Path(__file__).resolve().parent / ".tmp_listening_tts_gender_verify.wav"

    with patch(
        "app.services.language_listening_tts.renderer.synthesize_language_speech_segments",
        new=AsyncMock(side_effect=_fake_segments),
    ):
        ok = await synthesize_listening_lesson_audio(body, output_path=out_path, language="en")

    female = female_voice()
    male = male_voice()
    return {
        "renderer_delegates_segments": ok and len(captured) == 2,
        "renderer_passes_gender_voices": captured == [("Hello.", female), ("Hi.", male)],
    }


def main() -> int:
    _reload_app_modules()

    static = static_checks()
    segments = segment_checks()
    renderer = asyncio.run(renderer_checks())

    print("=== Listening TTS Gender Voice Selection ===\n")

    print("Static:")
    for key, value in static.items():
        print(f"  {key}: {'PASS' if value else 'FAIL'}")

    print("\nSegment mapping:")
    for key, value in segments.items():
        print(f"  {key}: {'PASS' if value else 'FAIL'}")

    print("\nRenderer:")
    for key, value in renderer.items():
        print(f"  {key}: {'PASS' if value else 'FAIL'}")

    all_checks = {**static, **segments, **renderer}
    passed = sum(1 for v in all_checks.values() if v)
    total = len(all_checks)
    ok = all(all_checks.values())
    print(f"\n=== Results: {passed}/{total} checks passed ===")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
