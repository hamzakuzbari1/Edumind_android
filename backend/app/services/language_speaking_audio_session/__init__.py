"""Speaking audio_session (S3).

RESPONSIBILITY: Owns the audio session record and its ingestion/processing
lifecycle state machine. Infrastructure state only — never educational scoring,
mastery, readiness, or speaking performance.
"""

from app.services.language_speaking_audio_session.enums import SpeakingAudioLifecycleState
from app.services.language_speaking_audio_session.transitions import (
    ABSORBING_AUDIO_SESSION_STATE,
    IllegalAudioSessionTransition,
    LEGAL_AUDIO_SESSION_TRANSITIONS,
    TERMINAL_AUDIO_SESSION_STATES,
    is_legal_transition,
    next_states,
)
from app.services.language_speaking_audio_session.types import (
    LANGUAGE_SPEAKING_AUDIO_SESSION_VERSION,
    SpeakingAudioSessionRecord,
    SpeakingSessionRecord,
)

__all__ = [
    "ABSORBING_AUDIO_SESSION_STATE",
    "IllegalAudioSessionTransition",
    "LANGUAGE_SPEAKING_AUDIO_SESSION_VERSION",
    "LEGAL_AUDIO_SESSION_TRANSITIONS",
    "SpeakingAudioLifecycleState",
    "SpeakingAudioSessionRecord",
    "SpeakingSessionRecord",
    "TERMINAL_AUDIO_SESSION_STATES",
    "is_legal_transition",
    "next_states",
]
