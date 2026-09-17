"""Verify Grammar G0 architecture foundation.

Usage (from backend/):
    python scripts/verify_grammar_g0_architecture.py
"""

from __future__ import annotations

import ast
import importlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

BACKEND = Path(__file__).resolve().parents[1]
SERVICES = BACKEND / "app" / "services"

from app.services.language_grammar.ownership import (  # noqa: E402
    ADAPTIVE_JSONB_NAMESPACE_RESERVED,
    AI_TEACHER_JSONB_NAMESPACE_RESERVED,
    AI_TUTOR_COACHING_JSONB_NAMESPACE_RESERVED,
    AI_TUTOR_JSONB_NAMESPACE_RESERVED,
    ALLOWED_PACKAGE_DEPENDENCIES,
    ARCHITECTURE_LAYERS,
    EVIDENCE_TO_MASTERY_BRIDGE,
    FORBIDDEN_MASTERY_WRITERS,
    GRAMMAR_JSONB_NAMESPACE,
    MASTERY_WRITE_OWNER,
    PACKAGE_LAYER,
    PACKAGE_OWNERSHIP,
    REQUIRED_G0_PACKAGES,
    VOCABULARY_JSONB_NAMESPACE_RESERVED,
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
                    if pkg == "language_grammar":
                        continue
                    if pkg.startswith("language_grammar_"):
                        imports.add(pkg)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("app.services."):
                    parts = alias.name.split(".")
                    if len(parts) >= 3:
                        pkg = parts[2]
                        if pkg == "language_grammar":
                            continue
                        if pkg.startswith("language_grammar_"):
                            imports.add(pkg)
    return imports


def check_packages_exist() -> list[bool]:
    results: list[bool] = []
    for pkg in sorted(REQUIRED_G0_PACKAGES):
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
    results.append(
        _ok(
            "ownership count matches required packages",
            len(PACKAGE_OWNERSHIP) == len(REQUIRED_G0_PACKAGES),
        )
    )
    results.append(
        _ok(
            "no duplicate ownership descriptions",
            len(set(PACKAGE_OWNERSHIP.values())) == len(PACKAGE_OWNERSHIP),
        )
    )
    for pkg in REQUIRED_G0_PACKAGES:
        results.append(_ok(f"ownership entry: {pkg}", pkg in PACKAGE_OWNERSHIP))
    results.append(_ok("mastery write owner is mastery package", MASTERY_WRITE_OWNER == "language_grammar_mastery"))
    results.append(
        _ok(
            "evidence is sole skill->mastery bridge",
            EVIDENCE_TO_MASTERY_BRIDGE == "language_grammar_evidence",
        )
    )
    results.append(
        _ok(
            "evidence package cannot write mastery scores",
            EVIDENCE_TO_MASTERY_BRIDGE in FORBIDDEN_MASTERY_WRITERS,
        )
    )
    results.append(
        _ok(
            "JSONB grammar namespace reserved",
            GRAMMAR_JSONB_NAMESPACE == "grammar",
        )
    )
    results.append(
        _ok(
            "JSONB vocabulary sibling reserved distinctly",
            VOCABULARY_JSONB_NAMESPACE_RESERVED == "vocabulary"
            and VOCABULARY_JSONB_NAMESPACE_RESERVED != GRAMMAR_JSONB_NAMESPACE,
        )
    )
    results.append(
        _ok(
            "JSONB adaptive sibling reserved distinctly",
            ADAPTIVE_JSONB_NAMESPACE_RESERVED == "adaptive_intelligence"
            and ADAPTIVE_JSONB_NAMESPACE_RESERVED != GRAMMAR_JSONB_NAMESPACE
            and ADAPTIVE_JSONB_NAMESPACE_RESERVED != VOCABULARY_JSONB_NAMESPACE_RESERVED,
        )
    )
    results.append(
        _ok(
            "JSONB ai_tutor sibling reserved distinctly",
            AI_TUTOR_JSONB_NAMESPACE_RESERVED == "ai_tutor"
            and AI_TUTOR_JSONB_NAMESPACE_RESERVED != GRAMMAR_JSONB_NAMESPACE
            and AI_TUTOR_JSONB_NAMESPACE_RESERVED != ADAPTIVE_JSONB_NAMESPACE_RESERVED
            and AI_TUTOR_JSONB_NAMESPACE_RESERVED != VOCABULARY_JSONB_NAMESPACE_RESERVED,
        )
    )
    results.append(
        _ok(
            "JSONB ai_tutor_coaching sibling reserved distinctly",
            AI_TUTOR_COACHING_JSONB_NAMESPACE_RESERVED == "ai_tutor_coaching"
            and AI_TUTOR_COACHING_JSONB_NAMESPACE_RESERVED != AI_TUTOR_JSONB_NAMESPACE_RESERVED
            and AI_TUTOR_COACHING_JSONB_NAMESPACE_RESERVED != GRAMMAR_JSONB_NAMESPACE
            and AI_TUTOR_COACHING_JSONB_NAMESPACE_RESERVED != ADAPTIVE_JSONB_NAMESPACE_RESERVED,
        )
    )
    results.append(
        _ok(
            "JSONB ai_teacher sibling reserved distinctly",
            AI_TEACHER_JSONB_NAMESPACE_RESERVED == "ai_teacher"
            and AI_TEACHER_JSONB_NAMESPACE_RESERVED != AI_TUTOR_COACHING_JSONB_NAMESPACE_RESERVED
            and AI_TEACHER_JSONB_NAMESPACE_RESERVED != GRAMMAR_JSONB_NAMESPACE
            and AI_TEACHER_JSONB_NAMESPACE_RESERVED != ADAPTIVE_JSONB_NAMESPACE_RESERVED,
        )
    )
    return results


def check_import_graph() -> list[bool]:
    results: list[bool] = []
    grammar_deps: dict[str, set[str]] = {}

    for pkg in REQUIRED_G0_PACKAGES:
        pkg_dir = _package_path(pkg)
        deps: set[str] = set()
        for py_file in pkg_dir.glob("*.py"):
            for imp in _parse_imports(py_file):
                if imp.startswith("language_grammar"):
                    deps.add(imp)
        grammar_deps[pkg] = deps

    for pkg in sorted(REQUIRED_G0_PACKAGES):
        module_name = f"app.services.{pkg}.types"
        try:
            importlib.import_module(module_name)
            results.append(_ok(f"import types: {pkg}", True))
        except Exception as exc:  # noqa: BLE001
            results.append(_ok(f"import types: {pkg}", False, str(exc)))

    for pkg, deps in grammar_deps.items():
        allowed = ALLOWED_PACKAGE_DEPENDENCIES.get(pkg, frozenset())
        for dep in deps:
            if dep == pkg:
                continue
            if dep not in allowed:
                results.append(
                    _ok(f"dependency allowed: {pkg} -> {dep}", False, f"not in {sorted(allowed)}")
                )
            else:
                results.append(_ok(f"dependency allowed: {pkg} -> {dep}", True))

    layer_index = {name: i for i, name in enumerate(ARCHITECTURE_LAYERS)}
    for pkg, deps in grammar_deps.items():
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


def check_enums_and_contracts() -> list[bool]:
    results: list[bool] = []
    from app.services.language_grammar import enums as grammar_enums  # noqa: WPS433
    from app.services.language_grammar.id_canon import (  # noqa: WPS433
        assert_canonical_grammar_id,
        is_canonical_grammar_id,
    )

    required_enums = [
        "GrammarCEFRBand",
        "GrammarMasteryState",
        "GrammarReinforcementSkill",
        "GrammarLessonStepKind",
        "GrammarObservationType",
        "GrammarEvidenceSourceSkill",
        "GrammarLegacyIdKind",
    ]
    for name in required_enums:
        results.append(_ok(f"enum: {name}", hasattr(grammar_enums, name)))

    contract_modules = [
        ("GrammarTopic", "app.services.language_grammar_catalog.types"),
        ("GrammarMasteryRecord", "app.services.language_grammar_mastery.types"),
        ("GrammarMasteryDimensions", "app.services.language_grammar_mastery.types"),
        ("PublicGrammarMasteryView", "app.services.language_grammar_mastery.types"),
        ("GrammarEvidenceObservation", "app.services.language_grammar_evidence.types"),
        ("GrammarReviewQueue", "app.services.language_grammar_review.types"),
        ("GrammarProgressionSnapshot", "app.services.language_grammar_progression.types"),
        ("GrammarLessonBlueprint", "app.services.language_grammar_lesson_planner.types"),
        ("GrammarLessonStep", "app.services.language_grammar_lesson_planner.types"),
        ("GrammarPackageConstraints", "app.services.language_grammar_educational_package.types"),
        ("GrammarRuntimeSession", "app.services.language_grammar_lesson_runtime.types"),
        ("GrammarRuntimeCursor", "app.services.language_grammar_lesson_runtime.types"),
        ("GrammarAnalyticsProjection", "app.services.language_grammar_analytics.types"),
        ("GrammarResolveTargetsRequest", "app.services.language_grammar_integration.types"),
        ("GrammarLegacyMapping", "app.services.language_grammar_legacy_bridge.types"),
    ]
    for class_name, module_path in contract_modules:
        mod = importlib.import_module(module_path)
        results.append(_ok(f"contract: {class_name}", hasattr(mod, class_name)))

    results.append(_ok("canonical id accepts gram_present_simple", is_canonical_grammar_id("gram_present_simple")))
    results.append(_ok("canonical id rejects structure_x", not is_canonical_grammar_id("structure_present_simple")))
    try:
        assert_canonical_grammar_id("gram_passive_voice")
        results.append(_ok("assert_canonical_grammar_id accepts valid", True))
    except ValueError as exc:
        results.append(_ok("assert_canonical_grammar_id accepts valid", False, str(exc)))
    try:
        assert_canonical_grammar_id("grammar.present_simple")
        results.append(_ok("assert_canonical_grammar_id rejects BKT", False, "should have raised"))
    except ValueError:
        results.append(_ok("assert_canonical_grammar_id rejects BKT", True))

    return results


def check_blueprint_and_catalog_contracts() -> list[bool]:
    results: list[bool] = []
    from app.services.language_grammar.enums import (  # noqa: WPS433
        GrammarCEFRBand,
        GrammarLessonStepKind,
        GrammarReinforcementSkill,
    )
    from app.services.language_grammar_catalog.types import GrammarTopic  # noqa: WPS433
    from app.services.language_grammar_lesson_planner.types import (  # noqa: WPS433
        GrammarLessonBlueprint,
        GrammarLessonStep,
    )
    from app.services.language_grammar_lesson_runtime.types import GrammarRuntimeCursor  # noqa: WPS433
    from app.services.language_grammar_mastery.types import (  # noqa: WPS433
        GrammarMasteryDimensions,
        GrammarMasteryRecord,
        PublicGrammarMasteryView,
        to_public_view,
    )
    from app.services.language_grammar.enums import GrammarMasteryState  # noqa: WPS433

    topic = GrammarTopic(
        grammar_id="gram_passive_voice",
        display_name="Passive voice",
        cefr_band=GrammarCEFRBand.B2,
        introduction_order=330,
        best_reinforcement_skills=(
            GrammarReinforcementSkill.reading,
            GrammarReinforcementSkill.writing,
        ),
        recommended_contexts=("news headline", "school notice"),
        minimum_context_diversity=2,
        learning_objectives=("Form passives",),
        demonstration_patterns=("was told", "is expected"),
        example_sentences=("The students were given clear instructions.",),
        common_errors=("The students was given...",),
    )
    results.append(_ok("catalog has best_reinforcement_skills", hasattr(topic, "best_reinforcement_skills")))
    results.append(_ok("catalog has recommended_contexts", hasattr(topic, "recommended_contexts")))
    results.append(_ok("catalog has minimum_context_diversity", hasattr(topic, "minimum_context_diversity")))
    results.append(
        _ok(
            "passive topic does not force all four skills",
            len(topic.best_reinforcement_skills) == 2
            and GrammarReinforcementSkill.speaking not in topic.best_reinforcement_skills,
        )
    )

    steps = (
        GrammarLessonStep(kind=GrammarLessonStepKind.explanation, step_id="s1"),
        GrammarLessonStep(kind=GrammarLessonStepKind.practice, step_id="s2", evidence_eligible=True),
        GrammarLessonStep(
            kind=GrammarLessonStepKind.reinforcement,
            step_id="s3",
            skill=GrammarReinforcementSkill.reading,
            evidence_eligible=True,
        ),
        GrammarLessonStep(
            kind=GrammarLessonStepKind.reinforcement,
            step_id="s4",
            skill=GrammarReinforcementSkill.writing,
            evidence_eligible=True,
        ),
    )
    blueprint = GrammarLessonBlueprint(
        grammar_id="gram_passive_voice",
        target_cefr=GrammarCEFRBand.B2,
        objectives=("Notice passive outcomes",),
        steps=steps,
    )
    results.append(_ok("blueprint owns ordered steps", len(blueprint.steps) == 4))
    results.append(
        _ok(
            "blueprint has no hardcoded four-skill chain",
            [s.skill for s in blueprint.steps if s.kind == GrammarLessonStepKind.reinforcement]
            == [GrammarReinforcementSkill.reading, GrammarReinforcementSkill.writing],
        )
    )

    cursor_fields = GrammarRuntimeCursor.__dataclass_fields__
    results.append(_ok("runtime cursor has step_index", "step_index" in cursor_fields))
    results.append(_ok("runtime cursor has no step-builder fields", "best_reinforcement_skills" not in cursor_fields))

    dims = GrammarMasteryDimensions(
        understanding=70.0,
        accuracy=65.0,
        fluency=40.0,
        retention=55.0,
        overall_mastery=58.0,
    )
    record = GrammarMasteryRecord(
        student_id=1,
        language_id=1,
        grammar_id="gram_passive_voice",
        state=GrammarMasteryState.learning,
        dimensions=dims,
    )
    public = to_public_view(record)
    results.append(_ok("public view exposes overall_mastery", public.overall_mastery == 58.0))
    results.append(_ok("public view type has no understanding field", not hasattr(public, "understanding")))
    results.append(
        _ok(
            "public view fields are overall-only surface",
            set(PublicGrammarMasteryView.__dataclass_fields__)
            == {
                "grammar_id",
                "overall_mastery",
                "state",
                "evidence_count",
                "distinct_context_count",
                "last_seen_at",
                "last_mastered_at",
            },
        )
    )
    return results


def check_evidence_first_boundary() -> list[bool]:
    results: list[bool] = []
    evidence_types = (_package_path("language_grammar_evidence") / "types.py").read_text(encoding="utf-8")
    results.append(_ok("evidence defines GrammarEvidenceObservation", "GrammarEvidenceObservation" in evidence_types))
    results.append(
        _ok(
            "evidence does not import mastery write types",
            "GrammarMasteryUpdateRequest" not in evidence_types,
        )
    )

    # Integration must not import evidence write paths into mastery directly
    integ_deps: set[str] = set()
    for py_file in _package_path("language_grammar_integration").glob("*.py"):
        integ_deps |= _parse_imports(py_file)
    results.append(_ok("integration does not depend on evidence", "language_grammar_evidence" not in integ_deps))
    results.append(_ok("integration may read mastery types", "language_grammar_mastery" in integ_deps))

    # Algorithm engines allowed for Progression / Mastery / Review / Planner / Runtime
    engine_allowed = frozenset(
        {
            "language_grammar_progression",
            "language_grammar_mastery",
            "language_grammar_review",
            "language_grammar_lesson_planner",
            "language_grammar_lesson_runtime",
            "language_grammar_evaluation",
        }
    )
    for pkg in sorted(REQUIRED_G0_PACKAGES):
        engine = _package_path(pkg) / "engine.py"
        if pkg in engine_allowed:
            results.append(_ok(f"engine.py allowed for {pkg}", engine.is_file()))
        else:
            results.append(_ok(f"G0 has no engine.py yet: {pkg}", not engine.is_file()))
    return results


def check_legacy_bridge() -> list[bool]:
    results: list[bool] = []
    from app.services.language_grammar.enums import GrammarLegacyIdKind  # noqa: WPS433
    from app.services.language_grammar_legacy_bridge.maps import (  # noqa: WPS433
        BKT_GRAMMAR_TO_GRAMMAR_ID,
        SPEAKING_GRAM_IDS,
        resolve_legacy_grammar_id,
    )
    from app.services.language_grammar_legacy_bridge.types import map_legacy_id  # noqa: WPS433

    results.append(_ok("speaking gram set non-empty", len(SPEAKING_GRAM_IDS) >= 10))
    results.append(_ok("BKT map non-empty", len(BKT_GRAMMAR_TO_GRAMMAR_ID) >= 4))
    results.append(
        _ok(
            "speaking identity map",
            resolve_legacy_grammar_id("gram_present_simple", kind=GrammarLegacyIdKind.speaking_gram)
            == "gram_present_simple",
        )
    )
    results.append(
        _ok(
            "BKT map present_simple",
            resolve_legacy_grammar_id("grammar.present_simple", kind=GrammarLegacyIdKind.bkt_grammar)
            == "gram_present_simple",
        )
    )
    results.append(
        _ok(
            "writing structure map",
            resolve_legacy_grammar_id("present_simple", kind=GrammarLegacyIdKind.writing_structure)
            == "gram_present_simple",
        )
    )
    mapped = map_legacy_id(GrammarLegacyIdKind.bkt_grammar, "grammar.conditionals")
    results.append(_ok("legacy mapping type works", mapped.grammar_id == "gram_first_conditional"))
    return results


def check_feature_flags() -> list[bool]:
    results: list[bool] = []
    from app.core.config import Settings  # noqa: WPS433

    fields = Settings.model_fields
    results.append(_ok("LANG_GRAMMAR_ENGINE_ENABLED exists", "LANG_GRAMMAR_ENGINE_ENABLED" in fields))
    results.append(_ok("LANG_GRAMMAR_ENGINE_SELECT exists", "LANG_GRAMMAR_ENGINE_SELECT" in fields))
    enabled_default = fields["LANG_GRAMMAR_ENGINE_ENABLED"].default
    select_default = fields["LANG_GRAMMAR_ENGINE_SELECT"].default
    results.append(_ok("LANG_GRAMMAR_ENGINE_ENABLED default false", enabled_default is False))
    results.append(_ok("LANG_GRAMMAR_ENGINE_SELECT default false", select_default is False))

    for env_path in (BACKEND / ".env.example", BACKEND.parent / ".env.example"):
        if env_path.is_file():
            text = env_path.read_text(encoding="utf-8")
            results.append(_ok(f"{env_path.name} documents ENABLED", "LANG_GRAMMAR_ENGINE_ENABLED" in text))
            results.append(_ok(f"{env_path.name} documents SELECT", "LANG_GRAMMAR_ENGINE_SELECT" in text))
    return results


def check_not_fifth_skill() -> list[bool]:
    results: list[bool] = []
    from app.models.language.enums import LanguageSkill  # noqa: WPS433

    skill_values = {s.value for s in LanguageSkill}
    results.append(_ok("LanguageSkill has no grammar", "grammar" not in skill_values))
    results.append(
        _ok(
            "LanguageSkill remains four skills",
            skill_values == {"reading", "listening", "writing", "speaking"},
        )
    )
    return results


def check_architecture_violations() -> list[bool]:
    results: list[bool] = []
    forbidden_prefixes = ("app.api", "src.")
    for pkg in REQUIRED_G0_PACKAGES:
        for py_file in _package_path(pkg).glob("*.py"):
            text = py_file.read_text(encoding="utf-8")
            for prefix in forbidden_prefixes:
                if f"from {prefix}" in text or f"import {prefix}" in text:
                    results.append(_ok(f"no API/frontend import in {pkg}/{py_file.name}", False))
    # Shared core must not implement engines
    core = SERVICES / "language_grammar"
    results.append(_ok("core has no engine.py", not (core / "engine.py").is_file()))
    results.append(_ok("LanguageTool service remains separate", (SERVICES / "language_grammar_service.py").is_file()))
    return results


def main() -> int:
    print("Grammar G0 architecture verification\n")
    suites = [
        ("Packages", check_packages_exist),
        ("Ownership", check_ownership_registry),
        ("Import graph", check_import_graph),
        ("Enums & contracts", check_enums_and_contracts),
        ("Blueprint & catalog", check_blueprint_and_catalog_contracts),
        ("Evidence-first boundary", check_evidence_first_boundary),
        ("Legacy bridge", check_legacy_bridge),
        ("Feature flags", check_feature_flags),
        ("Not a fifth skill", check_not_fifth_skill),
        ("Architecture violations", check_architecture_violations),
    ]
    all_results: list[bool] = []
    for title, fn in suites:
        print(f"[{title}]")
        all_results.extend(fn())
        print()

    passed = sum(1 for r in all_results if r)
    failed = sum(1 for r in all_results if not r)
    print(f"Summary: {passed} passed, {failed} failed, {len(all_results)} total")
    if failed:
        print("G0 VERDICT: NOT READY")
        return 1
    print("G0 VERDICT: PRODUCTION-READY (contracts/ownership)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
