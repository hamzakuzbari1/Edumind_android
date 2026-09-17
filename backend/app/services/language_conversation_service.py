"""AI speaking conversation — session lifecycle and turn pipeline."""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timezone
from io import BytesIO

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.language.analytics import LanguageAnalytics
from app.models.language.conversation import LanguageSpeakingConversationSession, LanguageSpeakingConversationTurn
from app.models.language.enums import LanguageLevel, LanguageSkill
from app.models.media import MediaObject
from app.services.language_conversation_ai_service import generate_conversation_turn
from app.services.language_conversation_correction import (
    build_correction_display,
    build_spoken_segments,
    resolve_correction_display,
)
from app.services.language_engagement_service import record_activity
from app.services.language_learner_events import record_speaking_scores
from app.services.language_grammar_service import analyze_grammar
from app.services.language_media_service import upload_student_speaking
from app.services.language_reply_tts_service import synthesize_english_reply
from app.services.language_speaking_evolution_service import (
    build_conversation_progress,
    update_speaking_level_from_conversation,
)
from app.services.language_subscription_service import get_default_language
from app.services.language_transcription_service import transcribe_english_audio

logger = logging.getLogger(__name__)
settings = get_settings()

WELCOME_HINT = "Speak in English — I will correct your mistakes and respond to you at a level that suits you."


def _rate_score(wpm: float) -> int:
    """Speaking rate (words/minute) → 0-100. Natural conversational band ≈ 90-160 wpm."""
    if wpm <= 0:
        return 0
    if wpm < 50:
        return 45
    if wpm < 90:
        return 70
    if wpm <= 160:
        return 100
    if wpm <= 200:
        return 80
    return 60


def _stt_confidence(stt_meta: dict) -> int:
    """Map Whisper avg_logprob (~ -1.0 poor .. 0 great) to 0-100; honour the low_confidence flag."""
    lp = stt_meta.get("avg_logprob")
    if lp is None:
        conf = 70  # neutral when the engine gives no logprob (e.g. Gemini STT)
    else:
        conf = max(0, min(100, round((float(lp) + 1.0) * 100)))
    if stt_meta.get("low_confidence"):
        conf = min(conf, 55)
    return conf


def _audio_grounded_scores(
    *, transcript: str, duration_seconds: int | None, pronunciation: dict | None, stt_meta: dict, ai_scores: dict
) -> dict:
    """Blend objective audio signals into the headline scores.

    - fluency  ← speaking rate + pronunciation + STT confidence (real audio, not a text guess)
    - pronunciation ← the audio pronunciation assessment
    - grammar / vocabulary ← kept from the text analysis (appropriate there)
    - confidence ← blend of the AI's read and STT confidence
    Falls back to the AI scores when no usable audio signal exists.
    """
    scores = dict(ai_scores or {})
    words = len((transcript or "").split())
    dur = int(duration_seconds or 0)
    pron = pronunciation.get("overall_score") if isinstance(pronunciation, dict) else None
    stt_conf = _stt_confidence(stt_meta or {})

    have_audio = bool(pron is not None or (dur > 0 and words > 0))
    if not have_audio:
        return scores

    parts: list[int] = [stt_conf]
    if dur > 0 and words > 0:
        parts.append(_rate_score(words / dur * 60))
    if pron is not None:
        parts.append(int(pron))
    scores["fluency"] = round(sum(parts) / len(parts))
    if pron is not None:
        scores["pronunciation"] = int(pron)
    ai_conf = scores.get("confidence")
    scores["confidence"] = round(((ai_conf if isinstance(ai_conf, (int, float)) else stt_conf) + stt_conf) / 2)
    return scores


async def _effective_level(db: AsyncSession, *, student_id: int, language_id: int) -> str:
    analytics = await db.get(LanguageAnalytics, {"student_id": student_id, "language_id": language_id})
    if analytics and analytics.speaking_level:
        return analytics.speaking_level.value
    return LanguageLevel.A1.value


async def _get_or_create_active_session(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
) -> LanguageSpeakingConversationSession:
    result = await db.execute(
        select(LanguageSpeakingConversationSession)
        .where(
            LanguageSpeakingConversationSession.student_id == student_id,
            LanguageSpeakingConversationSession.language_id == language_id,
            LanguageSpeakingConversationSession.status == "active",
            # Free-chat conversation only — never pick up a role-play scenario session.
            LanguageSpeakingConversationSession.scenario_id.is_(None),
        )
        .order_by(desc(LanguageSpeakingConversationSession.started_at))
        .limit(1)
    )
    session = result.scalar_one_or_none()
    if session:
        return session

    level_str = await _effective_level(db, student_id=student_id, language_id=language_id)
    try:
        level_enum = LanguageLevel(level_str)
    except ValueError:
        level_enum = LanguageLevel.A1

    session = LanguageSpeakingConversationSession(
        student_id=student_id,
        language_id=language_id,
        status="active",
        effective_level_at_start=level_enum,
        turn_count=0,
    )
    db.add(session)
    await db.flush()
    return session


async def get_conversation_state(db: AsyncSession, *, student_id: int) -> dict:
    language = await get_default_language(db)
    session = await _get_or_create_active_session(db, student_id=student_id, language_id=language.id)
    result = await db.execute(
        select(LanguageSpeakingConversationTurn)
        .where(LanguageSpeakingConversationTurn.session_id == session.id)
        .order_by(LanguageSpeakingConversationTurn.turn_index)
    )
    turns = list(result.scalars().all())

    messages: list[dict] = []
    for turn in turns:
        user_eval = turn.evaluation_json or {}
        messages.append(
            {
                "role": "user",
                "content": turn.user_transcript,
                "turn_index": turn.turn_index,
                "evaluation": user_eval,
                "reply_audio_url": None,
            }
        )
        reply_url = None
        if turn.reply_media_object_id:
            media = await db.get(MediaObject, turn.reply_media_object_id)
            reply_url = media.public_url if media else None
        correction_display = resolve_correction_display(user_eval)
        audio_pending = bool(user_eval.get("reply_audio_pending")) and not reply_url
        messages.append(
            {
                "role": "assistant",
                "content": turn.assistant_reply,
                "turn_index": turn.turn_index,
                "turn_db_id": turn.id,
                "evaluation": None,
                "correction_display": correction_display,
                "reply_audio_url": reply_url,
                "reply_audio_pending": audio_pending,
            }
        )

    effective = await _effective_level(db, student_id=student_id, language_id=language.id)
    return {
        "session_id": session.id,
        "effective_speaking_level": effective,
        "turn_count": session.turn_count,
        "messages": messages,
        "welcome_hint": WELCOME_HINT if not turns else None,
    }


async def process_conversation_turn(
    db: AsyncSession,
    *,
    student_id: int,
    file: UploadFile,
    duration_seconds: int | None = None,
    voice: str | None = None,
    focus: str | None = None,
) -> dict:
    turn_started = time.perf_counter()
    timing_ms: dict[str, int] = {}

    language = await get_default_language(db)
    session = await _get_or_create_active_session(db, student_id=student_id, language_id=language.id)
    effective = await _effective_level(db, student_id=student_id, language_id=language.id)

    upload_started = time.perf_counter()
    data = await file.read()
    if not data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="The audio file is empty")

    upload_file = UploadFile(
        filename=file.filename or "speech.webm",
        file=BytesIO(data),
        headers={"content-type": file.content_type or "audio/webm"},
    )
    user_media = await upload_student_speaking(
        db,
        student_id=student_id,
        subfolder="language_conversation",
        filename_hint=f"turn_{session.turn_count + 1}",
        file=upload_file,
    )
    timing_ms["upload"] = int((time.perf_counter() - upload_started) * 1000)

    suffix = ".webm"
    if file.filename and "." in file.filename:
        suffix = "." + file.filename.rsplit(".", 1)[-1].lower()

    whisper_started = time.perf_counter()
    stt = await transcribe_english_audio(data, suffix=suffix)
    transcript = stt.text
    timing_ms["whisper"] = int((time.perf_counter() - whisper_started) * 1000)

    grammar_started = time.perf_counter()
    grammar = analyze_grammar(transcript)
    grammar_hints = grammar.get("errors") or []
    timing_ms["grammar"] = int((time.perf_counter() - grammar_started) * 1000)

    history_result = await db.execute(
        select(LanguageSpeakingConversationTurn)
        .where(LanguageSpeakingConversationTurn.session_id == session.id)
        .order_by(LanguageSpeakingConversationTurn.turn_index)
    )
    prior_turns = list(history_result.scalars().all())
    history = []
    for t in prior_turns:
        history.append({"role": "user", "content": t.user_transcript})
        history.append({"role": "assistant", "content": t.assistant_reply})

    from app.services.language_pronunciation_service import assess_pronunciation

    # Phase 1 — inject the learner-memory snapshot before the existing prompt (never replacing it).
    # Best-effort: a memory lookup must never break a conversation turn.
    try:
        from app.services.language_learner_memory_service import get_prompt_context

        memory_context = await get_prompt_context(db, student_id=student_id, language_id=language.id)
    except Exception:
        logger.warning("learner-memory context lookup failed", exc_info=True)
        memory_context = ""

    gemini_started = time.perf_counter()
    # Conversation turn (text) and pronunciation assessment (audio) run concurrently —
    # pronunciation adds no serial latency to the turn.
    ai_result, pronunciation = await asyncio.gather(
        generate_conversation_turn(
            transcript=transcript,
            effective_level=effective,
            grammar_hints=grammar_hints,
            history=history,
            focus=focus,
            memory_context=memory_context,
        ),
        assess_pronunciation(data, suffix=suffix),
    )
    timing_ms["gemini"] = int((time.perf_counter() - gemini_started) * 1000)

    reply_text = ai_result.get("reply") or ""
    follow_up = ai_result.get("follow_up")
    if follow_up:
        reply_text = f"{reply_text} {follow_up}".strip()

    correction_raw = ai_result.get("correction") or {}
    correction_display = build_correction_display(correction_raw)
    # Tag mispronounced words onto the correction so the UI can colour them yellow (vs grammar red).
    if isinstance(correction_display, dict) and correction_display.get("has_errors"):
        weak = [
            w.get("word")
            for w in (pronunciation or {}).get("words", [])
            if isinstance(w, dict) and w.get("weak") and w.get("word")
        ]
        if weak:
            correction_display = {**correction_display, "weak_words": weak}
    spoken_segments = build_spoken_segments(
        correction_display=correction_display,
        conversation_reply=reply_text,
    )

    # Phase 10 — run the post-turn enrichment agents (error intelligence + pronunciation history)
    # through one orchestrator; each is isolated so a failure never breaks the turn.
    from app.services.language_agent_orchestrator import run_post_turn_agents

    await run_post_turn_agents(
        db, student_id=student_id, language_id=language.id,
        correction=correction_raw, pronunciation=pronunciation,
    )

    async_tts = bool(settings.LANGUAGE_CONVERSATION_ASYNC_TTS and settings.ENABLE_TTS and spoken_segments)
    reply_media = None
    if not async_tts and spoken_segments:
        tts_started = time.perf_counter()
        reply_media = await synthesize_english_reply(
            db, student_id=student_id, segments=spoken_segments, voice=voice
        )
        timing_ms["tts"] = int((time.perf_counter() - tts_started) * 1000)

    stt_meta = {
        "engine": stt.engine,
        "model": stt.model,
        "raw_text": stt.raw_text,
        "avg_logprob": stt.avg_logprob,
        "no_speech_prob": stt.no_speech_prob,
        "language_probability": stt.language_probability,
        "low_confidence": stt.low_confidence,
    }
    # Ground the headline scores in real audio (rate + pronunciation + STT confidence),
    # not just a text guess; grammar/vocabulary stay from the text analysis.
    grounded_scores = _audio_grounded_scores(
        transcript=transcript,
        duration_seconds=duration_seconds,
        pronunciation=pronunciation,
        stt_meta=stt_meta,
        ai_scores=ai_result.get("scores") or {},
    )

    evaluation = {
        "correction": correction_raw,
        "correction_display": correction_display,
        "scores": grounded_scores,
        "pronunciation": pronunciation,
        "estimated_cefr": ai_result.get("estimated_cefr"),
        "coaching_note_ar": ai_result.get("coaching_note_ar"),
        "grammar_tool_used": grammar.get("available", False),
        "topic": ai_result.get("topic"),
        "reply_audio_pending": async_tts and not reply_media,
        "stt": stt_meta,
    }

    turn_index = session.turn_count + 1
    try:
        estimated = LanguageLevel(evaluation["estimated_cefr"])
    except (ValueError, TypeError):
        estimated = LanguageLevel(effective)

    turn = LanguageSpeakingConversationTurn(
        session_id=session.id,
        student_id=student_id,
        turn_index=turn_index,
        user_transcript=transcript,
        assistant_reply=reply_text,
        user_media_object_id=user_media.id,
        reply_media_object_id=reply_media.id if reply_media else None,
        duration_seconds=duration_seconds,
        evaluation_json=evaluation,
        estimated_cefr=estimated,
    )
    db.add(turn)
    session.turn_count = turn_index
    await db.flush()

    new_level, level_changed = await update_speaking_level_from_conversation(
        db, student_id=student_id, language_id=language.id
    )
    # Note: conversation earns XP only via the daily mission ("have a conversation" task),
    # so the learner can keep chatting freely for practice without farming XP.

    # Feed the unified learner model (additive; the headline speaking level is handled above).
    await record_speaking_scores(
        db, student_id=student_id, language_id=language.id,
        level=estimated, scores=grounded_scores, source="speaking",
    )

    # Real conversation is genuine speaking practice — let a solid turn credit the speaking
    # curriculum objectives (the only way "conversation" objectives reach mastery now that the
    # manual Practice tap no longer masters anything).
    try:
        from app.services.language_curriculum_service import credit_skill_objectives

        # Credit objectives on LANGUAGE quality (grammar + vocabulary), not the overall mean — fluency
        # and STT-confidence default high (~70) for any normal-paced speech and would otherwise let a
        # grammatically weak turn count as a pass.
        _lang = [grounded_scores.get(k) for k in ("grammar", "vocabulary") if isinstance(grounded_scores.get(k), (int, float))]
        _conv_score = sum(_lang) / len(_lang) if _lang else 0.0
        await credit_skill_objectives(
            db, student_id=student_id, language_id=language.id, skill=LanguageSkill.speaking,
            score_percent=_conv_score, passed=_conv_score >= 60.0,
        )
    except Exception:  # never let curriculum crediting break a conversation turn
        logger.warning("conversation objective crediting failed", exc_info=True)

    await record_activity(
        db,
        student_id=student_id,
        language_id=language.id,
        event_type="speaking_conversation_turn",
        skill=LanguageSkill.speaking,
        duration_seconds=int(duration_seconds or 0),
        payload_json={
            "session_id": session.id,
            "turn_index": turn_index,
            "estimated_cefr": evaluation.get("estimated_cefr"),
            "scores": evaluation.get("scores"),
        },
    )

    timing_ms["total"] = int((time.perf_counter() - turn_started) * 1000)
    logger.info(
        "Conversation turn timing_ms session=%s turn=%s upload=%s whisper=%s grammar=%s gemini=%s total=%s async_tts=%s",
        session.id,
        turn_index,
        timing_ms.get("upload"),
        timing_ms.get("whisper"),
        timing_ms.get("grammar"),
        timing_ms.get("gemini"),
        timing_ms.get("total"),
        async_tts,
    )

    result = {
        "session_id": session.id,
        "turn_id": turn.id,
        "turn_index": turn_index,
        "transcript": transcript,
        "evaluation": evaluation,
        "correction_display": correction_display,
        "reply": reply_text,
        "reply_audio_url": reply_media.public_url if reply_media else None,
        "reply_audio_pending": async_tts and not reply_media,
        "effective_speaking_level": new_level.value if new_level else effective,
        "level_changed": level_changed,
        "timing_ms": timing_ms,
    }
    if async_tts:
        result["_background_tts"] = {
            "turn_id": turn.id,
            "student_id": student_id,
            "segments": spoken_segments,
            "voice": voice,
        }
    return result


async def reset_conversation(db: AsyncSession, *, student_id: int) -> dict:
    language = await get_default_language(db)
    result = await db.execute(
        select(LanguageSpeakingConversationSession).where(
            LanguageSpeakingConversationSession.student_id == student_id,
            LanguageSpeakingConversationSession.language_id == language.id,
            LanguageSpeakingConversationSession.status == "active",
            # Reset only the free-chat conversation — leave role-play scenario sessions alone.
            LanguageSpeakingConversationSession.scenario_id.is_(None),
        )
    )
    now = datetime.now(timezone.utc)
    from app.services.language_learner_memory_service import summarize_session

    for session in result.scalars().all():
        session.status = "completed"
        session.ended_at = now
        # Phase 1 — store a cheap session summary so it can feed the learner-memory context next time.
        try:
            await summarize_session(db, session_id=session.id)
        except Exception:
            logger.warning("session summarization failed for session=%s", session.id, exc_info=True)
    await db.flush()
    return {"ok": True}


async def get_conversation_progress(db: AsyncSession, *, student_id: int) -> dict:
    language = await get_default_language(db)
    return await build_conversation_progress(db, student_id=student_id, language_id=language.id)


async def list_conversation_sessions(db: AsyncSession, *, student_id: int) -> dict:
    """Past free-chat conversation sessions (newest first) for the history view."""
    language = await get_default_language(db)
    result = await db.execute(
        select(LanguageSpeakingConversationSession)
        .where(
            LanguageSpeakingConversationSession.student_id == student_id,
            LanguageSpeakingConversationSession.language_id == language.id,
            LanguageSpeakingConversationSession.scenario_id.is_(None),
        )
        .order_by(desc(LanguageSpeakingConversationSession.started_at))
    )
    sessions = []
    for s in result.scalars().all():
        sessions.append(
            {
                "session_id": s.id,
                "status": s.status,
                "turn_count": int(s.turn_count or 0),
                "level_at_start": s.effective_level_at_start.value if s.effective_level_at_start else None,
                "started_at": s.started_at,
                "ended_at": s.ended_at,
            }
        )
    return {"sessions": sessions}


async def get_conversation_session_detail(db: AsyncSession, *, student_id: int, session_id: int) -> dict:
    """Full transcript + corrections of one past conversation session."""
    session = await db.get(LanguageSpeakingConversationSession, session_id)
    if not session or session.student_id != student_id or session.scenario_id is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    result = await db.execute(
        select(LanguageSpeakingConversationTurn)
        .where(LanguageSpeakingConversationTurn.session_id == session.id)
        .order_by(LanguageSpeakingConversationTurn.turn_index)
    )
    turns = []
    for t in result.scalars().all():
        ev = t.evaluation_json or {}
        turns.append(
            {
                "turn_index": t.turn_index,
                "you": t.user_transcript,
                "reply": t.assistant_reply,
                "correction_display": ev.get("correction_display"),
                "scores": ev.get("scores"),
                "estimated_cefr": t.estimated_cefr.value if t.estimated_cefr else None,
            }
        )
    return {
        "session_id": session.id,
        "status": session.status,
        "level_at_start": session.effective_level_at_start.value if session.effective_level_at_start else None,
        "started_at": session.started_at,
        "ended_at": session.ended_at,
        "turns": turns,
    }


async def get_turn_explanation(db: AsyncSession, *, student_id: int, turn_id: int) -> dict:
    """On-demand detailed explanation of a turn's correction (ported from the speaking coach).

    Generated lazily on the first request and cached on the turn's evaluation_json, so it
    adds no latency to the turn itself and is produced only when the learner taps "Explain".
    """
    turn = await db.get(LanguageSpeakingConversationTurn, turn_id)
    if not turn or turn.student_id != student_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Turn not found")

    eval_json = dict(turn.evaluation_json or {})
    cached = eval_json.get("detailed_explanation")
    if cached is not None:
        return {"turn_id": turn_id, "explanation": cached, "ready": True}

    correction = eval_json.get("correction") or {}
    original = (correction.get("original") or turn.user_transcript or "").strip()
    corrected = (correction.get("corrected") or "").strip()
    has_errors = bool(correction.get("has_errors")) and corrected and corrected != original

    if not has_errors:
        text = ""
    else:
        from app.services.language_conversation_ai_service import generate_correction_explanation

        # Use the student's effective speaking level (same source the conversation turn used),
        # so the explanation's vocabulary and depth match how the AI talks to this learner.
        language = await get_default_language(db)
        level = await _effective_level(db, student_id=student_id, language_id=language.id)
        text = await generate_correction_explanation(
            original=original, corrected=corrected, effective_level=level
        )

    eval_json["detailed_explanation"] = text
    turn.evaluation_json = eval_json  # reassign so SQLAlchemy detects the JSON change
    await db.flush()
    return {"turn_id": turn_id, "explanation": text, "ready": True}
