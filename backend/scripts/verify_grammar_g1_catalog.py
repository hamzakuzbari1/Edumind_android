"""Verify Grammar G1 Catalog Foundation.

Usage (from backend/):
    python scripts/verify_grammar_g1_catalog.py
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

BACKEND = Path(__file__).resolve().parents[1]
SERVICES = BACKEND / "app" / "services"
CATALOG_PKG = SERVICES / "language_grammar_catalog"


def _ok(name: str, passed: bool, detail: str = "") -> bool:
    status = "PASS" if passed else "FAIL"
    suffix = f" - {detail}" if detail else ""
    print(f"  {name}: {status}{suffix}")
    return passed


def _parse_imports(py_file: Path) -> set[str]:
    try:
        tree = ast.parse(py_file.read_text(encoding="utf-8"))
    except SyntaxError as exc:
        raise RuntimeError(f"Syntax error in {py_file}: {exc}") from exc
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            if node.module.startswith("app.services."):
                parts = node.module.split(".")
                if len(parts) >= 3:
                    imports.add(parts[2])
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("app.services."):
                    parts = alias.name.split(".")
                    if len(parts) >= 3:
                        imports.add(parts[2])
    return imports


def audit_1_catalog_integrity() -> list[bool]:
    print("[Audit 1 - Catalog Integrity]")
    results: list[bool] = []
    from app.services.language_grammar_catalog.catalog import (  # noqa: WPS433
        get_english_catalog,
        validate_default_catalog,
    )
    from app.services.language_grammar_catalog.validation import REQUIRED_METADATA_ATTRS  # noqa: WPS433

    integrity, _curriculum = validate_default_catalog()
    if integrity.valid:
        results.append(_ok("catalog integrity validation", True))
    else:
        for issue in integrity.issues[:12]:
            results.append(_ok(f"integrity:{issue.code}", False, f"{issue.grammar_id} {issue.message}"))
        if len(integrity.issues) > 12:
            results.append(_ok("integrity remaining issues truncated", False, str(len(integrity.issues) - 12)))

    catalog = get_english_catalog()
    ids = [t.grammar_id for t in catalog.topics]
    results.append(_ok("all IDs unique", len(ids) == len(set(ids)), f"count={len(ids)}"))
    results.append(_ok("no empty catalog", len(ids) > 0))

    for topic in catalog.topics:
        missing = [a for a in REQUIRED_METADATA_ATTRS if not hasattr(topic, a)]
        if missing:
            results.append(_ok(f"metadata:{topic.grammar_id}", False, str(missing)))
        if not topic.prerequisite_ids and topic.grammar_id != "gram_be_present":
            # roots are allowed; only ensure at least one root exists (checked in validator)
            pass
        if len(topic.prerequisite_ids) != len(set(topic.prerequisite_ids)):
            results.append(_ok(f"dup parents:{topic.grammar_id}", False))

    # Broken links / cycles already in integrity; surface summary
    results.append(_ok("no circular dependencies", all(i.code != "circular_dependency" for i in integrity.issues)))
    results.append(_ok("no broken prerequisite links", all(i.code != "broken_prerequisite" for i in integrity.issues)))
    results.append(_ok("Audit 1 verdict", integrity.valid and len(ids) == len(set(ids))))
    print()
    return results


def audit_2_curriculum_integrity() -> list[bool]:
    print("[Audit 2 - Curriculum Integrity]")
    results: list[bool] = []
    from app.services.language_grammar.enums import GrammarCEFRBand  # noqa: WPS433
    from app.services.language_grammar_catalog.catalog import (  # noqa: WPS433
        get_english_catalog,
        validate_default_catalog,
    )
    from app.services.language_grammar_catalog.cefr_order import CEFR_SEQUENCE  # noqa: WPS433

    _integrity, curriculum = validate_default_catalog()
    if curriculum.valid:
        results.append(_ok("curriculum validation", True))
    else:
        for issue in curriculum.issues[:12]:
            results.append(_ok(f"curriculum:{issue.code}", False, f"{issue.grammar_id} {issue.message}"))

    catalog = get_english_catalog()
    for band in CEFR_SEQUENCE:
        band_topics = catalog.topics_for_band(band)
        results.append(_ok(f"{band.value} progression present", len(band_topics) > 0, f"n={len(band_topics)}"))
        orders = [t.introduction_order for t in band_topics]
        results.append(_ok(f"{band.value} introduction_order increasing", orders == sorted(orders)))

    # Spot-check known unlock chains
    by_id = {t.grammar_id: t for t in catalog.topics}
    chains = [
        ("gram_be_present", "gram_present_simple"),
        ("gram_present_simple", "gram_past_simple"),
        ("gram_past_simple", "gram_present_perfect"),
        ("gram_first_conditional", "gram_second_conditional"),
        ("gram_passive_voice", "gram_causatives_basic"),
    ]
    for parent, child in chains:
        results.append(
            _ok(
                f"unlock {parent} -> {child}",
                parent in by_id[child].prerequisite_ids,
            )
        )

    results.append(_ok("Audit 2 verdict", curriculum.valid))
    print()
    return results


def audit_3_architecture_integrity() -> list[bool]:
    print("[Audit 3 - Architecture Integrity]")
    results: list[bool] = []
    forbidden = {
        "language_grammar_progression",
        "language_grammar_mastery",
        "language_grammar_review",
        "language_grammar_lesson_planner",
        "language_grammar_lesson_runtime",
        "language_grammar_educational_package",
        "language_grammar_analytics",
        "language_grammar_integration",
        "language_grammar_evidence",
        "claude_service",
    }
    catalog_deps: set[str] = set()
    for py_file in CATALOG_PKG.glob("*.py"):
        catalog_deps |= _parse_imports(py_file)

    for dep in sorted(forbidden):
        results.append(_ok(f"catalog does not import {dep}", dep not in catalog_deps))

    # Allowed: language_grammar shared only
    unexpected = {
        d
        for d in catalog_deps
        if d.startswith("language_grammar_") and d != "language_grammar_catalog"
    }
    # language_grammar shared core is allowed; ensure no other grammar_* engines
    results.append(_ok("catalog has no grammar engine package deps", not unexpected, str(sorted(unexpected))))

    # No engine modules for progression/mastery/etc created by this phase inside catalog
    for name in ("engine.py", "storage.py", "runtime.py"):
        results.append(_ok(f"catalog has no {name}", not (CATALOG_PKG / name).is_file()))

    results.append(_ok("Audit 3 verdict", all(results)))
    print()
    return results


def audit_4_migration_safety() -> list[bool]:
    print("[Audit 4 - Migration Safety]")
    results: list[bool] = []
    from app.services.language_grammar.enums import GrammarLegacyIdKind  # noqa: WPS433
    from app.services.language_grammar_catalog.catalog import all_grammar_ids, get_topic  # noqa: WPS433
    from app.services.language_grammar_legacy_bridge.maps import (  # noqa: WPS433
        BKT_GRAMMAR_TO_GRAMMAR_ID,
        SPEAKING_GRAM_IDS,
        WRITING_STRUCTURE_TO_GRAMMAR_ID,
        resolve_legacy_grammar_id,
    )
    from app.services.language_speaking_curriculum_engine.grammar_catalog import (  # noqa: WPS433
        select_grammar_targets,
    )

    catalog_ids = all_grammar_ids()
    missing_speaking = sorted(SPEAKING_GRAM_IDS - catalog_ids)
    results.append(_ok("all speaking gram_* IDs in catalog", not missing_speaking, str(missing_speaking)))

    for code, gid in BKT_GRAMMAR_TO_GRAMMAR_ID.items():
        results.append(_ok(f"BKT map target in catalog: {code}", gid in catalog_ids))

    for structure_id, gid in WRITING_STRUCTURE_TO_GRAMMAR_ID.items():
        results.append(_ok(f"writing map target in catalog: {structure_id}", gid in catalog_ids))

    results.append(
        _ok(
            "legacy speaking resolve",
            resolve_legacy_grammar_id("gram_passive_voice", kind=GrammarLegacyIdKind.speaking_gram)
            == "gram_passive_voice",
        )
    )
    results.append(
        _ok(
            "legacy BKT resolve",
            resolve_legacy_grammar_id("grammar.present_simple", kind=GrammarLegacyIdKind.bkt_grammar)
            == "gram_present_simple",
        )
    )

    # Speaking projection consumes catalog (no local topic authorship)
    speaking_src = (
        SERVICES / "language_speaking_curriculum_engine" / "grammar_catalog.py"
    ).read_text(encoding="utf-8")
    results.append(_ok("speaking grammar_catalog imports shared catalog", "language_grammar_catalog" in speaking_src))
    results.append(_ok("speaking grammar_catalog does not define local _g topics", "def _g(" not in speaking_src))

    targets = select_grammar_targets(cefr="B2", count=2)
    results.append(_ok("speaking select_grammar_targets works", len(targets) == 2))
    results.append(_ok("speaking targets resolve in catalog", all(get_topic(t.grammar_topic_id) for t in targets)))

    # Ownership: only catalog package defines GrammarTopic registry content
    results.append(
        _ok(
            "english registry lives under language_grammar_catalog",
            (CATALOG_PKG / "english_catalog_v1.py").is_file(),
        )
    )

    results.append(_ok("Audit 4 verdict", not missing_speaking and "language_grammar_catalog" in speaking_src))
    print()
    return results


def self_review_checks() -> list[bool]:
    print("[Self-review checks]")
    results: list[bool] = []
    from app.services.language_grammar_catalog.catalog import get_english_catalog  # noqa: WPS433

    catalog = get_english_catalog()
    # Scaling: introduction_order unique and sparse-ish (room to insert)
    orders = [t.introduction_order for t in catalog.topics]
    results.append(_ok("introduction_order unique", len(orders) == len(set(orders))))
    sorted_orders = sorted(orders)
    gaps = [sorted_orders[i + 1] - sorted_orders[i] for i in range(len(sorted_orders) - 1)]
    results.append(_ok("introduction_order has insert gaps", bool(gaps) and all(g >= 10 for g in gaps)))

    # No topic with all four reinforcement skills (anti-hardcoding)
    four = 0
    for t in catalog.topics:
        if len(t.best_reinforcement_skills) >= 4:
            four += 1
    results.append(_ok("no topic hardcodes all four skills", four == 0, f"offenders={four}"))

    # Future edges derived consistently
    by_id = {t.grammar_id: t for t in catalog.topics}
    inconsistent = 0
    for t in catalog.topics:
        for fut in t.future_topic_ids:
            if t.grammar_id not in by_id[fut].prerequisite_ids:
                inconsistent += 1
    results.append(_ok("future edges consistent with prerequisites", inconsistent == 0))

    # Package version bumped for G1
    from app.services import language_grammar_catalog as pkg  # noqa: WPS433

    results.append(_ok("package version is 1.x", pkg.PACKAGE_VERSION.startswith("1.")))
    print()
    return results


def main() -> int:
    print("Grammar G1 Catalog Foundation verification\n")
    all_results: list[bool] = []
    all_results.extend(audit_1_catalog_integrity())
    all_results.extend(audit_2_curriculum_integrity())
    all_results.extend(audit_3_architecture_integrity())
    all_results.extend(audit_4_migration_safety())
    all_results.extend(self_review_checks())

    passed = sum(1 for r in all_results if r)
    failed = sum(1 for r in all_results if not r)
    print(f"Summary: {passed} passed, {failed} failed, {len(all_results)} total")
    if failed:
        print("G1 VERDICT: NOT READY")
        return 1
    print("G1 VERDICT: READY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
