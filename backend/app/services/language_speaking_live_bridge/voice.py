"""Legacy Scene Practice TTS wrapper — delegates to shared audio_frontend TTS.

Kept so M12 verifiers and dormant rehearsal paths keep working.
Prefer language_speaking_audio_frontend.tts_runtime for new code.
"""

from __future__ import annotations

from app.services.language_speaking_audio_frontend.tts_runtime import (
    TTS_AUDIO_FORMAT,
    TTS_AUDIO_MIME,
    synthesize_spoken_line,
)

# Backward-compatible names
synthesize_scene_line = synthesize_spoken_line

__all__ = [
    "TTS_AUDIO_FORMAT",
    "TTS_AUDIO_MIME",
    "synthesize_scene_line",
    "synthesize_spoken_line",
]
