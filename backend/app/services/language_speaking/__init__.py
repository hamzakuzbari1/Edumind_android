"""Speaking skill enums and core contracts (S0).

RESPONSIBILITY: Shared enums, SpeakingAudioSession, SpeakingSpeechEvidence stubs,
and package ownership registry. No evaluation logic or provider implementations.
"""

from app.services.language_speaking.enums import (
    InterruptionDecision,
    OfficialSpeakingCEFR,
    PromotionStatus,
    SpeakingAudioSource,
    SpeakingCoachPersonality,
    SpeakingConversationState,
    SpeakingGoal,
    SpeakingLearningStage,
    SpeakingLessonLifecycle,
    SpeakingSessionProcessingState,
    SpeakingSkillType,
    SpeakingTaskType,
)
from app.services.language_speaking.ownership import (
    ALLOWED_PACKAGE_DEPENDENCIES,
    ARCHITECTURE_LAYERS,
    FORBIDDEN_LEGACY_IMPORTS_IN,
    FORBIDDEN_PROVIDER_SDK_IMPORTS,
    LEGACY_FLAT_MODULES,
    LEGACY_IMPORT_GATEWAY,
    PACKAGE_LAYER,
    PACKAGE_OWNERSHIP,
    REQUIRED_S0_PACKAGES,
    SHARED_INFRASTRUCTURE,
)
from app.services.language_speaking.types import (
    PauseMarker,
    PhonemeAlignment,
    ProsodyFeatures,
    SPEAKING_CORE_TYPES_VERSION,
    SpeakingAudioSession,
    SpeakingSpeechEvidence,
    WordTiming,
)

__all__ = [
    "ALLOWED_PACKAGE_DEPENDENCIES",
    "ARCHITECTURE_LAYERS",
    "FORBIDDEN_LEGACY_IMPORTS_IN",
    "FORBIDDEN_PROVIDER_SDK_IMPORTS",
    "InterruptionDecision",
    "LEGACY_FLAT_MODULES",
    "LEGACY_IMPORT_GATEWAY",
    "OfficialSpeakingCEFR",
    "PACKAGE_LAYER",
    "PACKAGE_OWNERSHIP",
    "PauseMarker",
    "PhonemeAlignment",
    "PromotionStatus",
    "ProsodyFeatures",
    "REQUIRED_S0_PACKAGES",
    "SHARED_INFRASTRUCTURE",
    "SPEAKING_CORE_TYPES_VERSION",
    "SpeakingAudioSession",
    "SpeakingAudioSource",
    "SpeakingCoachPersonality",
    "SpeakingConversationState",
    "SpeakingGoal",
    "SpeakingLearningStage",
    "SpeakingLessonLifecycle",
    "SpeakingSessionProcessingState",
    "SpeakingSkillType",
    "SpeakingSpeechEvidence",
    "SpeakingTaskType",
    "WordTiming",
]
