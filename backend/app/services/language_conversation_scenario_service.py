"""Role-play speaking scenarios — text-based, Gemini-driven, in-character conversation.

This reuses the existing conversation session/turn tables (linked via scenario_id) but runs
a pure-text pipeline (no STT/TTS): the student types, the AI replies strictly in character.
End-of-session feedback is returned in Syrian Arabic.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.language.analytics import LanguageAnalytics
from app.models.language.conversation import (
    LanguageSpeakingConversationSession,
    LanguageSpeakingConversationTurn,
)
from app.models.language.enums import LanguageLevel
from app.models.language.scenario import LanguageConversationScenario
from app.core.ai_locale import GEMINI_LANGUAGE_RULE
from app.services.ai_service import generate_llm_json
from app.services.language_conversation_prompts import level_guidance
from app.services.language_level_utils import CEFR_RANK

logger = logging.getLogger(__name__)

HISTORY_LIMIT = 10


def _parse_json(raw: str) -> dict | None:
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", (raw or "").strip())
    s, e = text.find("{"), text.rfind("}")
    if s == -1 or e == -1:
        return None
    try:
        data = json.loads(text[s : e + 1])
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


async def _student_speaking_level(db: AsyncSession, *, student_id: int, language_id: int) -> LanguageLevel:
    analytics = await db.get(LanguageAnalytics, {"student_id": student_id, "language_id": language_id})
    if analytics and analytics.speaking_level:
        return analytics.speaking_level
    return LanguageLevel.A1


def _scenario_out(s: LanguageConversationScenario, locked: bool) -> dict:
    return {
        "id": s.id,
        "scenario_key": s.scenario_key,
        "title_en": s.title_en,
        "title_ar": s.title_ar,
        "description_en": s.description_en,
        "description_ar": s.description_ar,
        "level_min": s.level_min.value,
        "ai_role": s.ai_role,
        "student_role": s.student_role,
        "locked": locked,
    }


async def list_scenarios(db: AsyncSession, *, student_id: int, language_id: int) -> list[dict]:
    level = await _student_speaking_level(db, student_id=student_id, language_id=language_id)
    rank = CEFR_RANK[level]
    result = await db.execute(
        select(LanguageConversationScenario)
        .where(
            LanguageConversationScenario.language_id == language_id,
            LanguageConversationScenario.is_active.is_(True),
        )
        .order_by(LanguageConversationScenario.sort_order, LanguageConversationScenario.id)
    )
    return [_scenario_out(s, CEFR_RANK[s.level_min] > rank) for s in result.scalars().all()]


async def start_scenario_session(db: AsyncSession, *, student_id: int, language_id: int, scenario_id: int) -> dict:
    scenario = await db.get(LanguageConversationScenario, scenario_id)
    if not scenario or not scenario.is_active or scenario.language_id != language_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scenario not found")

    level = await _student_speaking_level(db, student_id=student_id, language_id=language_id)
    if CEFR_RANK[scenario.level_min] > CEFR_RANK[level]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"This scenario needs level {scenario.level_min.value} or higher.",
        )

    # Close any existing active SCENARIO session for this learner (one role-play at a time).
    # Never touch the free-chat conversation session — they are independent features now.
    now = datetime.now(timezone.utc)
    active = await db.execute(
        select(LanguageSpeakingConversationSession).where(
            LanguageSpeakingConversationSession.student_id == student_id,
            LanguageSpeakingConversationSession.language_id == language_id,
            LanguageSpeakingConversationSession.status == "active",
            LanguageSpeakingConversationSession.scenario_id.is_not(None),
        )
    )
    for sess in active.scalars().all():
        sess.status = "ended"
        sess.ended_at = now

    session = LanguageSpeakingConversationSession(
        student_id=student_id,
        language_id=language_id,
        status="active",
        scenario_id=scenario.id,
        effective_level_at_start=level,
        turn_count=0,
    )
    db.add(session)
    await db.flush()
    return {
        "session_id": session.id,
        "scenario": _scenario_out(scenario, False),
        "opening_line": scenario.opening_line,
        "ai_role": scenario.ai_role,
        "student_role": scenario.student_role,
    }


async def _load_scenario_session(
    db: AsyncSession, *, session_id: int, student_id: int
) -> tuple[LanguageSpeakingConversationSession, LanguageConversationScenario]:
    session = await db.get(LanguageSpeakingConversationSession, session_id)
    if not session or session.student_id != student_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    if not session.scenario_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This session is not a scenario session")
    scenario = await db.get(LanguageConversationScenario, session.scenario_id)
    if not scenario:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scenario not found")
    return session, scenario


async def get_scenario_session(db: AsyncSession, *, session_id: int, student_id: int) -> dict:
    session, scenario = await _load_scenario_session(db, session_id=session_id, student_id=student_id)

    turns_result = await db.execute(
        select(LanguageSpeakingConversationTurn)
        .where(LanguageSpeakingConversationTurn.session_id == session.id)
        .order_by(LanguageSpeakingConversationTurn.turn_index)
    )
    turns = list(turns_result.scalars().all())

    messages: list[dict] = [{"role": "assistant", "text": scenario.opening_line}]
    for t in turns:
        if t.user_transcript:
            messages.append({"role": "user", "text": t.user_transcript})
        if t.assistant_reply:
            messages.append({"role": "assistant", "text": t.assistant_reply})

    return {
        "session_id": session.id,
        "status": session.status,
        "scenario": _scenario_out(scenario, False),
        "messages": messages,
        "turn_count": int(session.turn_count or 0),
        "summary": session.summary_json,
    }


async def list_scenario_sessions(db: AsyncSession, *, student_id: int, language_id: int) -> dict:
    """Past role-play scenario sessions (newest first) for the history view."""
    result = await db.execute(
        select(LanguageSpeakingConversationSession)
        .where(
            LanguageSpeakingConversationSession.student_id == student_id,
            LanguageSpeakingConversationSession.language_id == language_id,
            LanguageSpeakingConversationSession.scenario_id.is_not(None),
        )
        .order_by(LanguageSpeakingConversationSession.started_at.desc())
    )
    sessions = list(result.scalars().all())
    scenario_ids = {s.scenario_id for s in sessions if s.scenario_id}
    titles: dict[int, dict] = {}
    if scenario_ids:
        srows = await db.execute(
            select(LanguageConversationScenario).where(LanguageConversationScenario.id.in_(scenario_ids))
        )
        for sc in srows.scalars().all():
            titles[sc.id] = {"title_en": sc.title_en, "title_ar": sc.title_ar}
    out = []
    for s in sessions:
        summary = s.summary_json or {}
        meta = titles.get(s.scenario_id, {})
        out.append(
            {
                "session_id": s.id,
                "scenario_id": s.scenario_id,
                "title_en": meta.get("title_en"),
                "title_ar": meta.get("title_ar"),
                "status": s.status,
                "turn_count": int(s.turn_count or 0),
                "started_at": s.started_at,
                "ended_at": s.ended_at,
                "goal_achieved": summary.get("goal_achieved"),
                "estimated_cefr": summary.get("estimated_cefr"),
            }
        )
    return {"sessions": out}


async def process_scenario_turn(
    db: AsyncSession, *, session_id: int, student_id: int, user_text: str, language_id: int
) -> dict:
    session, scenario = await _load_scenario_session(db, session_id=session_id, student_id=student_id)
    user_text = (user_text or "").strip()
    if not user_text:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Your message is empty")

    level = await _student_speaking_level(db, student_id=student_id, language_id=language_id)

    history_result = await db.execute(
        select(LanguageSpeakingConversationTurn)
        .where(LanguageSpeakingConversationTurn.session_id == session.id)
        .order_by(LanguageSpeakingConversationTurn.turn_index.desc())
        .limit(HISTORY_LIMIT)
    )
    recent = list(reversed(history_result.scalars().all()))

    # Reuse the SAME CEFR level guidance as the main conversation tutor so vocabulary
    # selection and reply shape stay consistent across conversation and role-play scenarios.
    system = (
        f"You are {scenario.ai_role}. The student is {scenario.student_role}.\n"
        f"Scenario context: {scenario.title_en} — {scenario.description_en}\n"
        "Stay strictly in character — never break role, never explain grammar, never switch to Arabic.\n"
        "Drive the role-play forward like a real person: react naturally to what the student says, ask "
        "realistic follow-up questions, and introduce small, believable developments or complications so "
        "the student has to respond and adapt. Keep the scene moving toward its natural goal; never end it "
        "abruptly and never answer on the student's behalf.\n"
        f"Student effective CEFR level: {level.value}.\n"
        f"Level guidance — match your vocabulary, grammar, and reply length to this: "
        f"{level_guidance(level.value)}\n"
        f"{GEMINI_LANGUAGE_RULE}\n"
        'Return ONLY JSON: {"reply": "<your in-character reply>"}'
    )

    lines = [f"Scenario opening: {scenario.opening_line}"]
    for t in recent:
        if t.user_transcript:
            lines.append(f"Student: {t.user_transcript}")
        if t.assistant_reply:
            lines.append(f"You: {t.assistant_reply}")
    lines.append(f"Student: {user_text}")
    lines.append("Reply in character as JSON now.")
    prompt = "\n".join(lines)

    raw = await generate_llm_json(prompt, system=system, temperature=0.6, max_output_tokens=512)
    parsed = _parse_json(raw)
    reply = ""
    if parsed:
        reply = str(parsed.get("reply") or "").strip()
    if not reply:
        reply = "Sorry, could you say that again, please?"

    turn_index = int(session.turn_count or 0) + 1
    turn = LanguageSpeakingConversationTurn(
        session_id=session.id,
        student_id=student_id,
        turn_index=turn_index,
        user_transcript=user_text,
        assistant_reply=reply,
        scoring_version="scenario_v1",
    )
    db.add(turn)
    session.turn_count = turn_index
    await db.flush()
    return {"turn_index": turn_index, "assistant_reply": reply, "session_id": session.id}


async def end_session_with_feedback(db: AsyncSession, *, session_id: int, student_id: int) -> dict:
    session, scenario = await _load_scenario_session(db, session_id=session_id, student_id=student_id)

    turns_result = await db.execute(
        select(LanguageSpeakingConversationTurn)
        .where(LanguageSpeakingConversationTurn.session_id == session.id)
        .order_by(LanguageSpeakingConversationTurn.turn_index)
    )
    turns = list(turns_result.scalars().all())

    start_level = session.effective_level_at_start.value if session.effective_level_at_start else "A1"
    fallback = {
        "scores": {"task_completion": 0, "fluency": 0, "grammar": 0, "vocabulary": 0, "interaction": 0},
        "goal_achieved": False,
        "goal_note": "Not enough conversation to judge — try completing the scenario.",
        "overall_impression": "You finished the scenario! Keep practising to get stronger.",
        "strengths": ["You took part in the conversation", "You tried to use English"],
        "errors": [],
        "vocabulary_suggestions": [],
        "estimated_cefr": start_level,
        "cefr_note": "",
        "next_focus": "Have a few more turns so we can assess your level accurately.",
        "encouragement": "Keep going — you're improving step by step!",
    }

    if turns:
        transcript_lines = []
        for t in turns:
            if t.user_transcript:
                transcript_lines.append(f"Student: {t.user_transcript}")
            if t.assistant_reply:
                transcript_lines.append(f"{scenario.ai_role}: {t.assistant_reply}")
        transcript = "\n".join(transcript_lines)

        system = (
            "You are a strict but encouraging English-speaking examiner reviewing a role-play. "
            f"Scenario: {scenario.title_en} — {scenario.description_en}. "
            f"The student played {scenario.student_role} talking to {scenario.ai_role}. "
            f"The student's CEFR level coming in was {start_level}. "
            "Judge ONLY the student's English (the 'Student:' lines), and be specific and grounded in what "
            "they actually said — quote their real words in corrections. Score each dimension 0-100. "
            "task_completion = did they accomplish the scenario's goal; interaction = how well they kept the "
            "conversation going and responded appropriately. Write ALL text in clear, encouraging English. "
            f"{GEMINI_LANGUAGE_RULE} "
            "Return ONLY JSON with this exact shape (field names are fixed; their content must be English): "
            '{"scores": {"task_completion": 0-100, "fluency": 0-100, "grammar": 0-100, "vocabulary": 0-100, "interaction": 0-100}, '
            '"goal_achieved": true|false, "goal_note": str, '
            '"overall_impression": str, '
            '"strengths": [str, str], '
            '"errors": [{"original": str, "corrected": str, "explanation_ar": str}], '
            '"vocabulary_suggestions": [str], '
            '"estimated_cefr": "A1|A2|B1|B2|C1|C2", "cefr_note": str, '
            '"next_focus": str, "encouragement": str}'
        )
        raw = await generate_llm_json(
            f"Conversation transcript:\n{transcript}\n\nWrite the detailed feedback JSON now.",
            system=system,
            temperature=0.4,
            max_output_tokens=3072,
        )
        parsed = _parse_json(raw)
        feedback = {**fallback, **parsed} if parsed else fallback
    else:
        feedback = fallback

    session.summary_json = feedback
    session.status = "ended"
    session.ended_at = datetime.now(timezone.utc)
    await db.flush()
    # XP once per scenario (not per session) so replaying the same scenario can't farm XP;
    # require a real exchange (>= 2 turns) so an instantly-ended scenario earns nothing.
    if len(turns) >= 2:
        from app.services.language_xp_service import award_language_xp
        from app.services.language_learner_events import record_speaking_scores

        await award_language_xp(
            db, student_id=student_id, language_id=session.language_id,
            activity="scenario", key=f"scenario:{session.scenario_id}",
        )
        # Feed the unified learner model with this role-play's speaking evidence (additive).
        await record_speaking_scores(
            db, student_id=student_id, language_id=session.language_id,
            level=feedback.get("estimated_cefr") or start_level, scores=feedback.get("scores"),
            source="speaking",
        )
    return feedback
