"""Types for language_speaking_audio_session (S3).

Owns the audio session record and its lifecycle. Infrastructure state only —
no educational scoring, mastery, readiness, or performance fields.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime

from app.services.language_speaking.enums import SpeakingAudioSource
from app.services.language_speaking_audio_session.enums import SpeakingAudioLifecycleState
from app.services.language_speaking_audio_session.transitions import (
    IllegalAudioSessionTransition,
    is_legal_transition,
)

LANGUAGE_SPEAKING_AUDIO_SESSION_VERSION = "0.3.0"


@dataclass(frozen=True, slots=True)
class SpeakingAudioSessionRecord:
    """Infrastructure record for one speaking audio session.

    Tracks the ingestion/processing lifecycle of audio for a student turn.
    This object never carries educational judgement — no pass/fail, mastery,
    readiness, CEFR, or lesson-completion fields are permitted here.
    """

    session_id: str
    student_id: int
    language_id: int
    audio_source: SpeakingAudioSource
    lifecycle_state: SpeakingAudioLifecycleState
    audio_id: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    expires_at: datetime | None = None
    failure_reason: str = ""
    record_version: str = LANGUAGE_SPEAKING_AUDIO_SESSION_VERSION

    def with_transition(
        self,
        to_state: SpeakingAudioLifecycleState,
        *,
        now: datetime | None = None,
        failure_reason: str = "",
    ) -> "SpeakingAudioSessionRecord":
        """Return a new record moved to ``to_state``.

        Raises ``IllegalAudioSessionTransition`` if the move is not permitted.
        """
        if not is_legal_transition(self.lifecycle_state, to_state):
            raise IllegalAudioSessionTransition(self.lifecycle_state, to_state)
        return replace(
            self,
            lifecycle_state=to_state,
            updated_at=now or self.updated_at,
            failure_reason=failure_reason or self.failure_reason,
        )

    def to_persistence_dict(self) -> dict[str, object]:
        return {
            "session_id": self.session_id,
            "student_id": self.student_id,
            "language_id": self.language_id,
            "audio_source": self.audio_source.value,
            "lifecycle_state": self.lifecycle_state.value,
            "audio_id": self.audio_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "failure_reason": self.failure_reason,
            "record_version": self.record_version,
        }


# Backwards-compatible alias for the former S0 stub name.
SpeakingSessionRecord = SpeakingAudioSessionRecord
