"""Verify Phase 7.3 AI scoring — placement + writing + speaking with rule fallback.

Usage (from backend/):
    python scripts/verify_language_ai_scoring.py
"""

from __future__ import annotations

import asyncio
import inspect
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

SAMPLE_WRITING = (
    "My name is Sara. I live in Damascus with my family. "
    "Every morning I go to school and study English because I want to travel abroad."
)
SAMPLE_PROMPT = "Write about yourself in 3-4 sentences."

MOCK_AI_WRITING = (
    68.5,
    {
        "scorer": "ai_rubric_v2",
        "score_percent": 68.5,
        "criteria": {
            "task_achievement": 72,
            "coherence_cohesion": 70,
            "grammar_accuracy": 65,
            "grammar_range": 60,
            "lexical_resource": 68,
            "mechanics": 75,
        },
        "flags": {"off_topic": False, "gibberish": False, "non_english": False, "too_short": False, "likely_memorized": False},
        "estimated_cefr": "B2",
        "strength": "Clear personal introduction with coherent sentences.",
        "key_error": "Missing article before 'school'.",
        "feedback": "Good structure. Add articles (a/the) and vary sentence openings.",
        "feedback_ar": "أسلوب واضح — ركّز على أدوات التعريف والتنكير.",
        "word_count": 28,
    },
)

MOCK_AI_SPEAKING = (
    55.0,
    {
        "scorer": "ai_rubric_v2",
        "score_percent": 55.0,
        "transcript": "I like reading books and playing football on weekends.",
        "criteria": {
            "task_relevance": 58,
            "fluency_coherence": 52,
            "pronunciation": 50,
            "grammar_accuracy": 55,
            "grammar_range": 48,
            "lexical_resource": 54,
        },
        "flags": {"off_topic": False, "gibberish": False, "non_english": False, "too_short": False, "no_speech": False, "likely_memorized": False},
        "estimated_cefr": "B1",
        "feedback": "Message is clear; work on smoother linking between ideas.",
        "feedback_ar": "الفكرة واضحة — حاول ربط الجمل بشكل أكثر سلاسة.",
    },
)


def _static_checks() -> dict[str, bool]:
    from app.services import language_placement_ai_scoring as ai_scoring
    from app.services import language_speaking_feedback_service as feedback
    from app.services.language_placement_scoring_service import score_speaking, score_writing

    placement_src = (Path(__file__).resolve().parents[1] / "app" / "services" / "language_placement_service.py").read_text(
        encoding="utf-8"
    )
    writing_src = (Path(__file__).resolve().parents[1] / "app" / "services" / "language_writing_service.py").read_text(
        encoding="utf-8"
    )
    speaking_src = (Path(__file__).resolve().parents[1] / "app" / "services" / "language_speaking_service.py").read_text(
        encoding="utf-8"
    )
    ai_src = inspect.getsource(ai_scoring)

    return {
        "placement_ai_scoring_module_exists": hasattr(ai_scoring, "score_writing_ai")
        and hasattr(ai_scoring, "score_speaking_ai"),
        "speaking_feedback_module_exists": hasattr(feedback, "analyze_speaking_recording"),
        "arabic_learner_prompts": "Arabic-speaking" in ai_src and "German" not in ai_src,
        "feedback_ar_in_rubric": "feedback_ar" in ai_src,
        "placement_uses_ai_writing": "score_writing_ai" in placement_src,
        "placement_uses_ai_speaking": "score_speaking_ai" in placement_src,
        "placement_keeps_rule_fallback": "score_writing(resp_json" in placement_src
        and "score_speaking(resp_json" in placement_src,
        "writing_uses_ai_scoring": "score_writing_ai" in writing_src,
        "writing_keeps_rule_fallback": "score_writing({" in writing_src,
        "speaking_uses_feedback_service": "analyze_speaking_recording" in speaking_src,
        "structured_criteria_in_ai": "criteria" in ai_src and "flags" in ai_src,
    }


def _before_after_examples() -> dict:
    from app.services.language_placement_scoring_service import score_speaking, score_writing

    rule_writing_score, rule_writing_metrics = score_writing({"text": SAMPLE_WRITING}, min_words=20)
    rule_speaking_score, rule_speaking_metrics = score_speaking(
        {"media_object_id": 1, "duration_seconds": 25},
        min_seconds=20,
    )

    return {
        "writing_rule_only": {
            "score_percent": rule_writing_score,
            "scorer": "rule_v1",
            "metrics_keys": sorted(rule_writing_metrics.keys()),
            "note": "Length + punctuation heuristic only — no CEFR criteria",
        },
        "writing_ai_example": {
            "score_percent": MOCK_AI_WRITING[0],
            "scorer": MOCK_AI_WRITING[1]["scorer"],
            "estimated_cefr": MOCK_AI_WRITING[1]["estimated_cefr"],
            "criteria": MOCK_AI_WRITING[1]["criteria"],
            "feedback": MOCK_AI_WRITING[1]["feedback"],
            "feedback_ar": MOCK_AI_WRITING[1]["feedback_ar"],
        },
        "speaking_rule_only": {
            "score_percent": rule_speaking_score,
            "scorer": "duration_heuristic",
            "metrics_keys": sorted(rule_speaking_metrics.keys()),
            "note": "Rewards recording length — no transcript analysis",
        },
        "speaking_ai_example": {
            "score_percent": MOCK_AI_SPEAKING[0],
            "scorer": MOCK_AI_SPEAKING[1]["scorer"],
            "estimated_cefr": MOCK_AI_SPEAKING[1]["estimated_cefr"],
            "transcript": MOCK_AI_SPEAKING[1]["transcript"],
            "criteria": MOCK_AI_SPEAKING[1]["criteria"],
            "feedback_ar": MOCK_AI_SPEAKING[1]["feedback_ar"],
        },
    }


async def _integration_mocks() -> dict[str, bool]:
    from app.services import language_placement_ai_scoring as ai_scoring
    from app.services import language_speaking_feedback_service as feedback
    from app.services.language_placement_scoring_service import score_writing

    with patch("app.services.language_placement_ai_scoring.generate_gemini_json", new_callable=AsyncMock) as gemini_mock:
        gemini_mock.return_value = '{"criteria":{"task_achievement":72,"coherence_cohesion":70,"grammar_accuracy":65,"grammar_range":60,"lexical_resource":68,"mechanics":75},"flags":{"off_topic":false,"gibberish":false,"non_english":false,"too_short":false,"likely_memorized":false},"estimated_cefr":"B2","strength":"ok","key_error":"articles","feedback":"Good","feedback_ar":"جيد"}'
        with patch.object(ai_scoring.settings, "GEMINI_API_KEY", "test-key"):
            ai_writing = await ai_scoring.score_writing_ai(text=SAMPLE_WRITING, prompt=SAMPLE_PROMPT)

    fallback_score, _ = score_writing({"text": SAMPLE_WRITING}, min_words=20)

    media = MagicMock()
    media.id = 99
    media.storage_key = "student_1/test.webm"

    stt = MagicMock()
    stt.text = MOCK_AI_SPEAKING[1]["transcript"]
    stt.engine = "faster-whisper"
    stt.low_confidence = False

    db = MagicMock()
    with (
        patch.object(feedback, "_read_media_bytes", return_value=(b"audio", ".webm")),
        patch.object(feedback, "transcribe_english_audio", new_callable=AsyncMock, return_value=stt),
        patch.object(feedback, "analyze_grammar", return_value={"available": True, "corrected_text": stt.text, "errors": []}),
        patch.object(feedback, "_generate_tutor_reply", new_callable=AsyncMock, return_value="Nice!"),
        patch.object(feedback, "score_speaking_ai", new_callable=AsyncMock, return_value=MOCK_AI_SPEAKING),
        patch.object(feedback, "synthesize_english_reply", new_callable=AsyncMock, return_value=None),
    ):
        speaking_feedback = await feedback.analyze_speaking_recording(
            db,
            student_id=1,
            media=media,
            prompt_text="Talk about your hobbies.",
            level=None,
            duration_seconds=25,
            min_seconds=20,
        )

    with (
        patch.object(feedback, "_read_media_bytes", return_value=(b"audio", ".webm")),
        patch.object(feedback, "transcribe_english_audio", new_callable=AsyncMock, return_value=stt),
        patch.object(feedback, "analyze_grammar", return_value={"available": True, "corrected_text": stt.text, "errors": []}),
        patch.object(feedback, "_generate_tutor_reply", new_callable=AsyncMock, return_value="Nice!"),
        patch.object(feedback, "score_speaking_ai", new_callable=AsyncMock, return_value=None),
        patch.object(feedback, "synthesize_english_reply", new_callable=AsyncMock, return_value=None),
    ):
        speaking_rule = await feedback.analyze_speaking_recording(
            db,
            student_id=1,
            media=media,
            prompt_text="Talk about your hobbies.",
            level=None,
            duration_seconds=25,
            min_seconds=20,
        )

    return {
        "ai_writing_returns_rubric": ai_writing is not None and ai_writing[1].get("scorer") == "ai_rubric_v2",
        "ai_writing_has_feedback_ar": bool(ai_writing and ai_writing[1].get("feedback_ar")),
        "writing_fallback_rule_score_sane": 0 < fallback_score <= 100,
        "speaking_feedback_uses_ai_rubric": speaking_feedback.get("scoring_version") == "ai_rubric_v2",
        "speaking_feedback_has_criteria": bool(speaking_feedback.get("metrics", {}).get("criteria")),
        "speaking_fallback_when_no_ai": speaking_rule.get("scoring_version") == "rule_hybrid_v1",
    }


def _print_section(title: str, data: dict) -> None:
    print(f"\n{title}")
    print("-" * len(title))
    for k, v in data.items():
        print(f"  {k}: {v}")


async def main() -> int:
    print("Phase 7.3 — verify_language_ai_scoring")

    static = _static_checks()
    _print_section("Static checks", {k: ("PASS" if v else "FAIL") for k, v in static.items()})

    examples = _before_after_examples()
    _print_section("Before/after scoring examples", examples)

    mocks = await _integration_mocks()
    _print_section("Integration (mocked)", {k: ("PASS" if v else "FAIL") for k, v in mocks.items()})

    failed = [k for k, v in {**static, **mocks}.items() if not v]
    if failed:
        print(f"\nFAILED: {', '.join(failed)}")
        return 1
    print(f"\nAll {len(static) + len(mocks)} checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
