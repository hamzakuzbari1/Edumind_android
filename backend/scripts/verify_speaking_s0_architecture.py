"""Verify Speaking S0 architecture foundation.

Usage (from backend/):
    python scripts/verify_speaking_s0_architecture.py
"""

from __future__ import annotations

import ast
import importlib
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

BACKEND = Path(__file__).resolve().parents[1]
APP = BACKEND / "app"
SERVICES = APP / "services"

from app.services.language_speaking.ownership import (  # noqa: E402
    ALLOWED_PACKAGE_DEPENDENCIES,
    ARCHITECTURE_LAYERS,
    FORBIDDEN_LEGACY_IMPORTS_IN,
    FORBIDDEN_PROVIDER_SDK_IMPORTS,
    LEGACY_FLAT_MODULES,
    LEGACY_IMPORT_GATEWAY,
    PACKAGE_LAYER,
    PACKAGE_OWNERSHIP,
    REQUIRED_S0_PACKAGES,
    SHARED_INFRASTRUCTURE,
)
from app.services.language_speaking_official_promotion.ownership_guard import (  # noqa: E402
    verify_speaking_cefr_ownership,
)
from app.services.language_speaking_legacy_adapter.adapter import (  # noqa: E402
    KNOWN_RUNTIME_BLOCKERS,
    LEGACY_MODULE_MAP,
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
                    if pkg == "language_speaking":
                        continue
                    if pkg.startswith("language_speaking_"):
                        imports.add(pkg)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("app.services."):
                    parts = alias.name.split(".")
                    if len(parts) >= 3:
                        pkg = parts[2]
                        if pkg == "language_speaking":
                            continue
                        if pkg.startswith("language_speaking_"):
                            imports.add(pkg)
    return imports


def _legacy_import_pattern(module: str) -> re.Pattern[str]:
    return re.compile(rf"\b(from\s+app\.services\.{re.escape(module)}|import\s+app\.services\.{re.escape(module)})\b")


def check_packages_exist() -> list[bool]:
    results: list[bool] = []
    for pkg in sorted(REQUIRED_S0_PACKAGES):
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
            len(PACKAGE_OWNERSHIP) == len(REQUIRED_S0_PACKAGES),
        )
    )
    results.append(
        _ok(
            "no duplicate ownership descriptions",
            len(set(PACKAGE_OWNERSHIP.values())) == len(PACKAGE_OWNERSHIP),
        )
    )
    for pkg in REQUIRED_S0_PACKAGES:
        results.append(_ok(f"ownership entry: {pkg}", pkg in PACKAGE_OWNERSHIP))
    return results


def check_import_graph() -> list[bool]:
    results: list[bool] = []
    speaking_deps: dict[str, set[str]] = {}

    for pkg in REQUIRED_S0_PACKAGES:
        pkg_dir = _package_path(pkg)
        deps: set[str] = set()
        for py_file in pkg_dir.glob("*.py"):
            for imp in _parse_imports(py_file):
                if imp.startswith("language_speaking"):
                    deps.add(imp)
        speaking_deps[pkg] = deps

    for pkg in sorted(REQUIRED_S0_PACKAGES):
        module_name = f"app.services.{pkg}.types"
        try:
            importlib.import_module(module_name)
            results.append(_ok(f"import types: {pkg}", True))
        except Exception as exc:  # noqa: BLE001
            results.append(_ok(f"import types: {pkg}", False, str(exc)))

    for pkg, deps in speaking_deps.items():
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
    for pkg, deps in speaking_deps.items():
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


def check_legacy_boundary() -> list[bool]:
    results: list[bool] = []
    results.append(_ok("legacy gateway is legacy_adapter only", LEGACY_IMPORT_GATEWAY == frozenset({"language_speaking_legacy_adapter"})))
    results.append(_ok("legacy module map documented", len(LEGACY_MODULE_MAP) >= 8))

    legacy_patterns = [_legacy_import_pattern(mod) for mod in LEGACY_FLAT_MODULES]
    for pkg in sorted(FORBIDDEN_LEGACY_IMPORTS_IN):
        for py_file in _package_path(pkg).glob("*.py"):
            text = py_file.read_text(encoding="utf-8")
            for mod, pattern in zip(LEGACY_FLAT_MODULES, legacy_patterns, strict=True):
                if pattern.search(text):
                    results.append(
                        _ok(
                            f"no legacy import in {pkg}/{py_file.name}: {mod}",
                            False,
                        )
                    )

    adapter_dir = _package_path("language_speaking_legacy_adapter")
    results.append(_ok("legacy adapter package exists", adapter_dir.is_dir()))
    return results


def check_provider_isolation() -> list[bool]:
    results: list[bool] = []
    allowed_sdk_packages = frozenset(
        {
            "language_speaking_providers",
            "language_speaking_audio_frontend",
            "language_speaking_legacy_adapter",
        }
    )
    provider_abcs = (
        "SpeechTranscriptionProvider",
        "SpeechEmbeddingProvider",
        "PhonemeAlignmentProvider",
        "AcousticFeatureProvider",
        "SpeakingSpeechOutputProvider",
        "SpeakingEducationalAnalyzerProvider",
    )
    from app.services.language_speaking_providers import providers as prov_mod  # noqa: WPS433

    for abc in provider_abcs:
        results.append(_ok(f"provider ABC: {abc}", hasattr(prov_mod, abc)))

    for pkg in REQUIRED_S0_PACKAGES:
        if pkg in allowed_sdk_packages:
            continue
        for py_file in _package_path(pkg).glob("*.py"):
            text = py_file.read_text(encoding="utf-8").lower()
            for sdk in FORBIDDEN_PROVIDER_SDK_IMPORTS:
                if sdk in text:
                    results.append(_ok(f"no SDK '{sdk}' in {pkg}/{py_file.name}", False))
    return results


def check_official_cefr_guard() -> list[bool]:
    results: list[bool] = []
    ok, unauthorized, _missing = verify_speaking_cefr_ownership(APP)
    results.append(_ok("official_speaking_cefr ownership (no unauthorized writers)", ok))
    if unauthorized:
        for mod in sorted(unauthorized):
            results.append(_ok(f"  unauthorized writer: {mod}", False))
    return results


def check_enums_and_contracts() -> list[bool]:
    results: list[bool] = []
    from app.services.language_speaking import enums as speaking_enums  # noqa: WPS433

    required_enums = [
        "OfficialSpeakingCEFR",
        "SpeakingGoal",
        "SpeakingCoachPersonality",
        "SpeakingTaskType",
        "SpeakingSkillType",
        "SpeakingAudioSource",
        "SpeakingSessionProcessingState",
        "SpeakingConversationState",
        "InterruptionDecision",
        "PromotionStatus",
    ]
    for name in required_enums:
        results.append(_ok(f"enum: {name}", hasattr(speaking_enums, name)))

    contract_modules = [
        ("SpeakingAudioSession", "app.services.language_speaking.types"),
        ("SpeakingSpeechEvidence", "app.services.language_speaking.types"),
        ("SpeakingEvaluationEngineResult", "app.services.language_speaking_evaluator.evaluation_result"),
        ("DimensionFacts", "app.services.language_speaking_evaluator.evaluation_result"),
        ("CriterionStatus", "app.services.language_speaking_evaluator.evaluation_facts_types"),
        ("SpeakingCoachGuidance", "app.services.language_speaking_coach.types"),
        ("SpeakingLessonExperienceBundle", "app.services.language_speaking_lesson_experience.types"),
        ("SpeakingJourneyBundle", "app.services.language_speaking_journey.types"),
        ("SpeakingPromotionTestBundle", "app.services.language_speaking_promotion_test.types"),
        ("LegacyTurnPayload", "app.services.language_speaking_legacy_adapter.types"),
    ]
    for class_name, module_path in contract_modules:
        mod = importlib.import_module(module_path)
        results.append(_ok(f"contract: {class_name}", hasattr(mod, class_name)))

    return results


def check_runtime_blockers_documented() -> list[bool]:
    results: list[bool] = []
    blocker_ids = {b["id"] for b in KNOWN_RUNTIME_BLOCKERS}
    for required in ("mastery_settings_attr", "tts_signature_mismatch", "dual_level_system"):
        results.append(_ok(f"runtime blocker documented: {required}", required in blocker_ids))

    arch_doc = SERVICES / "SPEAKING_ARCHITECTURE.md"
    if arch_doc.is_file():
        text = arch_doc.read_text(encoding="utf-8")
        results.append(_ok("SPEAKING_ARCHITECTURE.md exists", True))
        results.append(_ok("architecture doc: runtime blockers section", "Runtime blockers" in text))
        results.append(_ok("architecture doc: legacy freeze policy", "Legacy freeze" in text))
        results.append(_ok("architecture doc: retention boundaries", "Retention" in text))
    else:
        results.append(_ok("SPEAKING_ARCHITECTURE.md exists", False))
    return results


def check_legacy_preservation() -> list[bool]:
    results: list[bool] = []
    for mod in sorted(LEGACY_FLAT_MODULES):
        legacy = SERVICES / f"{mod}.py"
        results.append(_ok(f"legacy module preserved: {mod}", legacy.is_file()))
    return results


def check_architecture_violations() -> list[bool]:
    results: list[bool] = []
    forbidden_prefixes = ("app.api", "src.")
    for pkg in REQUIRED_S0_PACKAGES:
        for py_file in _package_path(pkg).glob("*.py"):
            text = py_file.read_text(encoding="utf-8")
            for prefix in forbidden_prefixes:
                results.append(_ok(f"no {prefix} in {pkg}/{py_file.name}", prefix not in text))
    results.append(_ok("shared infrastructure documented", len(SHARED_INFRASTRUCTURE) >= 4))
    results.append(_ok("ElevenLabs excluded from speaking providers", "elevenlabs" in FORBIDDEN_PROVIDER_SDK_IMPORTS))
    return results


def main() -> int:
    print("Speaking S0 Architecture Verification\n")
    sections = [
        ("Package layout", check_packages_exist),
        ("Ownership registry", check_ownership_registry),
        ("Import graph & layers", check_import_graph),
        ("Legacy adapter boundary", check_legacy_boundary),
        ("Provider isolation", check_provider_isolation),
        ("Official CEFR guard", check_official_cefr_guard),
        ("Enums & contracts", check_enums_and_contracts),
        ("Runtime blockers (documented)", check_runtime_blockers_documented),
        ("Legacy preservation", check_legacy_preservation),
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
        print("S0 READY — S1 may begin after review.")
        return 0
    print("S0 NOT READY — fix failures before S1.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
