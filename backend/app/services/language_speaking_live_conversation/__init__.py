"""Speaking live_conversation (S7.5) — provider-neutral live session contracts.

RESPONSIBILITY: Live session/turn/event facts and turn audio accumulator — no scoring.
"""

from app.services.language_speaking_live_conversation.enums import (
    LANGUAGE_SPEAKING_LIVE_CONVERSATION_VERSION,
    SpeakingLiveSessionState,
)
from app.services.language_speaking_live_conversation.errors import (
    LiveAuthenticationFailedError,
    LiveConfigurationInvalidError,
    LiveConnectionClosedError,
    LiveConnectionFailedError,
    LiveEvaluationHandoffFailedError,
    LiveProtocolError,
    LiveProviderUnavailableError,
    LiveReconnectFailedError,
    LiveTurnFinalizationFailedError,
    LiveTurnTimeoutError,
    LiveTurnTooLargeError,
    SpeakingLiveRuntimeError,
)
from app.services.language_speaking_live_conversation.transitions import (
    IllegalLiveTransition,
    is_legal_live_transition,
)
from app.services.language_speaking_live_conversation.turn_accumulator import StudentTurnAudioAccumulator
from app.services.language_speaking_live_conversation.tutor_context import LiveTutorContext, default_live_tutor_context
from app.services.language_speaking_live_conversation.types import (
    SpeakingLiveAudioChunk,
    SpeakingLiveConversationEvidence,
    SpeakingLiveEvent,
    SpeakingLiveProviderProvenance,
    SpeakingLiveSession,
    SpeakingLiveTurn,
)

__all__ = [
    "LANGUAGE_SPEAKING_LIVE_CONVERSATION_VERSION",
    "IllegalLiveTransition",
    "LiveAuthenticationFailedError",
    "LiveConfigurationInvalidError",
    "LiveConnectionClosedError",
    "LiveConnectionFailedError",
    "LiveEvaluationHandoffFailedError",
    "LiveProtocolError",
    "LiveProviderUnavailableError",
    "LiveReconnectFailedError",
    "LiveTurnFinalizationFailedError",
    "LiveTurnTimeoutError",
    "LiveTurnTooLargeError",
    "LiveTutorContext",
    "SpeakingLiveRuntimeError",
    "SpeakingLiveAudioChunk",
    "SpeakingLiveConversationEvidence",
    "SpeakingLiveEvent",
    "SpeakingLiveProviderProvenance",
    "SpeakingLiveSession",
    "SpeakingLiveSessionState",
    "SpeakingLiveTurn",
    "StudentTurnAudioAccumulator",
    "default_live_tutor_context",
    "is_legal_live_transition",
]
