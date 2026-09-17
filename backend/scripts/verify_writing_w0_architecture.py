"""Verify Writing W0 architecture foundation.

Usage (from backend/):
    python scripts/verify_writing_w0_architecture.py
"""

from __future__ import annotations

import ast
import importlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

BACKEND = Path(__file__).resolve().parents[1]
SERVICES = BACKEND / "app" / "services"

from app.services.language_writing.ownership import (  # noqa: E402
    ALLOWED_PACKAGE_DEPENDENCIES,
    ARCHITECTURE_LAYERS,
    PACKAGE_LAYER,
    PACKAGE_OWNERSHIP,
    REQUIRED_W0_PACKAGES,
    SHARED_INFRASTRUCTURE,
)


def _ok(name: str, passed: bool, detail: str = "") -> bool:
    status = "PASS" if passed else "FAIL"
    suffix = f" — {detail}" if detail else ""
    print(f"  {name}: {status}{suffix}")
    return passed


def _package_path(name: str) -> Path:
    return SERVICES / name


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
                    pkg = parts[2]
                    # Shared enums live under language_writing/ — not a skill engine package.
                    if pkg == "language_writing":
                        continue
                    if pkg.startswith("language_writing_"):
                        imports.add(pkg)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("app.services."):
                    parts = alias.name.split(".")
                    if len(parts) >= 3:
                        pkg = parts[2]
                        if pkg == "language_writing":
                            continue
                        if pkg.startswith("language_writing_"):
                            imports.add(pkg)
    return imports


def check_packages_exist() -> list[bool]:
    results: list[bool] = []
    for pkg in sorted(REQUIRED_W0_PACKAGES):
        pkg_dir = _package_path(pkg)
        init_file = pkg_dir / "__init__.py"
        types_file = pkg_dir / "types.py"
        results.append(_ok(f"package exists: {pkg}", pkg_dir.is_dir()))
        results.append(_ok(f"  __init__.py: {pkg}", init_file.is_file()))
        results.append(_ok(f"  types.py: {pkg}", types_file.is_file()))
        if init_file.is_file():
            text = init_file.read_text(encoding="utf-8")
            results.append(_ok(f"  RESPONSIBILITY declared: {pkg}", "RESPONSIBILITY" in text))
    return results


def check_ownership_registry() -> list[bool]:
    results: list[bool] = []
    results.append(_ok("ownership count matches required packages", len(PACKAGE_OWNERSHIP) == len(REQUIRED_W0_PACKAGES)))
    dup_values = [k for k, v in PACKAGE_OWNERSHIP.items() if list(PACKAGE_OWNERSHIP.values()).count(v) > 1 and v]
    results.append(_ok("no duplicate ownership descriptions", len(set(PACKAGE_OWNERSHIP.values())) == len(PACKAGE_OWNERSHIP)))
    for pkg in REQUIRED_W0_PACKAGES:
        results.append(_ok(f"ownership entry: {pkg}", pkg in PACKAGE_OWNERSHIP))
    return results


def check_import_graph() -> list[bool]:
    results: list[bool] = []
    writing_deps: dict[str, set[str]] = {}

    for pkg in REQUIRED_W0_PACKAGES:
        pkg_dir = _package_path(pkg)
        deps: set[str] = set()
        for py_file in pkg_dir.glob("*.py"):
            for imp in _parse_imports(py_file):
                if imp.startswith("language_writing"):
                    deps.add(imp)
        writing_deps[pkg] = deps

    # Circular import via importlib (types modules only)
    for pkg in sorted(REQUIRED_W0_PACKAGES):
        module_name = f"app.services.{pkg}.types"
        try:
            importlib.import_module(module_name)
            results.append(_ok(f"import types: {pkg}", True))
        except Exception as exc:  # noqa: BLE001
            results.append(_ok(f"import types: {pkg}", False, str(exc)))

    # Allowed dependencies
    for pkg, deps in writing_deps.items():
        allowed = ALLOWED_PACKAGE_DEPENDENCIES.get(pkg, frozenset())
        for dep in deps:
            if dep == pkg:
                continue  # same-package relative imports are allowed
            if dep not in allowed:
                results.append(_ok(f"dependency allowed: {pkg} -> {dep}", False, f"not in {sorted(allowed)}"))
            else:
                results.append(_ok(f"dependency allowed: {pkg} -> {dep}", True))

    # Layer violations: lower layer must not import higher layer
    layer_index = {name: i for i, name in enumerate(ARCHITECTURE_LAYERS)}
    for pkg, deps in writing_deps.items():
        pkg_layer = PACKAGE_LAYER.get(pkg, "")
        pkg_idx = layer_index.get(pkg_layer, -1)
        for dep in deps:
            dep_layer = PACKAGE_LAYER.get(dep, "")
            dep_idx = layer_index.get(dep_layer, -1)
            if dep_idx > pkg_idx >= 0:
                results.append(
                    _ok(
                        f"layer order: {pkg}({pkg_layer}) -> {dep}({dep_layer})",
                        False,
                        "lower layer imports higher layer",
                    )
                )
    return results


def check_facts_narrative_separation() -> list[bool]:
    results: list[bool] = []
    exp_init = (_package_path("language_writing_explainability") / "__init__.py").read_text(encoding="utf-8")
    journey_init = (_package_path("language_writing_journey") / "__init__.py").read_text(encoding="utf-8")
    lesson_init = (_package_path("language_writing_lesson_experience") / "__init__.py").read_text(encoding="utf-8")

    results.append(_ok("explainability owns facts", "facts" in exp_init.lower()))
    results.append(_ok("journey does not claim facts ownership", "facts assembly" not in journey_init.lower()))
    results.append(_ok("lesson experience forbids journey keys", "FORBIDDEN" in lesson_init or "FORBIDDEN" in (
        _package_path("language_writing_lesson_experience") / "types.py"
    ).read_text(encoding="utf-8")))

    # Portfolio must not import progression
    portfolio_deps = set()
    for py_file in _package_path("language_writing_portfolio").glob("*.py"):
        portfolio_deps |= {d for d in _parse_imports(py_file) if d.startswith("language_writing")}
    results.append(_ok("portfolio isolated from progression", "language_writing_progression" not in portfolio_deps))
    results.append(_ok("portfolio isolated from official_promotion", "language_writing_official_promotion" not in portfolio_deps))
    return results


def check_enums_and_contracts() -> list[bool]:
    results: list[bool] = []
    from app.services.language_writing import enums as writing_enums  # noqa: WPS433

    required_enums = [
        "OfficialWritingCEFR",
        "WritingArc",
        "WritingGoal",
        "WritingCoachPersonality",
        "ContextComplexity",
        "LexisCategory",
        "GrammarState",
        "LexisState",
        "WritingLessonLifecycle",
        "WritingRevisionStatus",
        "PromotionStatus",
    ]
    for name in required_enums:
        results.append(_ok(f"enum: {name}", hasattr(writing_enums, name)))

    contract_modules = [
        ("WritingMission", "app.services.language_writing_lesson_experience.types"),
        ("WritingDraft", "app.services.language_writing_revision.types"),
        ("WritingFeedback", "app.services.language_writing_coach.types"),
        ("WritingLessonFacts", "app.services.language_writing_explainability.types"),
        ("WritingJourneyBundle", "app.services.language_writing_journey.types"),
        ("WritingLessonExperienceBundle", "app.services.language_writing_lesson_experience.types"),
        ("WritingPromotionBundle", "app.services.language_writing_promotion_test.types"),
        ("WritingPortfolioEntry", "app.services.language_writing_portfolio.types"),
        ("TrendFacts", "app.services.language_writing_explainability.types"),
        ("ContextComplexityFacts", "app.services.language_writing_explainability.types"),
        ("WritingGoalProfile", "app.services.language_writing_curriculum.types"),
        ("WritingKnowledgeChainNode", "app.services.language_writing_knowledge_chain.types"),
        ("WritingTopicNode", "app.services.language_writing_topic_universe.types"),
        ("WritingGrammarState", "app.services.language_writing_grammar_progression.types"),
        ("WritingLexisState", "app.services.language_writing_lexis_progression.types"),
    ]
    for class_name, module_path in contract_modules:
        mod = importlib.import_module(module_path)
        results.append(_ok(f"contract: {class_name}", hasattr(mod, class_name)))

    from app.schemas import language_writing_bundles as bundles  # noqa: WPS433

    for schema in (
        "WritingLessonExperienceBundleOut",
        "WritingJourneyBundleOut",
        "WritingPromotionBundleOut",
        "WritingPortfolioEntryOut",
        "WritingFeedbackOut",
    ):
        results.append(_ok(f"api schema: {schema}", hasattr(bundles, schema)))

    return results


def check_schema_plan() -> list[bool]:
    results: list[bool] = []
    plan = BACKEND / "alembic" / "sql" / "W0_writing_schema_plan.sql"
    text = plan.read_text(encoding="utf-8") if plan.is_file() else ""
    for token in (
        "context_complexity",
        "language_writing_portfolio_entry",
        "language_writing_trend_snapshot",
        "language_writing_lexis_state",
        "language_writing_grammar_state",
        "language_writing_chain_progress",
    ):
        results.append(_ok(f"schema plan mentions: {token}", token in text))
    return results


def check_legacy_service_preserved() -> list[bool]:
    results: list[bool] = []
    legacy = SERVICES / "language_writing_service.py"
    results.append(_ok("legacy language_writing_service.py preserved", legacy.is_file()))
    results.append(_ok("legacy service not deleted (W0)", legacy.stat().st_size > 100 if legacy.is_file() else False))
    return results


def check_architecture_violations() -> list[bool]:
    results: list[bool] = []
    # No writing package should import frontend or API layers
    forbidden_prefixes = ("app.api", "src.")
    for pkg in REQUIRED_W0_PACKAGES:
        for py_file in _package_path(pkg).glob("*.py"):
            text = py_file.read_text(encoding="utf-8")
            for prefix in forbidden_prefixes:
                results.append(_ok(f"no {prefix} in {pkg}/{py_file.name}", prefix not in text))
    # Shared infra is documented
    results.append(_ok("shared infrastructure documented", len(SHARED_INFRASTRUCTURE) >= 4))
    return results


def main() -> int:
    print("Writing W0 Architecture Verification\n")
    sections = [
        ("Package layout", check_packages_exist),
        ("Ownership registry", check_ownership_registry),
        ("Import graph & layers", check_import_graph),
        ("Facts/narrative separation", check_facts_narrative_separation),
        ("Enums & contracts", check_enums_and_contracts),
        ("Schema plan", check_schema_plan),
        ("Legacy preservation", check_legacy_service_preserved),
        ("Architecture violations", check_architecture_violations),
    ]

    all_results: list[bool] = []
    for title, fn in sections:
        print(f"[{title}]")
        all_results.extend(fn())
        print()

    passed = sum(all_results)
    total = len(all_results)
    print(f"Summary: {passed}/{total} checks passed")
    if passed == total:
        print("W0 READY — W1 may begin after review.")
        return 0
    print("W0 NOT READY — fix failures before W1.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
