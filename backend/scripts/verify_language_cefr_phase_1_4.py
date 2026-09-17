"""Verify Phase 1.4 — CEFR profile activation in Listening generation prompts.

Usage (from backend/):
    python scripts/verify_language_cefr_phase_1_4.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

CEFR_LEVELS = ("A1", "A2", "B1", "B2", "C1", "C2")


def _truncate(text: str, limit: int = 72) -> str:
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def audit() -> dict[str, object]:
    from app.services.language_cefr import (
        build_listening_cefr_profile_block,
        get_listening_generation_question_types,
        listening_prompt_spec_snapshot,
    )
    from app.services.language_lesson_generation_service import _build_prompt

    results: dict[str, object] = {}
    snapshots: dict[str, dict[str, object]] = {}
    prompts: dict[str, str] = {}

    for level in CEFR_LEVELS:
        snapshots[level] = listening_prompt_spec_snapshot(level)
        sys_prompt, _user = _build_prompt("listening", level, 1, "present simple / daily routine", "", "", "")
        prompts[level] = sys_prompt

    results["snapshots"] = snapshots
    results["prompts"] = prompts

    # Structural checks
    results["all_prompts_have_cefr_block"] = all("[CEFR PROFILE]" in p and "[/CEFR PROFILE]" in p for p in prompts.values())
    results["no_level_guidance_in_listening"] = all("reply shape" not in p for p in prompts.values())
    results["all_use_build_cefr_block"] = all("You MUST obey every constraint in [CEFR PROFILE]" in p for p in prompts.values())

    # A1 must forbid inference / T/F/NG in question instructions
    a1_prompt = prompts["A1"]
    results["a1_forbids_inference"] = "NEVER use these question types: inference" in a1_prompt
    results["a1_forbids_tfng"] = "true_false_notgiven" in a1_prompt and "NEVER use these question types:" in a1_prompt
    a1_allowed = {t.value for t in get_listening_generation_question_types("A1")}
    results["a1_no_inference_in_allowed"] = "inference" not in a1_allowed

    # B2+ should include bias
    b2_allowed = {t.value for t in get_listening_generation_question_types("B2")}
    results["b2_includes_bias"] = "bias" in b2_allowed

    # Progression visible across levels
    word_ideals = [snapshots[l]["word_ideal"] for l in CEFR_LEVELS]
    sentence_max = [snapshots[l]["sentence_max"] for l in CEFR_LEVELS]
    results["word_count_progression"] = word_ideals == sorted(word_ideals) and len(set(word_ideals)) == 6
    results["sentence_length_progression"] = sentence_max == sorted(sentence_max) and len(set(sentence_max)) > 1

    qtype_sets = [frozenset(snapshots[l]["allowed_question_types"]) for l in CEFR_LEVELS]
    results["question_types_differ_by_level"] = len(set(qtype_sets)) >= 3

    grammar_sets = [frozenset(snapshots[l]["allowed_grammar"]) for l in CEFR_LEVELS]
    results["grammar_differ_by_level"] = len(set(grammar_sets)) == 6

    vocab_texts = [snapshots[l]["vocabulary_band"] for l in CEFR_LEVELS]
    results["vocabulary_differ_by_level"] = len(set(vocab_texts)) == 6

    topic_texts = [snapshots[l]["topic_complexity"] for l in CEFR_LEVELS]
    results["topics_differ_by_level"] = len(set(topic_texts)) == 6

    # CEFR block is built only from engine (sanity)
    block_b1 = build_listening_cefr_profile_block("B1")
    results["cefr_block_contains_profile_fields"] = all(
        token in block_b1
        for token in ("Transcript:", "Grammar:", "Vocabulary:", "Question Types:", "Learning Objective:")
    )

    return results


def print_comparison(results: dict[str, object]) -> None:
    snapshots: dict[str, dict[str, object]] = results["snapshots"]  # type: ignore[assignment]

    print("\nSIDE-BY-SIDE: TRANSCRIPT & SENTENCE LIMITS")
    print(f"{'Level':<6} {'Words (min–ideal–max)':<26} {'Sentence (min–max)':<18} {'Q types':<6}")
    print("-" * 62)
    for level in CEFR_LEVELS:
        s = snapshots[level]
        words = f"{s['word_min']}–{s['word_ideal']}–{s['word_max']}"
        sents = f"{s['sentence_min']}–{s['sentence_max']}"
        qcount = len(s["allowed_question_types"])  # type: ignore[arg-type]
        print(f"{level:<6} {words:<26} {sents:<18} {qcount:<6}")

    print("\nSIDE-BY-SIDE: ALLOWED QUESTION TYPES")
    for level in CEFR_LEVELS:
        types = ", ".join(snapshots[level]["allowed_question_types"])  # type: ignore[index]
        print(f"  {level}: {types}")

    print("\nSIDE-BY-SIDE: GRAMMAR (first allowed rule)")
    for level in CEFR_LEVELS:
        grammar = snapshots[level]["allowed_grammar"][0]  # type: ignore[index]
        print(f"  {level}: {grammar}")

    print("\nSIDE-BY-SIDE: VOCABULARY BAND (truncated)")
    for level in CEFR_LEVELS:
        vocab = _truncate(str(snapshots[level]["vocabulary_band"]))
        print(f"  {level}: {vocab}")

    print("\nSIDE-BY-SIDE: TOPIC COMPLEXITY (truncated)")
    for level in CEFR_LEVELS:
        topic = _truncate(str(snapshots[level]["topic_complexity"]))
        print(f"  {level}: {topic}")

    print("\nBEFORE vs AFTER (prompt structure)")
    print("  BEFORE (Phase 1.3): same 5 question types at every level; ~N-word target only; LEVEL_GUIDANCE prose")
    print("  AFTER  (Phase 1.4): full [CEFR PROFILE] block; per-level question types; grammar/vocab/topic/objectives")


def main() -> int:
    results = audit()
    checks = [
        "all_prompts_have_cefr_block",
        "no_level_guidance_in_listening",
        "all_use_build_cefr_block",
        "a1_forbids_inference",
        "a1_forbids_tfng",
        "a1_no_inference_in_allowed",
        "b2_includes_bias",
        "word_count_progression",
        "sentence_length_progression",
        "question_types_differ_by_level",
        "grammar_differ_by_level",
        "vocabulary_differ_by_level",
        "topics_differ_by_level",
        "cefr_block_contains_profile_fields",
    ]

    print("LANGUAGE-CEFR-PHASE-1.4 VERIFICATION")
    print("=" * 44)
    for key in checks:
        status = "PASS" if results.get(key) else "FAIL"
        print(f"  [{status}] {key}")

    print_comparison(results)

    passed = all(bool(results.get(k)) for k in checks)
    print("-" * 44)
    print(f"  OVERALL: {'PASS' if passed else 'FAIL'}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
