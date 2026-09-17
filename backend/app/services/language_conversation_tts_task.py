"""Background reply TTS for AI conversation — does not block the turn HTTP response."""

from __future__ import annotations

import logging
import time

from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.language.conversation import LanguageSpeakingConversationTurn
from app.services.language_reply_tts_service import synthesize_english_reply

logger = logging.getLogger(__name__)


async def generate_conversation_reply_audio(
    *,
    turn_id: int,
    student_id: int,
    segments: list[dict],
    voice: str | None = None,
) -> None:
    """Synthesize reply audio and attach MediaObject to the turn (runs after HTTP response)."""
    started = time.perf_counter()
    async with AsyncSessionLocal() as db:
        try:
            result = await db.execute(
                select(LanguageSpeakingConversationTurn).where(
                    LanguageSpeakingConversationTurn.id == turn_id,
                    LanguageSpeakingConversationTurn.student_id == student_id,
                )
            )
            turn = result.scalar_one_or_none()
            if not turn:
                logger.warning("Background TTS: turn %s not found", turn_id)
                return
            if turn.reply_media_object_id:
                logger.info("Background TTS: turn %s already has audio", turn_id)
                return

            reply_media = await synthesize_english_reply(
                db,
                student_id=student_id,
                segments=segments,
                voice=voice,
            )
            if reply_media:
                turn.reply_media_object_id = reply_media.id
                eval_json = dict(turn.evaluation_json or {})
                eval_json["reply_audio_pending"] = False
                turn.evaluation_json = eval_json
                await db.commit()
                logger.info(
                    "Background TTS ok turn_id=%s duration_s=%.2f url=%s",
                    turn_id,
                    time.perf_counter() - started,
                    reply_media.public_url,
                )
            else:
                eval_json = dict(turn.evaluation_json or {})
                eval_json["reply_audio_pending"] = False
                turn.evaluation_json = eval_json
                await db.commit()
                logger.warning(
                    "Background TTS skipped turn_id=%s duration_s=%.2f",
                    turn_id,
                    time.perf_counter() - started,
                )
        except Exception as exc:
            try:
                result = await db.execute(
                    select(LanguageSpeakingConversationTurn).where(
                        LanguageSpeakingConversationTurn.id == turn_id,
                    )
                )
                turn = result.scalar_one_or_none()
                if turn:
                    eval_json = dict(turn.evaluation_json or {})
                    eval_json["reply_audio_pending"] = False
                    turn.evaluation_json = eval_json
                    await db.commit()
            except Exception:
                pass
            logger.warning(
                "Background TTS failed turn_id=%s duration_s=%.2f error=%s",
                turn_id,
                time.perf_counter() - started,
                exc,
            )
