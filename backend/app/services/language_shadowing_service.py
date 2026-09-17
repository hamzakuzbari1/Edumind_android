"""Shadowing ("repeat after me") — play a target sentence, the learner repeats it,
score how closely they matched (word similarity) and their pronunciation (Gemini).
"""

from __future__ import annotations

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, UploadFile, status

from app.models.language.analytics import LanguageAnalytics
from app.models.language.conversation import LanguageSpeakingConversationTurn
from app.models.language.enums import LanguageLevel, LanguageSkill
from app.services.language_engagement_service import record_activity
from app.services.language_learner_events import record_scored_practice
from app.services.language_pronunciation_service import assess_pronunciation, word_similarity
from app.services.language_subscription_service import get_default_language

PASS_SIMILARITY = 70
PASS_PRONUNCIATION = 70

# Curated shadowing sentences per CEFR level (kept short and natural for speaking practice).
SHADOW_SENTENCES: dict[str, list[str]] = {
    "A1": [
        "My name is Sara and I am happy.",
        "I like coffee in the morning.",
        "Where is the train station, please?",
        "This is my best friend.",
        "I have two brothers and one sister.",
    ],
    "A2": [
        "I went to the market yesterday afternoon.",
        "She is reading a very interesting book.",
        "We are going to travel next week.",
        "Could you please help me with this?",
        "The weather is nice and sunny today.",
    ],
    "B1": [
        "I have been studying English for three years.",
        "If I had more time, I would exercise every day.",
        "She told me that she was moving to another city.",
        "We should leave early to avoid the traffic.",
        "I am looking forward to meeting you next month.",
    ],
    "B2": [
        "Despite the heavy rain, the event went ahead as planned.",
        "I would rather work on a challenging project than an easy one.",
        "The committee has not yet reached a final decision.",
        "Had I known earlier, I would have prepared differently.",
        "This research highlights the importance of regular practice.",
    ],
    "C1": [
        "The proposal, although ambitious, lacks a coherent budget.",
        "Her argument was both nuanced and remarkably persuasive.",
        "We must weigh the long-term consequences before committing.",
        "The findings challenge several widely held assumptions.",
        "He articulated his concerns with admirable clarity.",
    ],
}


def _level_key(level: LanguageLevel | None) -> str:
    value = level.value if level else "A1"
    return value if value in SHADOW_SENTENCES else "A1"


async def _student_speaking_level(db: AsyncSession, *, student_id: int, language_id: int) -> LanguageLevel:
    analytics = await db.get(LanguageAnalytics, {"student_id": student_id, "language_id": language_id})
    if analytics and analytics.speaking_level:
        return analytics.speaking_level
    return LanguageLevel.A1


async def _conversation_shadow_items(db: AsyncSession, *, student_id: int, limit: int = 15) -> list[str]:
    """Corrected sentences the student produced in the AI conversation — practice your own fixes."""
    result = await db.execute(
        select(LanguageSpeakingConversationTurn.evaluation_json)
        .where(LanguageSpeakingConversationTurn.student_id == student_id)
        .order_by(desc(LanguageSpeakingConversationTurn.id))
        .limit(60)
    )
    seen: list[str] = []
    for (evaluation,) in result.all():
        if not isinstance(evaluation, dict):
            continue
        display = evaluation.get("correction_display") or {}
        if not display.get("has_errors"):
            continue
        text = (display.get("corrected_sentence") or "").strip()
        if text and text not in seen:
            seen.append(text)
        if len(seen) >= limit:
            break
    return seen


async def _focus_sentences(level: str, focus: str) -> list[str]:
    """Generate short shadowing sentences that practise a curriculum focus. [] on failure."""
    from app.core.config import get_settings
    from app.services.ai_service import generate_llm_json
    from app.services.claude_service import is_claude_configured
    from app.services.language_conversation_prompts import level_calibration_line

    settings = get_settings()
    if not is_claude_configured() or not focus.strip():
        return []
    try:
        raw = await generate_llm_json(
            f'Write 5 short, natural English sentences at CEFR {level} that practise: "{focus.strip()}".'
            + level_calibration_line(level) +
            ' Return ONLY JSON: {"sentences": [string, ...]}',
            system="You generate concise shadowing sentences for language learners.",
            temperature=0.5,
            max_output_tokens=4096,
        )
        import json
        import re

        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", (raw or "").strip())
        s, e = text.find("{"), text.rfind("}")
        data = json.loads(text[s : e + 1]) if s != -1 and e != -1 else {}
        return [str(x).strip() for x in (data.get("sentences") or []) if str(x).strip()][:5]
    except Exception:
        return []


async def list_shadow_sentences(db: AsyncSession, *, student_id: int, focus: str | None = None) -> dict:
    language = await get_default_language(db)
    level = await _student_speaking_level(db, student_id=student_id, language_id=language.id)
    key = _level_key(level)

    sentences: list[dict] = []
    idx = 1
    # Curriculum focus sentences first, when the student came here to practise a specific objective.
    if focus and focus.strip():
        for text in await _focus_sentences(key, focus):
            sentences.append({"id": idx, "text": text, "level": key, "source": "focus"})
            idx += 1
    # The student's own corrected lines from conversation come next — most relevant to practice.
    for text in await _conversation_shadow_items(db, student_id=student_id):
        sentences.append({"id": idx, "text": text, "level": key, "source": "conversation"})
        idx += 1
    for text in SHADOW_SENTENCES[key]:
        sentences.append({"id": idx, "text": text, "level": key, "source": "level"})
        idx += 1
    return {"level": key, "sentences": sentences, "focus": focus or None}


async def submit_shadow(
    db: AsyncSession, *, student_id: int, target_text: str, file: UploadFile
) -> dict:
    target = (target_text or "").strip()
    if not target:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Target sentence is required")

    data = await file.read()
    if not data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="The audio file is empty")

    suffix = ".webm"
    if file.filename and "." in file.filename:
        suffix = "." + file.filename.rsplit(".", 1)[-1].lower()

    pron = await assess_pronunciation(data, suffix=suffix, expected_text=target)
    if not pron:
        # Pronunciation engine unavailable (e.g. no Gemini key / quota) — graceful, not a hard error.
        return {
            "transcript": None,
            "similarity": 0,
            "overall_score": 0,
            "words": [],
            "weak_words": [],
            "note": "Pronunciation check is unavailable right now. Please try again.",
            "passed": False,
        }

    transcript = pron.get("transcript") or ""
    similarity = word_similarity(transcript, target)
    overall = int(pron.get("overall_score") or 0)
    passed = similarity >= PASS_SIMILARITY and overall >= PASS_PRONUNCIATION

    language = await get_default_language(db)
    await record_activity(
        db,
        student_id=student_id,
        language_id=language.id,
        event_type="shadowing_attempt",
        skill=LanguageSkill.speaking,
        duration_seconds=0,
        payload_json={"target": target, "similarity": similarity, "overall_score": overall, "passed": passed},
    )

    # Feed the unified learner model: speaking practice at the learner's speaking level (additive).
    analytics = await db.get(LanguageAnalytics, {"student_id": student_id, "language_id": language.id})
    spk_level = analytics.speaking_level if analytics and analytics.speaking_level else None
    await record_scored_practice(
        db, student_id=student_id, language_id=language.id, skill=LanguageSkill.speaking,
        level=spk_level, score_percent=float(overall), source="speaking",
    )

    return {
        "transcript": transcript,
        "similarity": similarity,
        "overall_score": overall,
        "words": pron.get("words") or [],
        "weak_words": pron.get("weak_words") or [],
        "note": pron.get("note") or "",
        "passed": passed,
    }
