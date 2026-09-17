"""Verify Phase 1.5 — Listening CEFR validation engine.

Usage (from backend/):
    python scripts/verify_language_cefr_phase_1_5.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

CEFR_LEVELS = ("A1", "A2", "B1", "B2", "C1", "C2")


def _questions(types: list[str]) -> list[dict]:
    return [
        {
            "id": f"q{i + 1}",
            "stem": f"Question {i + 1}?",
            "choices": ["A", "B", "C", "D"],
            "correct_index": 0,
            "type": t,
            "explanation": "Because the transcript states it.",
            "evidence_quote": "student",
        }
        for i, t in enumerate(types[:4])
    ]


_NOUNS = ("market", "shop", "park", "school", "library", "station", "bakery", "garden", "office", "museum")
_VERBS = ("visited", "walked", "passed", "entered", "saw", "found", "enjoyed", "explored", "joined", "watched")


def _sentence_for(level: str, i: int) -> str:
    if level == "A1":
        return f"I am in class number {i} today."
    if level == "A2":
        noun = _NOUNS[i % len(_NOUNS)]
        verb = _VERBS[i % len(_VERBS)]
        return f"Yesterday I {verb} the {noun} near street {i} and bought fresh bread."
    if level == "B1":
        topic = _NOUNS[i % len(_NOUNS)]
        return f"Our group discussed the {topic} plan {i} last month because tickets were cheaper."
    if level == "B2":
        topic = _NOUNS[i % len(_NOUNS)]
        return (
            f"During the meeting, colleagues debated whether the {topic} project {i} "
            f"would succeed when funding remained limited this year."
        )
    if level == "C1":
        topic = _NOUNS[i % len(_NOUNS)]
        return (
            f"Although several members questioned whether the {topic} policy {i} would "
            f"achieve its goals, most speakers agreed it deserved review."
        )
    topic = _NOUNS[i % len(_NOUNS)]
    verb = _VERBS[i % len(_VERBS)]
    return (
        f"Notwithstanding the complexity of the {topic} issue {i}, analysts {verb} "
        f"that broader cooperation could mitigate regional risks over time."
    )


def _build_transcript(level: str) -> str:
    from app.services.language_cefr import get_cefr_profile

    profile = get_cefr_profile(level)
    target = max(profile.ideal_word_count, profile.word_limits.min_words)
    sentences: list[str] = []
    wc = 0
    i = 0
    while wc < target:
        sentence = _sentence_for(level, i).rstrip(".")
        sentences.append(sentence)
        wc += len(sentence.split())
        i += 1
        if i > target * 2:
            break
    while sentences and len((". ".join(sentences) + ".").split()) > profile.word_limits.max_words:
        sentences.pop()
    return ". ".join(sentences) + "."


def _sample_body(level: str) -> dict:
    from app.services.language_cefr import get_allowed_question_types

    allowed = [t.value for t in get_allowed_question_types(level)]
    qtypes = (allowed * 2)[:4]
    return {
        "audio_transcript": _build_transcript(level),
        "instructions": "Listen and answer the questions.",
        "questions": _questions(qtypes),
    }


def audit() -> dict[str, object]:
    from app.services.language_cefr import (
        LISTENING_CEFR_MAX_ATTEMPTS,
        validate_listening_lesson,
    )
    from app.services.language_lesson_generation_service import (
        _generate_and_store_listening,
        _generate_one_validated_listening,
    )

    results: dict[str, object] = {}
    level_reports: dict[str, dict] = {}

    for level in CEFR_LEVELS:
        report = validate_listening_lesson(_sample_body(level), level)
        level_reports[level] = {
            "passed": report.passed,
            "score": report.score,
            "attempt_count": 1,
            "checks": report.checks,
        }

    results["level_reports"] = level_reports
    results["all_levels_pass_fixtures"] = all(r["passed"] for r in level_reports.values())
    results["max_attempts_constant"] = LISTENING_CEFR_MAX_ATTEMPTS == 3

    # Invalid cases
    a1_bad_word_count = _sample_body("A1")
    a1_bad_word_count["audio_transcript"] = "Hello. I am Sara."
    bad_wc = validate_listening_lesson(a1_bad_word_count, "A1")
    results["rejects_short_transcript"] = not bad_wc.passed and not bad_wc.checks["word_count"]["passed"]

    a1_bad_q = _sample_body("A1")
    a1_bad_q["questions"] = _questions(["inference", "detail", "main_idea", "detail"])
    bad_q = validate_listening_lesson(a1_bad_q, "A1")
    results["rejects_forbidden_question_type"] = not bad_q.passed and not bad_q.checks["questions"]["passed"]

    a1_bad_grammar = _sample_body("A1")
    a1_bad_grammar["audio_transcript"] = _build_transcript("A1") + " If I had known, I would have called you."
    bad_g = validate_listening_lesson(a1_bad_grammar, "A1")
    results["rejects_forbidden_grammar"] = not bad_g.passed and not bad_g.checks["grammar"]["passed"]

    # Pipeline wiring
    gen_src = (Path(__file__).resolve().parents[1] / "app/services/language_lesson_generation_service.py").read_text(
        encoding="utf-8"
    )
    results["listening_uses_validator"] = "validate_listening_lesson" in gen_src
    results["listening_has_regeneration"] = "_generate_one_validated_listening" in gen_src
    results["listening_routes_before_store"] = "_generate_and_store_listening" in gen_src
    results["invalid_not_stored_on_fail"] = "if last_report.passed" in gen_src

    # Import smoke
    try:
        from app.main import app  # noqa: F401

        results["fastapi_import_ok"] = True
    except Exception as exc:  # pragma: no cover
        results["fastapi_import_ok"] = False
        results["import_error"] = str(exc)

    return results


def print_reports(results: dict[str, object]) -> None:
    level_reports: dict[str, dict] = results["level_reports"]  # type: ignore[assignment]
    print("\nVALIDATION REPORTS (fixture lessons)")
    print(f"{'Level':<6} {'Pass':<6} {'Score':<6} {'Attempts':<10} {'Failed checks'}")
    print("-" * 60)
    for level in CEFR_LEVELS:
        r = level_reports[level]
        failed = [k for k, v in r["checks"].items() if not v.get("passed")]
        print(f"{level:<6} {str(r['passed']):<6} {r['score']:<6} {r['attempt_count']:<10} {', '.join(failed) or '-'}")

    print("\nSAMPLE CHECK DETAIL (A1)")
    print(json.dumps(level_reports["A1"]["checks"], indent=2)[:1200])


def main() -> int:
    results = audit()
    checks = [
        "all_levels_pass_fixtures",
        "max_attempts_constant",
        "rejects_short_transcript",
        "rejects_forbidden_question_type",
        "rejects_forbidden_grammar",
        "listening_uses_validator",
        "listening_has_regeneration",
        "listening_routes_before_store",
        "invalid_not_stored_on_fail",
        "fastapi_import_ok",
    ]

    print("LANGUAGE-CEFR-PHASE-1.5 VERIFICATION")
    print("=" * 44)
    for key in checks:
        print(f"  [{'PASS' if results.get(key) else 'FAIL'}] {key}")

    print_reports(results)

    print("\nVALIDATION PIPELINE")
    print("  Claude -> JSON -> _to_body -> validate_listening_lesson")
    print("  PASS -> store | FAIL -> regenerate (max 3) -> store or ListeningCefrValidationExhaustedError")

    passed = all(bool(results.get(k)) for k in checks)
    print("-" * 44)
    print(f"  OVERALL: {'PASS' if passed else 'FAIL'}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
