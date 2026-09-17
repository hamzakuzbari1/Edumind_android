"""Speaking Coach — structured feedback, retry challenge, and attempt comparison."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from app.core.config import get_settings
from app.services.ai_service import generate_llm_json
from app.services.claude_service import is_claude_configured

logger = logging.getLogger(__name__)
settings = get_settings()

_COACH_SYSTEM = (
    "You are an English speaking coach helping Arabic-speaking learners. "
    "Given the learner's transcript, grammar correction, score, and CEFR estimate, "
    "produce actionable coaching. Be concise and encouraging. "
    "Return ONLY JSON with these keys:\n"
    "  what_was_good (string, English),\n"
    "  biggest_mistake (string, English),\n"
    "  better_version (string, English — full corrected sentence),\n"
    "  pronunciation_tip (string, English — one tip),\n"
    "  fluency_tip (string, English — one tip),\n"
    "  grammar_tip (string, English — one tip),\n"
    "  retry_sentence (string, English — ONE short sentence the learner should record again),\n"
    "  coach_feedback (string, English — 2-3 sentence summary),\n"
    "  coach_feedback_ar (string, Arabic — same summary for the learner)"
)


def _parse_json(raw: str) -> dict | None:
    text = (raw or "").strip()
    if not text:
        return None
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        return None
    try:
        return json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return None


def _fluency_proxy(*, criteria: dict | None, duration_seconds: int | None, word_count: int) -> float:
    if criteria and criteria.get("fluency_coherence") is not None:
        return float(criteria["fluency_coherence"])
    duration = int(duration_seconds or 0)
    if duration <= 0 or word_count <= 0:
        return 40.0
    wpm = word_count / max(duration / 60.0, 0.1)
    return round(min(100.0, max(20.0, 30.0 + wpm * 4)), 1)


def _word_count(text: str) -> int:
    return len(re.findall(r"[A-Za-z']+", text or ""))


def _fallback_coach(
    *,
    transcript: str,
    corrected_text: str,
    errors: list,
    score_percent: float,
    estimated_cefr: str | None,
    prompt_text: str,
) -> dict[str, str]:
    corrected = (corrected_text or transcript or "").strip()
    has_errors = bool(errors) or (
        corrected.lower() != (transcript or "").strip().lower() and bool(transcript)
    )

    if score_percent >= 82:
        good = "Clear delivery and good task coverage."
    elif score_percent >= 55:
        good = "You communicated the main idea — keep building from here."
    else:
        good = "Good effort speaking in English — every attempt builds fluency."

    if errors:
        biggest = str(errors[0].get("message") or errors[0].get("type") or "Check verb tense and sentence structure.")
    elif has_errors:
        biggest = "Verb tense or missing words (e.g. 'to', articles)."
    else:
        biggest = "Minor polish — focus on natural word stress."

    better = corrected or transcript or prompt_text or "I went to school yesterday."
    retry = better if len(better.split()) <= 12 else " ".join(better.split()[:10])

    pron_tip = "Stress the main verb and end the sentence with clear falling intonation."
    fluency_tip = "Pause briefly at commas; don't rush multi-word phrases."
    grammar_tip = (
        "Use past tense for finished actions: went, not go."
        if re.search(r"\b(go|goes)\b", transcript or "", re.I)
        else "Check subject–verb agreement and articles (a/the)."
    )

    feedback_en = (
        f"{good} Focus next on: {biggest} "
        f"Try saying: \"{retry}\""
    )
    feedback_ar = (
        f"{good} ركّز على: {biggest} "
        f"جرّب أن تقول: \"{retry}\""
    )

    if estimated_cefr:
        feedback_en = f"[{estimated_cefr}] " + feedback_en

    return {
        "what_was_good": good,
        "biggest_mistake": biggest,
        "better_version": better,
        "pronunciation_tip": pron_tip,
        "fluency_tip": fluency_tip,
        "grammar_tip": grammar_tip,
        "retry_sentence": retry,
        "coach_feedback": feedback_en.strip(),
        "coach_feedback_ar": feedback_ar.strip(),
    }


async def generate_speaking_coach_feedback(
    *,
    transcript: str,
    corrected_text: str,
    errors: list,
    score_percent: float,
    estimated_cefr: str | None,
    prompt_text: str,
    criteria: dict | None,
    duration_seconds: int | None,
) -> dict[str, str]:
    """AI coach layer with rule-based fallback."""
    fallback = _fallback_coach(
        transcript=transcript,
        corrected_text=corrected_text,
        errors=errors,
        score_percent=score_percent,
        estimated_cefr=estimated_cefr,
        prompt_text=prompt_text,
    )

    if not is_claude_configured():
        return fallback

    user_prompt = (
        f"Speaking prompt: {prompt_text or '(free practice)'}\n"
        f"Learner transcript: {transcript or '(empty)'}\n"
        f"Grammar-corrected: {corrected_text or transcript}\n"
        f"Grammar errors ({len(errors)}): {json.dumps(errors[:5], ensure_ascii=False)}\n"
        f"Score percent: {score_percent}\n"
        f"Estimated CEFR: {estimated_cefr or 'unknown'}\n"
        f"Criteria: {json.dumps(criteria or {}, ensure_ascii=False)}\n"
        f"Duration seconds: {duration_seconds}\n"
        "retry_sentence must be ONE short sentence derived from the correction."
    )

    try:
        raw = await generate_llm_json(
            user_prompt,
            system=_COACH_SYSTEM,
            temperature=0.35,
            max_output_tokens=2048,
        )
        data = _parse_json(raw)
        if not data:
            return fallback
        out = {**fallback}
        for key in fallback:
            val = data.get(key)
            if isinstance(val, str) and val.strip():
                out[key] = val.strip()
        if not out.get("retry_sentence"):
            out["retry_sentence"] = out.get("better_version") or fallback["retry_sentence"]
        return out
    except Exception as exc:
        logger.warning("Speaking coach AI failed: %s", exc)
        return fallback


def _attempt_snapshot(
    *,
    attempt_number: int,
    transcript: str,
    score_percent: float,
    grammar_errors: int,
    fluency_score: float,
    estimated_cefr: str | None,
    coach: dict[str, str],
) -> dict[str, Any]:
    return {
        "attempt": attempt_number,
        "transcript": transcript,
        "score_percent": round(float(score_percent), 2),
        "grammar_errors": int(grammar_errors),
        "fluency_score": round(float(fluency_score), 1),
        "estimated_cefr": estimated_cefr,
        "retry_sentence": coach.get("retry_sentence"),
    }


def compare_speaking_attempts(
    previous: dict | None,
    current: dict[str, Any],
) -> dict[str, Any]:
    """Compare attempt N-1 vs N."""
    if not previous:
        return {
            "attempt_1": None,
            "attempt_2": current,
            "improvement_score": None,
            "grammar_improvement": None,
            "fluency_improvement": None,
        }

    imp_score = round(float(current["score_percent"]) - float(previous["score_percent"]), 1)
    grammar_imp = int(previous.get("grammar_errors") or 0) - int(current.get("grammar_errors") or 0)
    fluency_imp = round(
        float(current.get("fluency_score") or 0) - float(previous.get("fluency_score") or 0),
        1,
    )

    return {
        "attempt_1": previous,
        "attempt_2": current,
        "improvement_score": imp_score,
        "grammar_improvement": grammar_imp,
        "fluency_improvement": fluency_imp,
    }


async def build_speaking_coach_result(
    *,
    transcript: str,
    corrected_text: str,
    errors: list,
    score_percent: float,
    estimated_cefr: str | None,
    prompt_text: str,
    criteria: dict | None,
    duration_seconds: int | None,
    previous_attempts: list[dict] | None,
) -> dict[str, Any]:
    """Full coach payload for speaking submit response."""
    coach = await generate_speaking_coach_feedback(
        transcript=transcript,
        corrected_text=corrected_text,
        errors=errors,
        score_percent=score_percent,
        estimated_cefr=estimated_cefr,
        prompt_text=prompt_text,
        criteria=criteria,
        duration_seconds=duration_seconds,
    )

    wc = _word_count(transcript)
    fluency = _fluency_proxy(criteria=criteria, duration_seconds=duration_seconds, word_count=wc)
    attempt_number = len(previous_attempts or []) + 1

    current_snap = _attempt_snapshot(
        attempt_number=attempt_number,
        transcript=transcript,
        score_percent=score_percent,
        grammar_errors=len(errors),
        fluency_score=fluency,
        estimated_cefr=estimated_cefr,
        coach=coach,
    )

    prev_snap = (previous_attempts or [])[-1] if previous_attempts else None
    comparison = compare_speaking_attempts(prev_snap, current_snap)

    attempts_history = list(previous_attempts or [])
    attempts_history.append(current_snap)
    attempts_history = attempts_history[-5:]

    return {
        **coach,
        "attempt_number": attempt_number,
        "retry_sentence": coach.get("retry_sentence") or coach.get("better_version"),
        "improvement_score": comparison.get("improvement_score"),
        "grammar_improvement": comparison.get("grammar_improvement"),
        "fluency_improvement": comparison.get("fluency_improvement"),
        "attempt_comparison": comparison,
        "coach_attempts": attempts_history,
        "coach_detail": {
            "what_was_good": coach.get("what_was_good"),
            "biggest_mistake": coach.get("biggest_mistake"),
            "better_version": coach.get("better_version"),
            "pronunciation_tip": coach.get("pronunciation_tip"),
            "fluency_tip": coach.get("fluency_tip"),
            "grammar_tip": coach.get("grammar_tip"),
        },
    }
