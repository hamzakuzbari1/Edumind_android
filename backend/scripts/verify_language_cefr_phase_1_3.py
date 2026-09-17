"""Verify Phase 1.3 — Listening runtime migration to centralized CEFR engine.

Usage (from backend/):
    python scripts/verify_language_cefr_phase_1_3.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

BACKEND = Path(__file__).resolve().parents[1]
LISTENING_FILES = (
    BACKEND / "app/services/language_listening_service.py",
    BACKEND / "app/services/language_listening_prefill_task.py",
    BACKEND / "app/services/language_lesson_generation_service.py",
    BACKEND / "app/services/language_content_service.py",
    BACKEND / "app/api/language_student.py",
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def audit() -> dict[str, bool | str | int | list[str]]:
    from app.models.language.enums import LanguageLevel
    from app.services.language_cefr import (
        CEFR_LEVEL_CODES,
        get_cefr_profile,
        get_listening_generation_question_types,
        get_listening_generation_word_target,
        get_word_limits,
        listening_generation_question_type_names,
    )
    from app.services.language_cefr.listening_runtime import build_listening_generation_question_prompt_block
    from app.services.language_lesson_generation_service import _build_prompt

    results: dict[str, bool | str | int | list[str]] = {}

    gen_src = _read(BACKEND / "app/services/language_lesson_generation_service.py")
    listening_src = _read(BACKEND / "app/services/language_listening_service.py")

    # Legacy listening constants removed from generation service
    results["no_words_for_level_symbol"] = "WORDS_FOR_LEVEL" not in gen_src.replace("READING_WORDS_FOR_LEVEL", "")
    results["reading_words_preserved"] = "READING_WORDS_FOR_LEVEL" in gen_src
    results["generation_imports_cefr_runtime"] = "language_cefr.listening_runtime" in gen_src
    results["uses_get_listening_generation_word_target"] = "get_listening_generation_word_target" in gen_src
    results["uses_build_listening_question_block"] = "build_listening_generation_question_prompt_block" in gen_src

    # Listening service has no duplicated CEFR numeric maps
    results["listening_service_no_word_map"] = "WORDS_FOR_LEVEL" not in listening_src and "READING_WORDS_FOR_LEVEL" not in listening_src

    # Word targets match legacy runtime (backward compatible refactor)
    legacy_targets = {"A1": 45, "A2": 70, "B1": 110, "B2": 170, "C1": 230, "C2": 280}
    word_target_ok = all(
        get_listening_generation_word_target(level) == legacy_targets[level] for level in CEFR_LEVEL_CODES
    )
    results["word_targets_backward_compatible"] = word_target_ok

    # API works through engine for every level
    profile_ok = True
    for code in CEFR_LEVEL_CODES:
        profile = get_cefr_profile(code)
        limits = get_word_limits(code)
        if profile.level != LanguageLevel(code):
            profile_ok = False
        if limits.ideal_words != profile.ideal_word_count:
            profile_ok = False
    results["all_levels_via_engine"] = profile_ok

    # Question types centralized
    qtypes = get_listening_generation_question_types("B1")
    names = listening_generation_question_type_names(qtypes)
    results["question_types_count"] = len(qtypes)
    results["question_types_legacy_mix"] = names == (
        "main_idea",
        "detail",
        "inference",
        "true_false_notgiven",
        "sentence_completion",
    )

    # Prompt block still contains legacy instructions
    block = build_listening_generation_question_prompt_block("A1")
    results["prompt_block_has_mcq_line"] = "main_idea / detail / inference" in block
    results["prompt_block_has_tfng"] = "true_false_notgiven" in block

    # _build_prompt listening branch delegates to engine
    sys_prompt, _user = _build_prompt("listening", "A2", 1, "present simple / food", "", "", "")
    results["listening_prompt_uses_engine_word_target"] = "~70-word" in sys_prompt
    results["listening_prompt_has_question_block"] = "true_false_notgiven" in sys_prompt

    # Import graph — listening runtime path only through language_cefr
    importers: list[str] = []
    for rel in (
        "app/services/language_listening_service.py",
        "app/services/language_lesson_generation_service.py",
    ):
        src = _read(BACKEND / rel)
        if "language_cefr" in src:
            importers.append(rel)
    results["cefr_importers"] = importers

    # Scan listening-related files for forbidden duplicated maps
    duplicated: list[str] = []
    forbidden_patterns = (
        "WORDS_FOR_LEVEL",
        'main_idea|detail|inference|true_false_notgiven|sentence_completion',
    )
    for path in LISTENING_FILES:
        if not path.is_file():
            continue
        text = _read(path)
        if path.name == "language_lesson_generation_service.py":
            # Reading-only map is allowed; listening must not reference it.
            if "READING_WORDS_FOR_LEVEL" in text and 'skill == "listening"' in text:
                listening_branch = text.split('elif skill == "listening":', 1)[-1].split("elif skill ==")[0]
                if "READING_WORDS_FOR_LEVEL" in listening_branch:
                    duplicated.append(f"{path.name}:listening_branch_uses_reading_words")
            continue
        for pattern in forbidden_patterns:
            if pattern in text:
                duplicated.append(f"{path.name}:{pattern}")
    results["listening_files_without_duplicated_constants"] = not duplicated
    if duplicated:
        results["duplicated_hits"] = duplicated

    # FastAPI app import smoke test
    import_ok = True
    try:
        from app.main import app  # noqa: F401
    except Exception as exc:  # pragma: no cover
        import_ok = False
        results["import_error"] = str(exc)
    results["fastapi_import_ok"] = import_ok

    return results


def main() -> int:
    results = audit()
    checks = [
        "no_words_for_level_symbol",
        "reading_words_preserved",
        "generation_imports_cefr_runtime",
        "uses_get_listening_generation_word_target",
        "uses_build_listening_question_block",
        "listening_service_no_word_map",
        "word_targets_backward_compatible",
        "all_levels_via_engine",
        "question_types_legacy_mix",
        "prompt_block_has_mcq_line",
        "prompt_block_has_tfng",
        "listening_prompt_uses_engine_word_target",
        "listening_prompt_has_question_block",
        "listening_files_without_duplicated_constants",
        "fastapi_import_ok",
    ]
    passed = all(bool(results.get(k)) for k in checks)

    print("LANGUAGE-CEFR-PHASE-1.3 VERIFICATION")
    print("=" * 44)
    for key in checks:
        status = "PASS" if results.get(key) else "FAIL"
        print(f"  [{status}] {key}")
    if results.get("cefr_importers"):
        print(f"  CEFR importers: {', '.join(results['cefr_importers'])}")
    if results.get("duplicated_hits"):
        print(f"  Duplicated hits: {results['duplicated_hits']}")
    print("-" * 44)
    print(f"  OVERALL: {'PASS' if passed else 'FAIL'}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
