"""M10 Live Speaking Bridge — Educational Case → Scene Practice → Hume EVI.

RESPONSIBILITY: Own the Discussion → Scene Practice → Alex runtime transition for
ONE Educational Case: scenario preparation, rehearsal state, and the
LiveConversationContext handoff. Claude directs Scene Practice turns (M12);
never grades, never assigns CEFR, never authors package content.
"""

from app.services.language_speaking_live_bridge.continuity import (
    assert_same_world,
    continuity_fingerprint_for_package,
    extract_case_continuity_fields,
)
from app.services.language_speaking_live_bridge.engine import (
    LiveBridgeError,
    LiveBridgeView,
    apply_live_bridge_to_alex_payload,
    build_preparation,
    complete_rehearsal,
    get_live_bridge_view,
    respond_rehearsal_turn,
    start_voice_rehearsal,
    submit_rehearsal_turn,
)
from app.services.language_speaking_live_bridge.live_context import (
    build_live_conversation_context,
    merge_live_context_into_alex_dict,
)
from app.services.language_speaking_live_bridge.scenario import (
    build_speaking_scenario,
    scenario_to_prep_projection,
)
from app.services.language_speaking_live_bridge.types import (
    LIVE_BRIDGE_VERSION,
    SPEAKING_LIVE_BRIDGE_KEY,
    LiveBridgeBundle,
    LiveConversationContext,
    RehearsalState,
    SpeakingScenario,
)

__all__ = [
    "LIVE_BRIDGE_VERSION",
    "SPEAKING_LIVE_BRIDGE_KEY",
    "LiveBridgeBundle",
    "LiveBridgeError",
    "LiveBridgeView",
    "LiveConversationContext",
    "RehearsalState",
    "SpeakingScenario",
    "apply_live_bridge_to_alex_payload",
    "assert_same_world",
    "build_live_conversation_context",
    "build_preparation",
    "build_speaking_scenario",
    "complete_rehearsal",
    "continuity_fingerprint_for_package",
    "extract_case_continuity_fields",
    "get_live_bridge_view",
    "merge_live_context_into_alex_dict",
    "respond_rehearsal_turn",
    "scenario_to_prep_projection",
    "start_voice_rehearsal",
    "submit_rehearsal_turn",
]
