"""Speaking legacy adapter (S0).

RESPONSIBILITY: Sole gateway for imports from frozen legacy flat speaking modules.
"""

from app.services.language_speaking_legacy_adapter.adapter import (
    KNOWN_RUNTIME_BLOCKERS,
    LEGACY_MODULE_MAP,
    LegacyTurnPayload,
    SpeakingLegacyAdapter,
)

__all__ = [
    "KNOWN_RUNTIME_BLOCKERS",
    "LEGACY_MODULE_MAP",
    "LegacyTurnPayload",
    "SpeakingLegacyAdapter",
]
