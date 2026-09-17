"""Provider-neutral live conversation contracts (S7.5)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from app.services.language_speaking_live_conversation.enums import (
    LANGUAGE_SPEAKING_LIVE_CONVERSATION_VERSION,
    SpeakingLiveSessionState,
)


@dataclass(frozen=True, slots=True)
class SpeakingLiveProviderProvenance:
    provider_name: str
    api_version: str = "v0"
    config_id: str = ""
    model_name: str = ""
    chat_id: str = ""
    chat_group_id: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "provider_name": self.provider_name,
            "api_version": self.api_version,
            "config_id": self.config_id,
            "model_name": self.model_name,
            "chat_id": self.chat_id,
            "chat_group_id": self.chat_group_id,
        }


@dataclass(frozen=True, slots=True)
class SpeakingLiveAudioChunk:
    pcm_bytes: bytes
    sample_rate_hz: int = 16000
    channels: int = 1
    captured_at_ms: int = 0
    source: str = "student_microphone"


@dataclass(frozen=True, slots=True)
class SpeakingLiveEvent:
    event_type: str
    payload: dict[str, object]
    received_at: str
    provider_event_type: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "event_type": self.event_type,
            "provider_event_type": self.provider_event_type,
            "payload": self.payload,
            "received_at": self.received_at,
        }


@dataclass(frozen=True, slots=True)
class SpeakingLiveExpressionMeasure:
    provider_label: str
    score: float
    segment_start_ms: int = 0
    segment_end_ms: int = 0

    def to_dict(self) -> dict[str, object]:
        return {
            "provider_label": self.provider_label,
            "score": round(self.score, 4),
            "segment_start_ms": self.segment_start_ms,
            "segment_end_ms": self.segment_end_ms,
        }


@dataclass(frozen=True, slots=True)
class SpeakingLiveConversationEvidence:
    """EVI/live conversation facts — separate from S6 acoustic evidence."""

    provider_transcript: str
    expression_measures: tuple[SpeakingLiveExpressionMeasure, ...]
    event_sequence: tuple[SpeakingLiveEvent, ...]
    interruption_count: int
    provider_chat_id: str
    provider_chat_group_id: str
    turn_timing_ms: tuple[int, int] | None = None
    warnings: tuple[str, ...] = ()
    unavailable_fields: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "provider_transcript": self.provider_transcript,
            "expression_measures": [m.to_dict() for m in self.expression_measures],
            "event_sequence": [e.to_dict() for e in self.event_sequence],
            "interruption_count": self.interruption_count,
            "provider_chat_id": self.provider_chat_id,
            "provider_chat_group_id": self.provider_chat_group_id,
            "turn_timing_ms": list(self.turn_timing_ms) if self.turn_timing_ms else None,
            "warnings": list(self.warnings),
            "unavailable_fields": list(self.unavailable_fields),
            "evidence_kind": "live_conversation",
            "non_canonical": True,
        }


@dataclass(frozen=True, slots=True)
class SpeakingLiveTurn:
    turn_id: str
    session_id: str
    student_id: int
    language_id: int
    started_at: str
    ended_at: str
    audio_bytes: bytes
    audio_content_type: str
    provider_transcript: str
    evi_evidence: SpeakingLiveConversationEvidence
    interruption_context: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    finalized: bool = True

    def to_dict(self) -> dict[str, object]:
        return {
            "turn_id": self.turn_id,
            "session_id": self.session_id,
            "student_id": self.student_id,
            "language_id": self.language_id,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "audio_byte_size": len(self.audio_bytes),
            "audio_content_type": self.audio_content_type,
            "provider_transcript": self.provider_transcript,
            "evi_evidence": self.evi_evidence.to_dict(),
            "interruption_context": list(self.interruption_context),
            "warnings": list(self.warnings),
            "finalized": self.finalized,
        }


@dataclass(frozen=True, slots=True)
class SpeakingLiveSession:
    session_id: str
    student_id: int
    language_id: int
    provider_name: str
    state: SpeakingLiveSessionState
    started_at: str
    provider_session_id: str = ""
    ended_at: str = ""
    current_turn_id: str = ""
    turn_count: int = 0
    interruption_count: int = 0
    provider_provenance: SpeakingLiveProviderProvenance | None = None
    warnings: tuple[str, ...] = field(default_factory=tuple)
    schema_version: str = LANGUAGE_SPEAKING_LIVE_CONVERSATION_VERSION

    def to_dict(self) -> dict[str, object]:
        return {
            "session_id": self.session_id,
            "student_id": self.student_id,
            "language_id": self.language_id,
            "provider_name": self.provider_name,
            "state": self.state.value,
            "started_at": self.started_at,
            "provider_session_id": self.provider_session_id,
            "ended_at": self.ended_at,
            "current_turn_id": self.current_turn_id,
            "turn_count": self.turn_count,
            "interruption_count": self.interruption_count,
            "provider_provenance": self.provider_provenance.to_dict() if self.provider_provenance else None,
            "warnings": list(self.warnings),
            "schema_version": self.schema_version,
        }
