"""Verify Phase 7.6 Speaking Coach.

Usage (from backend/):
    python scripts/verify_language_speaking_coach.py
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

BACKEND = Path(__file__).resolve().parents[1]


def _static_checks() -> dict[str, bool]:
    coach_src = (BACKEND / "app" / "services" / "language_speaking_coach_service.py").read_text(encoding="utf-8")
    speak_src = (BACKEND / "app" / "services" / "language_speaking_service.py").read_text(encoding="utf-8")
    schema_src = (BACKEND / "app" / "schemas" / "language_learning.py").read_text(encoding="utf-8")
    api_src = (BACKEND / "app" / "api" / "language_student.py").read_text(encoding="utf-8")
    vue_src = (BACKEND.parent / "src" / "views" / "student" / "languages" / "StudentLanguageSpeakingView.vue").read_text(
        encoding="utf-8"
    )
    panel_src = (BACKEND.parent / "src" / "components" / "language" / "LanguageSpeakingCoachPanel.vue").read_text(
        encoding="utf-8"
    )
    return {
        "coach_service_exists": (BACKEND / "app" / "services" / "language_speaking_coach_service.py").exists(),
        "coach_fields": all(x in coach_src for x in ["coach_feedback", "coach_feedback_ar", "retry_sentence"]),
        "coach_tips": all(
            x in coach_src for x in ["what_was_good", "biggest_mistake", "better_version", "pronunciation_tip"]
        ),
        "attempt_compare": "compare_speaking_attempts" in coach_src and "improvement_score" in coach_src,
        "wired_submit": "build_speaking_coach_result" in speak_src,
        "schema_coach_fields": "coach_feedback" in schema_src and "retry_sentence" in schema_src,
        "schema_improvement": "improvement_score" in schema_src and "attempt_comparison" in schema_src,
        "vue_coach_panel": "LanguageSpeakingCoachPanel" in vue_src,
        "panel_retry": "retry_sentence" in panel_src and "تحدي إعادة التسجيل" in panel_src,
        "panel_improvement": "improvement_score" in panel_src,
    }


def _persona_examples() -> dict[str, bool]:
    from app.services.language_speaking_coach_service import (
        _fallback_coach,
        build_speaking_coach_result,
        compare_speaking_attempts,
    )

    personas = {
        "weak": {
            "transcript": "I go school yesterday",
            "corrected": "I went to school yesterday.",
            "errors": [{"type": "tense", "message": "Use past tense: went"}],
            "score": 38.0,
            "cefr": "A1",
            "criteria": {"fluency_coherence": 35, "grammar_accuracy": 30, "pronunciation": 40},
        },
        "average": {
            "transcript": "Yesterday I go to school and meet my friend.",
            "corrected": "Yesterday I went to school and met my friend.",
            "errors": [{"type": "tense", "message": "went/met"}],
            "score": 62.0,
            "cefr": "B1",
            "criteria": {"fluency_coherence": 58, "grammar_accuracy": 55, "pronunciation": 60},
        },
        "strong": {
            "transcript": "Yesterday I went to school and discussed our project with my team.",
            "corrected": "Yesterday I went to school and discussed our project with my team.",
            "errors": [],
            "score": 88.0,
            "cefr": "B2",
            "criteria": {"fluency_coherence": 85, "grammar_accuracy": 90, "pronunciation": 82},
        },
    }

    print("\nSpeaking Coach persona examples")
    print("-------------------------------")

    results: dict[str, bool] = {}
    for label, p in personas.items():
        coach = _fallback_coach(
            transcript=p["transcript"],
            corrected_text=p["corrected"],
            errors=p["errors"],
            score_percent=p["score"],
            estimated_cefr=p["cefr"],
            prompt_text="Describe your day.",
        )
        print(f"\n  {label.upper()} speaker:")
        print(f"    transcript: {p['transcript']}")
        print(f"    score: {p['score']}%  CEFR: {p['cefr']}")
        print(f"    coach_feedback: {coach['coach_feedback'][:100]}...")
        print(f"    retry_sentence: {coach['retry_sentence']}")
        print(f"    biggest_mistake: {coach['biggest_mistake'][:80]}")

        results[f"{label}_has_retry"] = bool(coach.get("retry_sentence"))
        results[f"{label}_has_coach_feedback"] = bool(coach.get("coach_feedback") and coach.get("coach_feedback_ar"))
        results[f"{label}_has_tips"] = all(coach.get(k) for k in ("pronunciation_tip", "fluency_tip", "grammar_tip"))

    # Weak → improved retry comparison
    async def _run_compare():
        with patch(
            "app.services.language_speaking_coach_service.generate_speaking_coach_feedback",
            new_callable=AsyncMock,
        ) as mock_ai:
            mock_ai.side_effect = lambda **kw: _fallback_coach(
                transcript=kw["transcript"],
                corrected_text=kw["corrected_text"],
                errors=kw["errors"],
                score_percent=kw["score_percent"],
                estimated_cefr=kw["estimated_cefr"],
                prompt_text=kw["prompt_text"],
            )
            attempt1 = await build_speaking_coach_result(
                transcript="I go school yesterday",
                corrected_text="I went to school yesterday.",
                errors=[{"type": "tense"}],
                score_percent=38.0,
                estimated_cefr="A1",
                prompt_text="Describe your day.",
                criteria={"fluency_coherence": 35},
                duration_seconds=15,
                previous_attempts=None,
            )
            attempt2 = await build_speaking_coach_result(
                transcript="I went to school yesterday.",
                corrected_text="I went to school yesterday.",
                errors=[],
                score_percent=50.0,
                estimated_cefr="A2",
                prompt_text="Describe your day.",
                criteria={"fluency_coherence": 52},
                duration_seconds=18,
                previous_attempts=attempt1["coach_attempts"],
            )
            return attempt1, attempt2

    a1, a2 = asyncio.run(_run_compare())
    cmp = compare_speaking_attempts(a1["coach_attempts"][0], a2["coach_attempts"][1])
    print("\n  RETRY comparison (weak → improved):")
    print(f"    attempt 1 score: {cmp['attempt_1']['score_percent']}%")
    print(f"    attempt 2 score: {cmp['attempt_2']['score_percent']}%")
    print(f"    improvement_score: {cmp['improvement_score']}")
    print(f"    grammar_improvement: {cmp['grammar_improvement']}")
    print(f"    fluency_improvement: {cmp['fluency_improvement']}")

    results["retry_improvement_positive"] = (cmp.get("improvement_score") or 0) > 0
    results["retry_grammar_improved"] = (cmp.get("grammar_improvement") or 0) > 0
    results["attempt_2_number"] = a2.get("attempt_number") == 2

    return results


def main() -> int:
    print("Phase 7.6 — verify_language_speaking_coach\n")

    static = _static_checks()
    print("Static checks")
    print("-------------")
    for k, v in static.items():
        print(f"  {k}: {'PASS' if v else 'FAIL'}")

    personas = _persona_examples()
    print("\nPersona checks")
    print("--------------")
    for k, v in personas.items():
        print(f"  {k}: {'PASS' if v else 'FAIL'}")

    all_ok = all(static.values()) and all(personas.values())
    total = len(static) + len(personas)
    passed = sum(static.values()) + sum(personas.values())
    print(f"\n{passed}/{total} checks passed.")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
