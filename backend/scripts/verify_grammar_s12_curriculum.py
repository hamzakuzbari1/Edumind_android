"""Verify Grammar S12 — file curriculum SSOT + Target Resolver foundation.

Usage (from backend/):
    python scripts/verify_grammar_s12_curriculum.py
"""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

BACKEND = Path(__file__).resolve().parents[1]
CURRICULUM = BACKEND / "curriculum" / "english" / "grammar"
SERVICES = BACKEND / "app" / "services"


def _ok(name: str, passed: bool, detail: str = "") -> bool:
    status = "PASS" if passed else "FAIL"
    suffix = f" - {detail}" if detail else ""
    print(f"  {name}: {status}{suffix}")
    return passed


def audit_files() -> list[bool]:
    print("[Audit 1 - Curriculum files]")
    results: list[bool] = []
    from app.services.language_grammar_catalog.schema import EXPECTED_TOPIC_COUNT

    results.append(_ok("curriculum dir exists", CURRICULUM.is_dir(), str(CURRICULUM)))
    index = CURRICULUM / "_index.yaml"
    results.append(_ok("_index.yaml exists", index.is_file()))
    topic_files = sorted(CURRICULUM.glob("gram_*.yaml"))
    results.append(
        _ok(
            f"topic file count == {EXPECTED_TOPIC_COUNT}",
            len(topic_files) == EXPECTED_TOPIC_COUNT,
            f"count={len(topic_files)}",
        )
    )
    return results


def audit_loader_catalog() -> list[bool]:
    print("[Audit 2 - Loader == catalog snapshot]")
    results: list[bool] = []
    from app.services.language_grammar_catalog.catalog import (  # noqa: WPS433
        reload_english_catalog,
        validate_default_catalog,
    )
    from app.services.language_grammar_catalog.loader import load_grammar_curriculum  # noqa: WPS433
    from app.services.language_grammar_catalog.schema import (  # noqa: WPS433
        ENGLISH_CEFR_QUOTAS,
        EXPECTED_TOPIC_COUNT,
    )

    try:
        loaded = load_grammar_curriculum("en")
        results.append(_ok("loader succeeds", True, f"topics={len(loaded.topics)}"))
    except Exception as exc:  # noqa: BLE001
        results.append(_ok("loader succeeds", False, str(exc)))
        return results

    integrity, curriculum = validate_default_catalog()
    results.append(_ok("catalog integrity", integrity.valid, f"issues={len(integrity.issues)}"))
    if not integrity.valid:
        for issue in integrity.issues[:8]:
            results.append(_ok(f"integrity:{issue.code}", False, f"{issue.grammar_id} {issue.message}"))
    results.append(_ok("curriculum progression", curriculum.valid, f"issues={len(curriculum.issues)}"))

    catalog = reload_english_catalog()
    results.append(
        _ok(
            f"topic count == {EXPECTED_TOPIC_COUNT}",
            len(catalog.topics) == EXPECTED_TOPIC_COUNT,
        )
    )
    counts = Counter(t.cefr_band.value for t in catalog.topics)
    results.append(_ok("CEFR quotas", dict(counts) == ENGLISH_CEFR_QUOTAS, str(dict(counts))))

    ids = [t.grammar_id for t in catalog.topics]
    codes = [t.display_code for t in catalog.topics]
    results.append(_ok("grammar_id unique", len(ids) == len(set(ids))))
    results.append(_ok("display_code unique", len(codes) == len(set(codes))))
    results.append(_ok("all grammar_id gram_*", all(i.startswith("gram_") for i in ids)))
    expected_codes = {f"G{i:03d}" for i in range(1, EXPECTED_TOPIC_COUNT + 1)}
    results.append(
        _ok(
            f"display_code G001-G{EXPECTED_TOPIC_COUNT:03d}",
            set(codes) == expected_codes,
        )
    )

    # Rank by introduction_order must match G00x
    ordered = sorted(catalog.topics, key=lambda t: (t.introduction_order, t.grammar_id))
    rank_ok = all(t.display_code == f"G{i:03d}" for i, t in enumerate(ordered, start=1))
    results.append(_ok("display_code follows introduction_order", rank_ok))

    # Existing speaking-critical IDs still present
    for required in (
        "gram_be_present",
        "gram_present_simple",
        "gram_past_simple",
        "gram_present_perfect",
        "gram_passive_voice",
    ):
        results.append(_ok(f"retained:{required}", required in set(ids)))

    return results


def audit_id_policy() -> list[bool]:
    print("[Audit 3 - ID policy: gram_* canonical, G00x display only]")
    results: list[bool] = []
    from app.services.language_grammar.id_canon import (  # noqa: WPS433
        assert_canonical_grammar_id,
        assert_grammar_display_code,
        is_canonical_grammar_id,
        is_grammar_display_code,
    )

    results.append(_ok("gram_be_present canonical", is_canonical_grammar_id("gram_be_present")))
    results.append(_ok("G001 not canonical grammar_id", not is_canonical_grammar_id("G001")))
    results.append(_ok("G001 is display_code", is_grammar_display_code("G001")))
    try:
        assert_canonical_grammar_id("G001")
        results.append(_ok("assert rejects G001 as grammar_id", False))
    except ValueError:
        results.append(_ok("assert rejects G001 as grammar_id", True))
    try:
        assert_grammar_display_code("gram_be_present")
        results.append(_ok("assert rejects gram_* as display_code", False))
    except ValueError:
        results.append(_ok("assert rejects gram_* as display_code", True))
    return results


def audit_target_resolver() -> list[bool]:
    print("[Audit 4 - Grammar Target Resolver facade]")
    results: list[bool] = []
    pkg = SERVICES / "language_grammar_target_resolver"
    results.append(_ok("package exists", (pkg / "__init__.py").is_file()))
    results.append(_ok("types.py exists", (pkg / "types.py").is_file()))
    results.append(_ok("service.py exists", (pkg / "service.py").is_file()))

    from app.services.language_grammar.ownership import (  # noqa: WPS433
        ALLOWED_PACKAGE_DEPENDENCIES,
        PACKAGE_LAYER,
        PACKAGE_OWNERSHIP,
    )
    from app.services.language_grammar_target_resolver import (  # noqa: WPS433
        GrammarTargetResolver,
        GrammarTargetResolveRequest,
        resolve_from_snapshot,
    )

    results.append(_ok("ownership registered", "language_grammar_target_resolver" in PACKAGE_OWNERSHIP))
    results.append(
        _ok(
            "layer == target_resolver",
            PACKAGE_LAYER.get("language_grammar_target_resolver") == "target_resolver",
        )
    )
    deps = ALLOWED_PACKAGE_DEPENDENCIES.get("language_grammar_target_resolver", frozenset())
    results.append(_ok("may depend on integration", "language_grammar_integration" in deps))
    results.append(_ok("may depend on catalog", "language_grammar_catalog" in deps))
    results.append(_ok("exports GrammarTargetResolver", GrammarTargetResolver is not None))
    results.append(_ok("exports resolve_from_snapshot", callable(resolve_from_snapshot)))
    results.append(
        _ok(
            "request type has source_skill",
            hasattr(GrammarTargetResolveRequest, "__annotations__")
            and "source_skill" in GrammarTargetResolveRequest.__annotations__,
        )
    )
    return results


def audit_language_path() -> list[bool]:
    print("[Audit 5 - Language-scoped curriculum path]")
    results: list[bool] = []
    from app.services.language_grammar_catalog.loader import (  # noqa: WPS433
        curriculum_root,
        language_curriculum_dir,
    )

    root = curriculum_root()
    results.append(_ok("curriculum root ends with curriculum", root.name == "curriculum", str(root)))
    en = language_curriculum_dir("en")
    results.append(_ok("en maps to english/grammar", en == root / "english" / "grammar", str(en)))
    try:
        language_curriculum_dir("fr")
        results.append(_ok("unsupported language raises", False))
    except ValueError:
        results.append(_ok("unsupported language raises", True))
    return results


def main() -> int:
    print("=== Grammar S12 Curriculum Verification ===")
    results: list[bool] = []
    results.extend(audit_files())
    results.extend(audit_loader_catalog())
    results.extend(audit_id_policy())
    results.extend(audit_target_resolver())
    results.extend(audit_language_path())
    passed = sum(1 for r in results if r)
    failed = len(results) - passed
    print(f"\nResult: {passed} passed, {failed} failed, {len(results)} total")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
