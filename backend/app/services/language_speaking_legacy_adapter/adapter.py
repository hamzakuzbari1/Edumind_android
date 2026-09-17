"""Legacy Speaking adapter (S0) — freeze-wrap boundary for flat legacy services.

RESPONSIBILITY: The ONLY package permitted to import legacy flat modules
(language_conversation_service, language_speaking_feedback_service, etc.).
New speaking packages must route through this adapter until S7+ migration.

Legacy modules are FROZEN — no new features. They continue to serve existing
API routes until replaced endpoint-by-endpoint.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# Documented mapping — legacy module → canonical target (S7+)
LEGACY_MODULE_MAP: dict[str, str] = {
    "language_transcription_service": "SpeechTranscriptionProvider (legacy impl)",
    "language_pronunciation_service": "pronunciation analysis (legacy Claude+STT)",
    "language_conversation_service": "evaluation_runtime (conversation turn)",
    "language_conversation_ai_service": "SpeakingEducationalAnalyzerProvider (legacy)",
    "language_speaking_feedback_service": "evaluation_runtime (prompt submit)",
    "language_speaking_service": "lesson_experience (prompt list/upload)",
    "language_speaking_evolution_service": "progression (analytics.speaking_level — to migrate)",
    "language_speaking_coach_service": "coach (UNWIRED — replace with language_speaking_coach)",
    "language_shadowing_service": "lesson_experience (shadowing mode)",
    "language_conversation_scenario_service": "lesson_experience (scenarios)",
    "language_reply_tts_service": "SpeakingSpeechOutputProvider (Supertonic legacy wrapper)",
    "speaking_coach_service": "standalone /speaking/coach API (in-memory, separate from main flow)",
}

# Known runtime blockers tracked for S0 — fix in hotfix PR, not S0 implementation.
KNOWN_RUNTIME_BLOCKERS: tuple[dict[str, str], ...] = (
    {
        "id": "mastery_settings_attr",
        "module": "language_speaking_evolution_service",
        "issue": "Reads settings.LANGUAGE_MASTERY_WINDOW but config defines LANGUAGE_MASTERY_WINDOW_SIZE",
        "impact": "Conversation level update may raise AttributeError every turn",
    },
    {
        "id": "tts_signature_mismatch",
        "module": "language_conversation_service",
        "issue": "Calls synthesize_english_reply(segments=, voice=) but wrapper accepts text= only",
        "impact": "Sync reply TTS may fail with TypeError",
    },
    {
        "id": "dual_level_system",
        "module": "language_speaking_evolution_service",
        "issue": "Writes analytics.speaking_level; official_speaking_cefr column unused by speaking runtime",
        "impact": "Inconsistent CEFR across modules until S15–S18 progression wired",
    },
)


@dataclass(frozen=True, slots=True)
class LegacyTurnPayload:
    """Opaque legacy turn result — adapter normalizes to canonical types in S7+."""

    source_module: str
    raw: dict[str, Any]
    adapter_version: str = "0.1.0"


class SpeakingLegacyAdapter:
    """S0 interface — documents boundary; passthrough implementations in S7+."""

    adapter_version: str = "0.1.0"

    @staticmethod
    def legacy_modules() -> dict[str, str]:
        return dict(LEGACY_MODULE_MAP)

    @staticmethod
    def known_blockers() -> tuple[dict[str, str], ...]:
        return KNOWN_RUNTIME_BLOCKERS

    async def adapt_conversation_turn(self, *, raw_result: dict[str, object]) -> LegacyTurnPayload:
        """Placeholder — returns wrapped legacy payload until canonical evaluation exists."""
        return LegacyTurnPayload(source_module="language_conversation_service", raw=dict(raw_result))

    async def adapt_prompt_submit(self, *, raw_result: dict[str, object]) -> LegacyTurnPayload:
        """Placeholder for prompt submit path."""
        return LegacyTurnPayload(source_module="language_speaking_feedback_service", raw=dict(raw_result))
