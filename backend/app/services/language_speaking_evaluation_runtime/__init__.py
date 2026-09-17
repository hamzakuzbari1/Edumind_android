"""Speaking evaluation_runtime (S4/S5/S6/S7).

RESPONSIBILITY: Turn pipeline orchestration through hybrid evaluation engine.
"""

from app.services.language_speaking_evaluation_runtime.audio_runtime import (
    LANGUAGE_SPEAKING_EVALUATION_RUNTIME_VERSION,
    SpeakingAudioRuntimeResult,
    process_speaking_audio,
)
from app.services.language_speaking_evaluation_runtime.evaluation_pipeline import (
    LANGUAGE_SPEAKING_EVALUATION_PIPELINE_VERSION,
    SPEAKING_ENGINE_RESULT_KEY,
    SpeakingEvaluationTurnResult,
    process_speaking_evaluation,
)
from app.services.language_speaking_evaluation_runtime.knowledge_bridge import (
    apply_speaking_evaluation_to_knowledge_model,
    build_speaking_skill_observations,
)
from app.services.language_speaking_evaluation_runtime.knowledge_bridge_types import (
    LANGUAGE_SPEAKING_KNOWLEDGE_BRIDGE_VERSION,
    SpeakingKnowledgeMutationStatus,
)
from app.services.language_speaking_evaluation_runtime.evi_tool_runtime import (
    LiveContextCache,
    SPEAKING_LIVE_TOOL_ALLOWLIST,
    dispatch_evi_tool,
    get_live_context_cache,
    handle_evi_tool_call,
    invalidate_live_context,
)
from app.services.language_speaking_evaluation_runtime.live_runtime import (
    LANGUAGE_SPEAKING_LIVE_RUNTIME_VERSION,
    LiveTurnEvaluationResult,
    build_evi_evidence_from_events,
    get_evi_client_token,
    process_completed_live_turn,
)
from app.services.language_speaking_evaluation_runtime.pronunciation_runtime import (
    SpeakingPronunciationRuntimeResult,
    process_speaking_pronunciation,
)
from app.services.language_speaking_evaluation_runtime.prosody_runtime import (
    SpeakingProsodyRuntimeResult,
    process_speaking_prosody,
)

__all__ = [
    "LANGUAGE_SPEAKING_EVALUATION_PIPELINE_VERSION",
    "LANGUAGE_SPEAKING_EVALUATION_RUNTIME_VERSION",
    "LANGUAGE_SPEAKING_KNOWLEDGE_BRIDGE_VERSION",
    "LANGUAGE_SPEAKING_LIVE_RUNTIME_VERSION",
    "SPEAKING_ENGINE_RESULT_KEY",
    "LiveContextCache",
    "LiveTurnEvaluationResult",
    "SPEAKING_LIVE_TOOL_ALLOWLIST",
    "SpeakingKnowledgeMutationStatus",
    "SpeakingAudioRuntimeResult",
    "SpeakingEvaluationTurnResult",
    "SpeakingPronunciationRuntimeResult",
    "SpeakingProsodyRuntimeResult",
    "apply_speaking_evaluation_to_knowledge_model",
    "build_speaking_skill_observations",
    "build_evi_evidence_from_events",
    "dispatch_evi_tool",
    "get_evi_client_token",
    "get_live_context_cache",
    "handle_evi_tool_call",
    "invalidate_live_context",
    "process_completed_live_turn",
    "process_speaking_audio",
    "process_speaking_evaluation",
    "process_speaking_pronunciation",
    "process_speaking_prosody",
]
