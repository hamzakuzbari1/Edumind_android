"""Verify Phase 1.5.1 — format-aware CEFR sentence validation (C1 fix).

Usage (from backend/):
    python scripts/verify_language_cefr_phase_1_5_1.py
    python scripts/verify_language_cefr_phase_1_5_1.py --skip-live
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

CEFR_LEVELS = ("A1", "A2", "B1", "B2", "C1", "C2")
FORMATS = (
    "monologue",
    "dialogue",
    "interview",
    "discussion",
    "panel",
    "lecture",
    "news",
)
C1_LIVE_RUNS = 5


def _load_env() -> None:
    env_path = Path(__file__).resolve().parents[2] / ".env"
    if not env_path.is_file():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


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


def _build_monologue_transcript(level: str) -> str:
    """Reuse Phase 1.5 monologue fixture builder for regression parity."""
    import importlib.util

    p15_path = Path(__file__).with_name("verify_language_cefr_phase_1_5.py")
    spec = importlib.util.spec_from_file_location("verify_language_cefr_phase_1_5", p15_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not load verify_language_cefr_phase_1_5.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod._build_transcript(level)  # type: ignore[attr-defined]


def _build_c1_interview_transcript() -> str:
    """Synthetic C1 interview matching live-failure sentence-length profile (~8–11 avg)."""
    return (
        "Host: Good morning, listeners, and welcome back to our weekly show about digital life. "
        "Today we are exploring how smartphones have reshaped our daily routines. "
        "I am joined by Dr. Sarah Nasser, a sociologist who studies digital habits across age groups.\n\n"
        "Sarah: Thank you for having me. It is wonderful to be here today.\n\n"
        "Host: Let us start simply. How much time do teenagers spend on their phones?\n\n"
        "Sarah: Recent studies suggest the average is around four hours daily. "
        "That includes social media, messaging, and gaming.\n\n"
        "Host: That sounds substantial. Do you think this affects their sleep patterns?\n\n"
        "Sarah: Absolutely. Many teens report checking phones late at night. "
        "The blue light disrupts melatonin production significantly.\n\n"
        "Host: What about cognitive development? Should parents be concerned about attention spans?\n\n"
        "Sarah: There is growing evidence that constant notifications fragment attention. "
        "However, smartphones also offer educational opportunities when used mindfully.\n\n"
        "Host: Can schools play a role in teaching digital literacy?\n\n"
        "Sarah: Definitely. Schools should integrate media literacy into curricula. "
        "Students need tools to evaluate online information critically.\n\n"
        "Host: Before we wrap up, what one piece of advice would you give parents?\n\n"
        "Sarah: Model healthy boundaries yourself. Children notice when adults are constantly "
        "distracted by devices during family time.\n\n"
        "Host: Dr. Nasser, thank you for sharing your insights with us today.\n\n"
        "Sarah: Thank you for the thoughtful questions. It has been a pleasure discussing "
        "this important topic with your audience."
    )


def _format_classification_samples() -> dict[str, str]:
    return {
        "monologue": "Good morning. Today I will explain how rivers shape local agriculture.",
        "dialogue": "Anna: Did you finish the report?\nBen: Yes, I sent it this morning.",
        "interview": (
            "Host: Welcome back to the show. Today we are speaking with Dr Lee about climate policy.\n"
            "Dr Lee: Thank you for having me."
        ),
        "discussion": (
            "Moderator: Welcome to our roundtable on urban transport.\n"
            "Alex: I believe cycling infrastructure should be the priority.\n"
            "Jordan: However, funding for buses remains essential for equity."
        ),
        "panel": (
            "Host: Good evening. Joining me on Cross Currents are three policy analysts.\n"
            "Guest A: Thanks for inviting us.\n"
            "Guest B: Happy to contribute."
        ),
        "lecture": (
            "Good morning class. In this lecture we will examine chapter four on macroeconomics. "
            "The professor will outline three competing theories."
        ),
        "news": "Breaking news tonight: reports from the capital indicate negotiations will resume tomorrow.",
    }


def audit_static() -> dict[str, object]:
    from app.services.language_cefr import (
        ListeningTranscriptFormat,
        classify_transcript_format,
        get_cefr_profile,
        get_format_sentence_limits,
        validate_listening_lesson,
        get_allowed_question_types,
    )

    results: dict[str, object] = {}

    classified = {
        name: classify_transcript_format(text).value for name, text in _format_classification_samples().items()
    }
    results["format_classification"] = classified
    results["all_formats_classified"] = set(classified.values()) == set(FORMATS)

    profile_c1 = get_cefr_profile("C1")
    mono_limits = get_format_sentence_limits(profile_c1, ListeningTranscriptFormat.monologue)
    interview_limits = get_format_sentence_limits(profile_c1, ListeningTranscriptFormat.interview)
    results["c1_monologue_limits_match_profile"] = (
        mono_limits.min_words == profile_c1.sentence_min_words
        and mono_limits.max_words == profile_c1.sentence_max_words
    )
    results["c1_interview_limits_relaxed_vs_monologue"] = interview_limits.min_words < mono_limits.min_words

    allowed = [t.value for t in get_allowed_question_types("C1")]
    c1_interview_body = {
        "audio_transcript": _build_c1_interview_transcript(),
        "instructions": "Listen to the interview about smartphones and daily routines.",
        "questions": _questions(allowed),
    }
    c1_report = validate_listening_lesson(c1_interview_body, "C1")
    results["c1_interview_fixture_passes"] = c1_report.passed
    results["c1_interview_format"] = c1_report.checks["sentence_length"].get("transcript_format")

    monologue_reports: dict[str, bool] = {}
    for level in CEFR_LEVELS:
        allowed_level = [t.value for t in get_allowed_question_types(level)]
        body = {
            "audio_transcript": _build_monologue_transcript(level),
            "instructions": "Listen and answer.",
            "questions": _questions(allowed_level),
        }
        monologue_reports[level] = validate_listening_lesson(body, level).passed
    results["monologue_fixture_reports"] = monologue_reports
    results["all_monologue_fixtures_pass"] = all(monologue_reports.values())

    return results


async def audit_live_c1(runs: int = C1_LIVE_RUNS) -> dict[str, object]:
    from app.services.ai_service import generate_llm_json
    from app.services.claude_service import is_claude_configured
    from app.services.language_cefr import validate_listening_lesson
    from app.services.language_cefr.listening_validator import LISTENING_CEFR_MAX_ATTEMPTS
    from app.services.language_lesson_generation_service import _build_prompt, _parse, _to_body

    if not is_claude_configured():
        return {"skipped": True, "reason": "Claude not configured", "runs": runs, "successes": 0}

    outcomes: list[dict] = []
    for run in range(1, runs + 1):
        attempts_log: list[dict] = []
        success = False
        t0 = time.perf_counter()
        for attempt in range(1, LISTENING_CEFR_MAX_ATTEMPTS + 1):
            sys_prompt, user = _build_prompt(
                "listening", "C1", 1, "media literacy / digital habits", "", "", ""
            )
            try:
                raw = await generate_llm_json(user, system=sys_prompt, temperature=0.7, max_output_tokens=8192)
            except Exception as exc:
                attempts_log.append({"attempt": attempt, "error": str(exc)})
                continue
            items = _parse(raw)
            if not items:
                attempts_log.append({"attempt": attempt, "error": "parse_failed"})
                continue
            norm = _to_body("listening", "C1", items[0] if isinstance(items[0], dict) else {}, source="phase_1_5_1")
            if not norm:
                attempts_log.append({"attempt": attempt, "error": "invalid_body"})
                continue
            report = validate_listening_lesson(norm["body"], "C1")
            attempts_log.append(
                {
                    "attempt": attempt,
                    "passed": report.passed,
                    "score": report.score,
                    "format": report.checks.get("sentence_length", {}).get("transcript_format"),
                    "failed_checks": [k for k, v in report.checks.items() if not v.get("passed")],
                }
            )
            if report.passed:
                success = True
                outcomes.append(
                    {
                        "run": run,
                        "success": True,
                        "attempts_used": attempt,
                        "title": norm["title"],
                        "elapsed_s": round(time.perf_counter() - t0, 1),
                        "attempts_log": attempts_log,
                    }
                )
                break
        if not success:
            outcomes.append(
                {
                    "run": run,
                    "success": False,
                    "attempts_used": LISTENING_CEFR_MAX_ATTEMPTS,
                    "elapsed_s": round(time.perf_counter() - t0, 1),
                    "attempts_log": attempts_log,
                }
            )

    successes = sum(1 for o in outcomes if o["success"])
    return {
        "skipped": False,
        "runs": runs,
        "successes": successes,
        "success_rate": successes / runs if runs else 0,
        "all_passed": successes == runs,
        "outcomes": outcomes,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-live", action="store_true", help="Skip live Claude C1 generation")
    args = parser.parse_args()

    _load_env()
    static = audit_static()

    live: dict[str, object] = {"skipped": True, "reason": "--skip-live"}
    if not args.skip_live:
        live = asyncio.run(audit_live_c1())

    print("LANGUAGE-CEFR-PHASE-1.5.1 VERIFICATION")
    print("=" * 48)

    static_checks = [
        ("all_formats_classified", static.get("all_formats_classified")),
        ("c1_monologue_limits_match_profile", static.get("c1_monologue_limits_match_profile")),
        ("c1_interview_limits_relaxed_vs_monologue", static.get("c1_interview_limits_relaxed_vs_monologue")),
        ("c1_interview_fixture_passes", static.get("c1_interview_fixture_passes")),
        ("all_monologue_fixtures_pass", static.get("all_monologue_fixtures_pass")),
    ]
    for key, ok in static_checks:
        print(f"  [{'PASS' if ok else 'FAIL'}] {key}")

    print("\nFORMAT CLASSIFICATION")
    for name, fmt in static.get("format_classification", {}).items():  # type: ignore[union-attr]
        print(f"  {name}: {fmt}")

    print("\nMONOLOGUE FIXTURE PASS (by level)")
    for level, passed in static.get("monologue_fixture_reports", {}).items():  # type: ignore[union-attr]
        print(f"  {level}: {'PASS' if passed else 'FAIL'}")

    if live.get("skipped"):
        print(f"\nLIVE C1 GENERATION: SKIPPED ({live.get('reason')})")
    else:
        print(f"\nLIVE C1 GENERATION ({live.get('runs')} runs)")
        for outcome in live.get("outcomes", []):  # type: ignore[union-attr]
            status = "PASS" if outcome["success"] else "FAIL"
            print(
                f"  Run {outcome['run']}: {status} "
                f"(attempts={outcome['attempts_used']}, {outcome['elapsed_s']}s)"
            )
            if not outcome["success"]:
                last = outcome["attempts_log"][-1] if outcome["attempts_log"] else {}
                print(f"    last failed checks: {last.get('failed_checks')}")
        print(f"  Success rate: {live.get('successes')}/{live.get('runs')}")

    report = {
        "phase": "1.5.1",
        "static": static,
        "live_c1": live,
        "overall_pass": all(ok for _, ok in static_checks)
        and (live.get("skipped") or live.get("all_passed")),
    }
    out_path = Path(__file__).resolve().parents[1] / "scripts" / "_phase_1_5_1_report.json"
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print("-" * 48)
    print(f"  OVERALL: {'PASS' if report['overall_pass'] else 'FAIL'}")
    print(f"  Report: {out_path}")
    return 0 if report["overall_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
