"""Verify the centralized Listening CEFR profile engine (Phase 1.2).

Usage (from backend/):
    python scripts/verify_language_cefr_profile_engine.py
"""

from __future__ import annotations

import dataclasses
import inspect
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

BACKEND = Path(__file__).resolve().parents[1]

REQUIRED_PROFILE_FIELDS = (
    "level",
    "transcript_min_words",
    "transcript_max_words",
    "ideal_word_count",
    "sentence_min_words",
    "sentence_max_words",
    "allowed_grammar",
    "forbidden_grammar",
    "vocabulary_band",
    "topic_complexity",
    "listening_objectives",
    "allowed_question_types",
    "forbidden_question_types",
    "distractor_complexity",
    "inference_level",
    "cognitive_load",
    "recommended_speaking_speed",
    "recommended_accent",
    "learning_goal",
)


def _is_non_empty(value: object) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (tuple, list)):
        return len(value) > 0
    return True


def audit() -> dict[str, bool | str | int]:
    from app.models.language.enums import LanguageLevel
    from app.services.language_cefr import (
        CEFR_LEVEL_CODES,
        CEFR_LEVELS,
        CefrListeningProfile,
        ListeningQuestionType,
        get_all_cefr_profiles,
        get_allowed_question_types,
        get_cefr_profile,
        get_sentence_limits,
        get_word_limits,
        validate_level_exists,
    )
    from app.services.language_cefr.listening_profiles import LISTENING_CEFR_PROFILES

    results: dict[str, bool | str | int] = {}

    # Every level exists
    results["six_levels_registered"] = len(LISTENING_CEFR_PROFILES) == 6
    results["cefr_levels_match_enum"] = CEFR_LEVELS == tuple(LanguageLevel)
    results["level_codes_complete"] = CEFR_LEVEL_CODES == ("A1", "A2", "B1", "B2", "C1", "C2")

    # Every profile complete
    profiles = get_all_cefr_profiles()
    results["profile_count"] = len(profiles)
    incomplete: list[str] = []
    ordering_errors: list[str] = []
    limit_errors: list[str] = []
    overlap_errors: list[str] = []

    for expected, profile in zip(CEFR_LEVELS, profiles, strict=True):
        if profile.level != expected:
            ordering_errors.append(f"{profile.level} != {expected}")

        for field in REQUIRED_PROFILE_FIELDS:
            value = getattr(profile, field)
            if field in ("forbidden_grammar", "forbidden_question_types"):
                if value is None or not isinstance(value, tuple):
                    incomplete.append(f"{profile.level.value}.{field}")
            elif not _is_non_empty(value):
                incomplete.append(f"{profile.level.value}.{field}")

        if profile.transcript_min_words > profile.ideal_word_count:
            limit_errors.append(f"{profile.level.value}: min > ideal")
        if profile.ideal_word_count > profile.transcript_max_words:
            limit_errors.append(f"{profile.level.value}: ideal > max")
        if profile.sentence_min_words > profile.sentence_max_words:
            limit_errors.append(f"{profile.level.value}: sentence min > max")

        allowed = set(profile.allowed_question_types)
        forbidden = set(profile.forbidden_question_types)
        if allowed & forbidden:
            overlap_errors.append(f"{profile.level.value}: allowed/forbidden overlap")

    results["profiles_complete"] = not incomplete
    results["profiles_ordered"] = not ordering_errors
    results["word_limits_valid"] = not limit_errors
    results["question_types_disjoint"] = not overlap_errors
    if incomplete:
        results["incomplete_fields"] = ", ".join(incomplete[:8])
    if ordering_errors:
        results["ordering_errors"] = "; ".join(ordering_errors)
    if limit_errors:
        results["limit_errors"] = "; ".join(limit_errors)
    if overlap_errors:
        results["overlap_errors"] = "; ".join(overlap_errors)

    # API works
    api_ok = True
    try:
        a1 = get_cefr_profile("a1")
        assert a1.level == LanguageLevel.A1
        assert validate_level_exists("B2")
        assert not validate_level_exists("X9")
        wl = get_word_limits(LanguageLevel.C1)
        assert wl.min_words < wl.ideal_words < wl.max_words
        sl = get_sentence_limits("C2")
        assert sl.min_words <= sl.max_words
        qtypes = get_allowed_question_types("A1")
        assert len(qtypes) >= 1
        assert ListeningQuestionType.inference not in qtypes
        assert ListeningQuestionType.inference in get_cefr_profile("A1").forbidden_question_types
    except Exception as exc:  # pragma: no cover - audit script
        api_ok = False
        results["api_error"] = str(exc)
    results["api_works"] = api_ok

    # Immutability
    results["profile_frozen"] = dataclasses.is_dataclass(CefrListeningProfile) and getattr(
        CefrListeningProfile, "__dataclass_params__"
    ).frozen

    # No duplicated constants inside the engine package
    pkg_dir = BACKEND / "app/services/language_cefr"
    pkg_text = "\n".join(p.read_text(encoding="utf-8") for p in pkg_dir.glob("*.py"))
    duplicate_word_targets = "WORDS_FOR_LEVEL =" in pkg_text or "WORDS_FOR_LEVEL=" in pkg_text
    duplicate_level_guidance = "LEVEL_GUIDANCE =" in pkg_text or "LEVEL_GUIDANCE=" in pkg_text
    results["no_words_for_level_in_engine"] = not duplicate_word_targets
    results["no_level_guidance_in_engine"] = not duplicate_level_guidance

    # Single registry for numeric transcript targets (ideal counts appear once per level file section)
    ideal_counts = [p.ideal_word_count for p in profiles]
    results["ideal_counts_unique"] = len(ideal_counts) == len(set(ideal_counts))

    # Future modules can import from package root
    import_ok = True
    try:
        import app.services.language_cefr as cefr  # noqa: F401

        assert hasattr(cefr, "get_cefr_profile")
    except Exception as exc:  # pragma: no cover
        import_ok = False
        results["import_error"] = str(exc)
    results["package_importable"] = import_ok

    # Document public API surface
    results["public_api_functions"] = len(
        [name for name, obj in inspect.getmembers(sys.modules["app.services.language_cefr"]) if inspect.isfunction(obj)]
    )

    return results


def main() -> int:
    results = audit()
    checks = [
        "six_levels_registered",
        "cefr_levels_match_enum",
        "level_codes_complete",
        "profiles_complete",
        "profiles_ordered",
        "word_limits_valid",
        "question_types_disjoint",
        "api_works",
        "profile_frozen",
        "no_words_for_level_in_engine",
        "no_level_guidance_in_engine",
        "ideal_counts_unique",
        "package_importable",
    ]
    passed = all(bool(results.get(k)) for k in checks)

    print("LANGUAGE-CEFR-PHASE-1.2 VERIFICATION")
    print("=" * 44)
    for key in checks:
        status = "PASS" if results.get(key) else "FAIL"
        extra = ""
        if not results.get(key) and key in results:
            for detail_key in ("incomplete_fields", "ordering_errors", "limit_errors", "overlap_errors", "api_error", "import_error"):
                if detail_key in results and key in (
                    "profiles_complete",
                    "profiles_ordered",
                    "word_limits_valid",
                    "question_types_disjoint",
                    "api_works",
                    "package_importable",
                ):
                    extra = f" ({results[detail_key]})"
                    break
        print(f"  [{status}] {key}{extra}")

    print("-" * 44)
    print(f"  Profiles audited: {results.get('profile_count', 0)}")
    print(f"  Public API functions: {results.get('public_api_functions', 0)}")
    print(f"  OVERALL: {'PASS' if passed else 'FAIL'}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
