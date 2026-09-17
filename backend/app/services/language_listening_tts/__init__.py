"""Gender-aware listening TTS."""

from app.services.language_listening_tts.renderer import (
    listening_cache_filename,
    synthesize_listening_lesson_audio,
)
from app.services.language_listening_tts.speakers import build_synthesis_segments
from app.services.language_listening_tts.voice_config import (
    default_voice,
    female_voice,
    male_voice,
    voice_for_gender,
)

__all__ = [
    "build_synthesis_segments",
    "default_voice",
    "female_voice",
    "male_voice",
    "voice_for_gender",
    "listening_cache_filename",
    "synthesize_listening_lesson_audio",
]
