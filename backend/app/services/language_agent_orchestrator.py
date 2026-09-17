"""Phase 10 — Multi-agent orchestration for a conversation turn.

Centralizes the post-turn "agents" that enrich the learner model after a reply is produced:
  - Error Intelligence (Phase 2): log this turn's mistakes.
  - Pronunciation history (Phase 6): persist the prosody scores.

Design note: these are cheap, idempotent-ish DB writes that belong in the SAME transaction as the
turn, so they run inline here (each independently guarded — one failing never breaks the turn or the
others) rather than as background tasks with a separate session. The pre-turn agent (learner-memory
context, Phase 1) runs before generation in the conversation service. Keeping them behind one
orchestrator makes the pipeline explicit and easy to extend.
"""

from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def run_post_turn_agents(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
    correction: dict | None,
    pronunciation: dict | None,
) -> None:
    """Run every post-turn enrichment agent, each isolated so one failure can't affect the others."""
    # Error Intelligence
    try:
        from app.services.language_error_intelligence_service import log_correction

        await log_correction(db, student_id=student_id, language_id=language_id, correction=correction)
    except Exception:
        logger.warning("orchestrator: error-intelligence agent failed", exc_info=True)

    # Pronunciation history
    try:
        from app.services.language_pronunciation_service import store_pronunciation_score

        await store_pronunciation_score(
            db, student_id=student_id, language_id=language_id, result=pronunciation, source="conversation"
        )
    except Exception:
        logger.warning("orchestrator: pronunciation agent failed", exc_info=True)
