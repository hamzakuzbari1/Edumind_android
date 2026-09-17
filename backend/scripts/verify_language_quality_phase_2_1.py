"""Verify Phase 2.1 — Human-like Listening Quality Layer.

Usage (from backend/):
    python scripts/verify_language_quality_phase_2_1.py
    python scripts/verify_language_quality_phase_2_1.py --skip-live
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

GENERATION_LEVELS = ("A1", "A2", "B1", "B2", "C1", "C2")
LIVE_LEVELS = ("A1", "C1", "A2", "B1", "B2", "C1", "C2", "B2", "A2", "B1")


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


def _legacy_listening_prompt(level: str, themes: str = "", topics: str = "") -> str:
    """Pre-Phase-2.1 listening prompt shape (no quality layer)."""
    from app.services.language_cefr.listening_runtime import (
        build_listening_cefr_profile_block,
        build_listening_generation_question_prompt_block,
    )

    theme_line = f" Reinforce these grammar/vocabulary themes where natural: {themes}." if themes else ""
    topic_line = f" Prefer topics the learner enjoys: {topics}." if topics else ""
    cefr_block = build_listening_cefr_profile_block(level)
    question_block = build_listening_generation_question_prompt_block(level)
    return (
        f"You are a CEFR curriculum author writing IELTS-style listening tasks. Generate exactly 1 "
        f"DISTINCT CEFR {level} English listening lessons for Syrian secondary-school learners."
        f"{theme_line}{topic_line} ENGLISH ONLY.\n\n"
        f"{cefr_block}\n\n"
        "You MUST obey every constraint in [CEFR PROFILE]. "
        "The audio_transcript must match the transcript word-count and sentence-length bounds, "
        "use only allowed grammar, avoid forbidden grammar, match the vocabulary band, "
        "stay within suitable topics, and satisfy the listening objectives. "
        f"Each lesson: one natural spoken-English audio_transcript + {question_block}"
    )


def _current_listening_prompt(level: str, themes: str = "", topics: str = "") -> str:
    from app.services.language_lesson_generation_service import _build_prompt

    sys_prompt, _ = _build_prompt("listening", level, 1, themes, topics, "", "")
    return sys_prompt


def audit_static() -> dict[str, object]:
    from app.services.language_listening_quality import (
        build_listening_quality_prompt_block,
        listening_quality_spec_snapshot,
    )

    results: dict[str, object] = {}
    gen_src = (
        Path(__file__).resolve().parents[1] / "app/services/language_lesson_generation_service.py"
    ).read_text(encoding="utf-8")

    results["generation_wires_quality_layer"] = "build_listening_quality_prompt_block" in gen_src
    results["generation_preserves_cefr_block"] = "build_listening_cefr_profile_block" in gen_src
    results["quality_block_present_in_prompt"] = "[LISTENING QUALITY]" in _current_listening_prompt("B1")
    results["legacy_prompt_lacks_quality"] = "[LISTENING QUALITY]" not in _legacy_listening_prompt("B1")

    before = _legacy_listening_prompt("B1")
    after = _current_listening_prompt("B1")
    results["prompt_growth_chars"] = len(after) - len(before)
    results["after_has_authenticity"] = "Authenticity" in after
    results["after_has_narrative_flow"] = "Narrative flow" in after
    results["after_has_question_design"] = "Question design" in after

    seeds = [listening_quality_spec_snapshot("B1", seed=f"run-{i}") for i in range(10)]
    unique_situations = len({s["situation"] for s in seeds})
    unique_formats = len({s["format_hint"] for s in seeds})
    results["rotation_unique_situations_10"] = unique_situations
    results["rotation_unique_formats_10"] = unique_formats
    results["rotation_diverse"] = unique_situations >= 5 and unique_formats >= 3

    block = build_listening_quality_prompt_block("C1", seed="verify")
    results["no_hardcoded_transcript_template"] = "audio_transcript" not in block.lower() or "Return ONLY JSON" not in block
    results["quality_block_has_exam_refs"] = "Cambridge" in block and "IELTS" in block

    # CEFR engine files should remain importable unchanged
    try:
        from app.services.language_cefr import validate_listening_lesson, get_cefr_profile  # noqa: F401

        results["cefr_engine_intact"] = True
    except Exception as exc:  # pragma: no cover
        results["cefr_engine_intact"] = False
        results["cefr_import_error"] = str(exc)

    return results


async def audit_live_generation() -> dict[str, object]:
    from app.services.ai_service import generate_llm_json
    from app.services.claude_service import is_claude_configured
    from app.services.language_listening_quality.evaluation import evaluate_listening_lesson
    from app.services.language_listening_quality import listening_quality_spec_snapshot
    from app.services.language_lesson_generation_service import _build_prompt, _parse, _to_body

    if not is_claude_configured():
        return {"skipped": True, "reason": "Claude not configured", "lessons": []}

    lessons: list[dict] = []
    for idx, level in enumerate(LIVE_LEVELS):
        seed = f"phase-2.1-{idx}"
        spec = listening_quality_spec_snapshot(level, seed=seed)
        sys_prompt, user = _build_prompt(
            "listening", level, 1, "present simple / travel", "", "", "", quality_seed=seed
        )
        t0 = time.perf_counter()
        try:
            raw = await generate_llm_json(user, system=sys_prompt, temperature=0.7, max_output_tokens=8192)
        except Exception as exc:
            lessons.append({"level": level, "error": str(exc), "seed": seed})
            continue
        items = _parse(raw)
        if not items:
            lessons.append({"level": level, "error": "parse_failed", "seed": seed})
            continue
        norm = _to_body("listening", level, items[0] if isinstance(items[0], dict) else {}, source="quality_verify")
        if not norm:
            lessons.append({"level": level, "error": "invalid_body", "seed": seed})
            continue
        body = norm["body"]
        transcript = str(body.get("audio_transcript") or "")
        questions = body.get("questions") if isinstance(body.get("questions"), list) else []
        evaluation = evaluate_listening_lesson(
            level=level,
            title=norm["title"],
            transcript=transcript,
            questions=questions,
            situation=str(spec.get("situation")),
        )
        lessons.append(
            {
                "level": level,
                "seed": seed,
                "title": norm["title"],
                "spec": spec,
                "elapsed_s": round(time.perf_counter() - t0, 1),
                "transcript_preview": transcript[:220] + ("…" if len(transcript) > 220 else ""),
                "evaluation": evaluation,
            }
        )

    if not lessons:
        return {"skipped": False, "lessons": [], "all_generated": False}

    successful = [l for l in lessons if "evaluation" in l]
    composites = [l["evaluation"]["composite_score"] for l in successful]  # type: ignore[index]
    situations = [l["spec"]["situation"] for l in successful]  # type: ignore[index]

    return {
        "skipped": False,
        "requested": len(LIVE_LEVELS),
        "generated": len(successful),
        "all_generated": len(successful) == len(LIVE_LEVELS),
        "unique_situations": len(set(situations)),
        "avg_composite_score": round(sum(composites) / len(composites), 1) if composites else 0,
        "min_composite_score": min(composites) if composites else 0,
        "lessons": lessons,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-live", action="store_true")
    args = parser.parse_args()

    _load_env()
    static = audit_static()
    live = {"skipped": True, "reason": "--skip-live"} if args.skip_live else asyncio.run(audit_live_generation())

    checks = [
        ("generation_wires_quality_layer", static.get("generation_wires_quality_layer")),
        ("generation_preserves_cefr_block", static.get("generation_preserves_cefr_block")),
        ("quality_block_present_in_prompt", static.get("quality_block_present_in_prompt")),
        ("legacy_prompt_lacks_quality", static.get("legacy_prompt_lacks_quality")),
        ("after_has_authenticity", static.get("after_has_authenticity")),
        ("after_has_narrative_flow", static.get("after_has_narrative_flow")),
        ("after_has_question_design", static.get("after_has_question_design")),
        ("rotation_diverse", static.get("rotation_diverse")),
        ("quality_block_has_exam_refs", static.get("quality_block_has_exam_refs")),
        ("cefr_engine_intact", static.get("cefr_engine_intact")),
    ]

    print("LANGUAGE-QUALITY-PHASE-2.1 VERIFICATION")
    print("=" * 48)
    for key, ok in checks:
        print(f"  [{'PASS' if ok else 'FAIL'}] {key}")

    print("\nBEFORE vs AFTER PROMPT")
    print(f"  Legacy prompt length: {len(_legacy_listening_prompt('B1'))} chars")
    print(f"  Enhanced prompt length: {len(_current_listening_prompt('B1'))} chars")
    print(f"  Added guidance: +{static.get('prompt_growth_chars')} chars")
    print(f"  Rotation (10 seeds): {static.get('rotation_unique_situations_10')} situations, "
          f"{static.get('rotation_unique_formats_10')} formats")

    if live.get("skipped"):
        print(f"\nLIVE GENERATION (10 lessons): SKIPPED ({live.get('reason')})")
        live_ok = True
    else:
        print(f"\nLIVE GENERATION (10 lessons)")
        print(f"  Generated: {live.get('generated')}/{live.get('requested')}")
        print(f"  Unique situations: {live.get('unique_situations')}")
        print(f"  Avg composite score: {live.get('avg_composite_score')}")
        print(f"  Min composite score: {live.get('min_composite_score')}")
        for lesson in live.get("lessons", []):  # type: ignore[union-attr]
            if "evaluation" not in lesson:
                print(f"  {lesson.get('level')}: ERROR {lesson.get('error')}")
                continue
            ev = lesson["evaluation"]
            print(
                f"  {lesson['level']}: score={ev['composite_score']} "
                f"naturalness={ev['naturalness']} situation={lesson['spec']['situation']} "
                f"title={lesson['title'][:50]}"
            )
        live_ok = bool(live.get("all_generated")) and (live.get("unique_situations", 0) or 0) >= 5
        live_ok = live_ok and (live.get("avg_composite_score", 0) or 0) >= 70

    report = {
        "phase": "2.1",
        "static": static,
        "live": live,
        "overall_pass": all(ok for _, ok in checks) and live_ok,
    }
    out_path = Path(__file__).resolve().parents[1] / "scripts" / "_phase_2_1_report.json"
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    print("-" * 48)
    print(f"  OVERALL: {'PASS' if report['overall_pass'] else 'FAIL'}")
    print(f"  Report: {out_path}")
    return 0 if report["overall_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
