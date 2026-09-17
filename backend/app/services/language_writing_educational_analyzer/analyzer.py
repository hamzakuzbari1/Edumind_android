"""Claude Educational Analyzer — deep teacher-like educational facts (JSON only)."""

from __future__ import annotations

import logging

from app.core.config import get_settings
from app.services.claude_service import claude_model_name, generate_claude_json, is_claude_configured
from app.services.language_writing_educational_analyzer.mock_educational import build_mock_educational_facts
from app.services.language_writing_educational_analyzer.parser import parse_claude_educational_json
from app.services.language_writing_educational_analyzer.prompt import SYSTEM_PROMPT, build_analysis_prompt
from app.services.language_writing_educational_analyzer.types import (
    ClaudeEducationalFacts,
    EducationalAnalysisContext,
    unavailable_claude_facts,
)

logger = logging.getLogger(__name__)
settings = get_settings()


async def analyze_writing_draft_educationally(
    *,
    draft_text: str,
    context: EducationalAnalysisContext,
) -> ClaudeEducationalFacts:
    """Return structured Claude educational facts — never pass/fail."""
    mode = (settings.WRITING_EDUCATIONAL_ANALYZER or "claude").strip().lower()
    if mode == "off":
        return unavailable_claude_facts(reason="analyzer_off")
    if mode == "mock":
        return build_mock_educational_facts(draft_text, context)
    if not is_claude_configured():
        logger.info("Claude educational analyzer skipped — API key not configured; using heuristic analyzer")
        return build_mock_educational_facts(draft_text, context)

    model = claude_model_name(settings.CLAUDE_MODEL)
    user_prompt = build_analysis_prompt(draft_text=draft_text, context=context)
    try:
        raw = await generate_claude_json(
            user_prompt,
            system=SYSTEM_PROMPT,
            temperature=0.2,
            max_output_tokens=4200,
            model_name=model,
            timeout=float(settings.WRITING_GENERATION_TIMEOUT_SECONDS),
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("Claude educational analysis failed: %s", exc)
        return build_mock_educational_facts(draft_text, context)

    facts = parse_claude_educational_json(raw, model_name=model)
    if not facts.available:
        logger.warning(
            "Claude educational analyzer response unusable (%s); falling back to heuristic analyzer",
            facts.source,
        )
        return build_mock_educational_facts(draft_text, context)
    return facts
