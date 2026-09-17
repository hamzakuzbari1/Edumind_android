"""Grammar Speaking Domain Framework (V1.2A).

RESPONSIBILITY: Business model for Speaking activities inside the Grammar spine.
Zero LLM / STT / TTS / audio streaming. Evidence maps to GrammarEvidenceObservation only.
"""

from __future__ import annotations

from app.services.language_grammar_speaking.enums import (
    SPEAKING_DOMAIN_PACKAGE_VERSION,
    SPEAKING_DOMAIN_SCHEMA_VERSION,
    SpeakingAttemptStatus,
    SpeakingCompletionState,
    SpeakingEventType,
    SpeakingLifecyclePhase,
    SpeakingSessionStatus,
    SpeakingSpeaker,
    SpeakingTurnStatus,
)
from app.services.language_grammar_speaking.errors import (
    SpeakingDomainError,
    SpeakingLifecycleError,
    SpeakingStateError,
    SpeakingValidationError,
)
from app.services.language_grammar_speaking.evidence import (
    build_speaking_evidence,
    map_session_result_to_observations,
    map_speaking_evidence_to_observations,
)
from app.services.language_grammar_speaking.flags import (
    grammar_engine_enabled,
    speaking_domain_enabled,
)
from app.services.language_grammar_speaking.lifecycle import (
    cancel,
    complete_session,
    finish_attempt,
    initialize,
    next_turn,
    run_happy_path,
    start_attempt,
    start_session,
    to_view,
)
from app.services.language_grammar_speaking.state_machine import (
    ATTEMPT_TRANSITIONS,
    SESSION_TRANSITIONS,
    TURN_TRANSITIONS,
    assert_attempt_transition,
    assert_session_transition,
    assert_turn_transition,
)
from app.services.language_grammar_speaking.types import (
    SpeakingArtifact,
    SpeakingAttempt,
    SpeakingContext,
    SpeakingEvidence,
    SpeakingEvent,
    SpeakingResult,
    SpeakingSession,
    SpeakingSessionView,
    SpeakingState,
    SpeakingTiming,
    SpeakingTurn,
)
from app.services.language_grammar_speaking.validation import (
    validate_attempt_state,
    validate_context,
    validate_grammar_targets,
    validate_session,
    validate_session_state,
    validate_turn_order,
)

PACKAGE_VERSION = SPEAKING_DOMAIN_PACKAGE_VERSION
RESPONSIBILITY = (
    "Speaking Domain Framework - session/attempt/turn/result/evidence models + lifecycle; "
    "no LLM, no audio, no mastery writes"
)

__all__ = [
    "ATTEMPT_TRANSITIONS",
    "PACKAGE_VERSION",
    "RESPONSIBILITY",
    "SESSION_TRANSITIONS",
    "SPEAKING_DOMAIN_PACKAGE_VERSION",
    "SPEAKING_DOMAIN_SCHEMA_VERSION",
    "TURN_TRANSITIONS",
    "SpeakingArtifact",
    "SpeakingAttempt",
    "SpeakingAttemptStatus",
    "SpeakingCompletionState",
    "SpeakingContext",
    "SpeakingDomainError",
    "SpeakingEvent",
    "SpeakingEventType",
    "SpeakingEvidence",
    "SpeakingLifecycleError",
    "SpeakingLifecyclePhase",
    "SpeakingResult",
    "SpeakingSession",
    "SpeakingSessionStatus",
    "SpeakingSessionView",
    "SpeakingSpeaker",
    "SpeakingState",
    "SpeakingStateError",
    "SpeakingTiming",
    "SpeakingTurn",
    "SpeakingTurnStatus",
    "SpeakingValidationError",
    "assert_attempt_transition",
    "assert_session_transition",
    "assert_turn_transition",
    "build_speaking_evidence",
    "cancel",
    "complete_session",
    "finish_attempt",
    "grammar_engine_enabled",
    "initialize",
    "map_session_result_to_observations",
    "map_speaking_evidence_to_observations",
    "next_turn",
    "run_happy_path",
    "speaking_domain_enabled",
    "start_attempt",
    "start_session",
    "to_view",
    "validate_attempt_state",
    "validate_context",
    "validate_grammar_targets",
    "validate_session",
    "validate_session_state",
    "validate_turn_order",
]
