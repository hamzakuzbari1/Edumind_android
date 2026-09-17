"""Claude speaking educational analyzer — structured JSON facts only (S7)."""

from __future__ import annotations

import logging

from app.core.config import get_settings
from app.services.claude_service import claude_model_name, generate_claude_json, is_claude_configured
from app.services.language_speaking_educational_analyzer.mock_educational import build_mock_educational_facts
from app.services.language_speaking_educational_analyzer.parser import parse_speaking_educational_json
from app.services.language_speaking_educational_analyzer.prompt import SYSTEM_PROMPT, build_analysis_prompt
from app.services.language_speaking_educational_analyzer.types import (
    SpeakingAnalysisContext,
    SpeakingEducationalFacts,
    unavailable_speaking_facts,
)

logger = logging.getLogger(__name__)
settings = get_settings()


async def analyze_speaking_turn_educationally(*, context: SpeakingAnalysisContext) -> SpeakingEducationalFacts:
    """Return structured educational facts — never pass/fail."""
    mode = (settings.SPEAKING_EDUCATIONAL_ANALYZER or "claude").strip().lower()
    if mode == "off":
        return unavailable_speaking_facts(reason="analyzer_off")
    if mode == "mock":
        return build_mock_educational_facts(context)
    if not is_claude_configured():
        logger.warning("Speaking educational analyzer: Claude not configured (mode=%s)", mode)
        if mode == "claude":
            return unavailable_speaking_facts(reason="claude_not_configured")
        return build_mock_educational_facts(context)

    model = claude_model_name(settings.CLAUDE_MODEL)
    user_prompt = build_analysis_prompt(context=context)
    try:
        raw = await generate_claude_json(
            user_prompt,
            system=SYSTEM_PROMPT,
            temperature=0.2,
            max_output_tokens=4200,
            model_name=model,
            timeout=float(settings.SPEAKING_PROSODY_TIMEOUT_SECONDS or 120),
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("Speaking educational analysis failed: %s", exc)
        return unavailable_speaking_facts(reason=f"claude_failed:{type(exc).__name__}")

    facts = parse_speaking_educational_json(raw, model_name=model)
    if not facts.available:
        logger.warning("Speaking educational analyzer response unusable (%s)", facts.source)
        return unavailable_speaking_facts(reason=facts.source or "parse_failed")
    return facts
