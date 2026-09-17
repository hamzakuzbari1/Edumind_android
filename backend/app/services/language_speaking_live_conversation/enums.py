"""Live conversation lifecycle states (S7.5)."""

from __future__ import annotations

from enum import StrEnum

LANGUAGE_SPEAKING_LIVE_CONVERSATION_VERSION = "7.5.0"


class SpeakingLiveSessionState(StrEnum):
    created = "created"
    connecting = "connecting"
    connected = "connected"
    listening = "listening"
    user_speaking = "user_speaking"
    user_turn_complete = "user_turn_complete"
    assistant_thinking = "assistant_thinking"
    assistant_speaking = "assistant_speaking"
    interrupted = "interrupted"
    closing = "closing"
    closed = "closed"
    failed = "failed"
