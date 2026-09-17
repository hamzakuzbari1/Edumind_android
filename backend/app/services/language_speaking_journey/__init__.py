"""Speaking journey bundle assembly (S9 + S12 read model + S14 Alex context/identity).

RESPONSIBILITY: Student-facing SpeakingJourneyBundle assembly, journey API
orchestration, canonical Alex educational context projection, and backend-authoritative
live-execution identity / pre-evaluation authorization boundary.
"""

from app.services.language_speaking_journey.alex_context import (
    ALEX_EDUCATIONAL_CONTEXT_VERSION,
    MISSION_BEHAVIOR_CONTRACT,
    TUTOR_BEHAVIOR_CONTRACT,
    AlexSpeakingEducationalContext,
    authoritative_task_prompt,
    build_alex_speaking_educational_context,
    mission_behavior_for_kind,
)
from app.services.language_speaking_journey.builder import build_speaking_journey_bundle
from app.services.language_speaking_journey.errors import (
    AmbiguousActiveAttemptError,
    InvalidLiveSessionError,
    LiveExecutionNotReadyError,
    LiveSessionNotOwnedError,
    LiveTaskMismatchError,
    SpeakingContextStaleError,
    SpeakingContextUnavailableError,
    SpeakingLiveExecutionError,
)
from app.services.language_speaking_journey.live_execution import (
    LIVE_SESSION_ID_PREFIX,
    LiveTurnAuthorization,
    authorize_live_turn_execution,
    derive_live_session_id,
    is_backend_live_session_id,
)
from app.services.language_speaking_journey.read_model import (
    LANGUAGE_SPEAKING_JOURNEY_READ_MODEL_VERSION,
    SpeakingJourneyReadModel,
    build_speaking_journey_read_model,
)
from app.services.language_speaking_journey.types import (
    LANGUAGE_SPEAKING_JOURNEY_VERSION,
    SpeakingJourneyBundle,
    SpeakingJourneyMissionOut,
)

__all__ = [
    "ALEX_EDUCATIONAL_CONTEXT_VERSION",
    "LANGUAGE_SPEAKING_JOURNEY_READ_MODEL_VERSION",
    "LANGUAGE_SPEAKING_JOURNEY_VERSION",
    "LIVE_SESSION_ID_PREFIX",
    "MISSION_BEHAVIOR_CONTRACT",
    "TUTOR_BEHAVIOR_CONTRACT",
    "AlexSpeakingEducationalContext",
    "AmbiguousActiveAttemptError",
    "InvalidLiveSessionError",
    "LiveExecutionNotReadyError",
    "LiveSessionNotOwnedError",
    "LiveTaskMismatchError",
    "LiveTurnAuthorization",
    "SpeakingContextStaleError",
    "SpeakingContextUnavailableError",
    "SpeakingJourneyBundle",
    "SpeakingJourneyMissionOut",
    "SpeakingJourneyReadModel",
    "SpeakingLiveExecutionError",
    "authoritative_task_prompt",
    "authorize_live_turn_execution",
    "build_alex_speaking_educational_context",
    "build_speaking_journey_bundle",
    "build_speaking_journey_read_model",
    "derive_live_session_id",
    "is_backend_live_session_id",
    "mission_behavior_for_kind",
]
