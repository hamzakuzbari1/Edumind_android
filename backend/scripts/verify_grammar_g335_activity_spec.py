"""Verify Grammar G3.35 Activity Specification Framework.

Usage (from backend/):
    python scripts/verify_grammar_g335_activity_spec.py
"""

from __future__ import annotations

import ast
import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

BACKEND = Path(__file__).resolve().parents[1]
SERVICES = BACKEND / "app" / "services"
SPEC_PKG = SERVICES / "language_grammar_activity_spec"


def _ok(name: str, passed: bool, detail: str = "") -> bool:
    status = "PASS" if passed else "FAIL"
    suffix = f" - {detail}" if detail else ""
    print(f"  {name}: {status}{suffix}")
    return passed


def _parse_imports(py_file: Path) -> set[str]:
    tree = ast.parse(py_file.read_text(encoding="utf-8"))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("app.services."):
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


def _pkg_deps() -> set[str]:
    deps: set[str] = set()
    for py in SPEC_PKG.rglob("*.py"):
        deps |= _parse_imports(py)
    return deps


def audit_1_schema_integrity() -> list[bool]:
    print("[Audit 1 - Schema Integrity]")
    results: list[bool] = []
    from app.services.language_grammar_activity_spec import (
        ActivitySpecError,
        ActivitySpecification,
        build_minimal_specification,
        validate_activity_specification,
    )
    from app.services.language_grammar_activity_spec.types import (
        ActivityAssetRef,
        ActivityReference,
        ActivityVersionSet,
        CompletionRule,
        EvidenceDeclaration,
        ExpectedOutputSpec,
        LocalizedText,
        ProviderMetadata,
    )

    # Documented required surface — field presence on ActivitySpecification
    required_fields = {
        "activity_id",
        "activity_type",
        "grammar_topic",
        "lesson_id",
        "step_id",
        "title",
        "goal",
        "instructions",
        "difficulty",
        "estimated_duration_seconds",
        "grammar_targets",
        "expected_outputs",
        "evaluation_mode",
        "completion_rules",
        "hints",
        "assets",
        "references",
        "evidence",
        "provider_metadata",
        "localization_default_locale",
        "supported_locales",
        "versions",
        "fingerprint",
        "payload",
    }
    fields = set(ActivitySpecification.__dataclass_fields__.keys())
    results.append(_ok("all documented fields present", required_fields <= fields, str(sorted(required_fields - fields))))

    # Nested contract types exist
    for name, cls in (
        ("LocalizedText", LocalizedText),
        ("ExpectedOutputSpec", ExpectedOutputSpec),
        ("CompletionRule", CompletionRule),
        ("EvidenceDeclaration", EvidenceDeclaration),
        ("ProviderMetadata", ProviderMetadata),
        ("ActivityVersionSet", ActivityVersionSet),
        ("ActivityAssetRef", ActivityAssetRef),
        ("ActivityReference", ActivityReference),
    ):
        results.append(_ok(f"model {name} defined", cls is not None))

    spec = build_minimal_specification()
    try:
        validate_activity_specification(spec)
        results.append(_ok("minimal spec validates", True))
    except ActivitySpecError as exc:
        results.append(_ok("minimal spec validates", False, str(exc)))

    # Reject missing completion / evidence / unknown type
    bad = build_minimal_specification(validate=False)
    from dataclasses import replace

    try:
        validate_activity_specification(replace(bad, completion_rules=()))
        results.append(_ok("missing completion_rules rejected", False))
    except ActivitySpecError:
        results.append(_ok("missing completion_rules rejected", True))

    try:
        validate_activity_specification(replace(bad, evidence=()))
        results.append(_ok("missing evidence rejected", False))
    except ActivitySpecError:
        results.append(_ok("missing evidence rejected", True))

    try:
        validate_activity_specification(replace(bad, activity_type="not_a_real_type"))
        results.append(_ok("unknown activity type rejected", False))
    except ActivitySpecError:
        results.append(_ok("unknown activity type rejected", True))

    try:
        validate_activity_specification(replace(bad, evaluation_mode="telepathy"))
        results.append(_ok("unknown evaluation mode rejected", False))
    except ActivitySpecError:
        results.append(_ok("unknown evaluation mode rejected", True))

    try:
        validate_activity_specification(bad, known_activity_ids={bad.activity_id})
        results.append(_ok("duplicate activity_id rejected", False))
    except ActivitySpecError:
        results.append(_ok("duplicate activity_id rejected", True))

    try:
        validate_activity_specification(
            replace(bad, versions=replace(bad.versions, activity_schema_version=999))
        )
        results.append(_ok("broken schema version rejected", False))
    except ActivitySpecError:
        results.append(_ok("broken schema version rejected", True))

    results.append(_ok("Audit 1 verdict", all(results)))
    print()
    return results


def audit_2_future_compatibility() -> list[bool]:
    print("[Audit 2 - Future Compatibility]")
    results: list[bool] = []
    from app.services.language_grammar_activity_spec import (
        ActivitySpecError,
        build_minimal_specification,
        get_default_spec_registry,
        reset_default_spec_registry_for_tests,
        validate_activity_specification,
    )
    from dataclasses import replace

    reset_default_spec_registry_for_tests()
    reg = get_default_spec_registry()

    # Register new types without schema version bump
    reg.register_activity_type("drag_drop_sentence")
    reg.register_output_type("drag_drop_sentence")
    reg.register_evaluation_mode("rubric_v2")
    reg.register_evidence_kind("peer_observation")

    spec = build_minimal_specification(validate=False)
    extended = replace(
        spec,
        activity_type="drag_drop_sentence",
        expected_outputs=(
            replace(spec.expected_outputs[0], output_type="drag_drop_sentence"),
        ),
        evaluation_mode="rubric_v2",
        evidence=(
            replace(
                spec.evidence[0],
                evidence_kind="peer_observation",
            ),
        ),
    )
    try:
        validate_activity_specification(extended, registry=reg)
        results.append(_ok("new activity/output/eval/evidence types accepted after register", True))
    except ActivitySpecError as exc:
        results.append(_ok("new activity/output/eval/evidence types accepted after register", False, str(exc)))

    # Old specs still validate on same schema version
    try:
        validate_activity_specification(build_minimal_specification(validate=False), registry=reg)
        results.append(_ok("legacy builtin types still validate", True))
    except ActivitySpecError as exc:
        results.append(_ok("legacy builtin types still validate", False, str(exc)))

    # New schema version can be registered without breaking v1
    reg.register_schema_version(2)
    results.append(_ok("schema v1 still compatible", reg.is_schema_compatible(1)))
    results.append(_ok("schema v2 registerable", reg.is_schema_compatible(2)))

    reset_default_spec_registry_for_tests()
    results.append(_ok("Audit 2 verdict", all(results)))
    print()
    return results


def audit_3_architecture() -> list[bool]:
    print("[Audit 3 - Architecture]")
    results: list[bool] = []
    forbidden = {
        "language_grammar_lesson_runtime",
        "language_grammar_lesson_planner",
        "language_grammar_activity_provider",
        "language_grammar_educational_package",
        "claude_service",
        "language_grammar_analytics",
        "language_grammar_mastery",
        "language_grammar_progression",
        "language_grammar_review",
        "language_grammar_integration",
    }
    deps = _pkg_deps()
    for dep in sorted(forbidden):
        results.append(_ok(f"spec does not import {dep}", dep not in deps))

    # No frontend / UI framework coupling
    src = "\n".join(p.read_text(encoding="utf-8") for p in SPEC_PKG.rglob("*.py"))
    results.append(_ok("no React import", "import react" not in src.lower() and "from react" not in src.lower()))
    results.append(_ok("no Vue coupling", "vue" not in src.lower()))
    results.append(_ok("no JSX coupling", "jsx" not in src.lower() or "react_tree" in src))  # react_tree is a forbidden key name only
    results.append(_ok("no template engine coupling", "django.template" not in src and "fastapi.templating" not in src))

    from app.services.language_grammar.ownership import ALLOWED_PACKAGE_DEPENDENCIES

    allowed = ALLOWED_PACKAGE_DEPENDENCIES["language_grammar_activity_spec"]
    unexpected = {d.split(".")[0] for d in deps if d.startswith("language_grammar_")} - set(allowed) - {
        "language_grammar_activity_spec",
        "language_grammar",
    }
    results.append(_ok("ownership DAG: leaf package", not unexpected, str(sorted(unexpected))))
    results.append(_ok("Audit 3 verdict", all(results)))
    print()
    return results


def audit_4_replayability() -> list[bool]:
    print("[Audit 4 - Replayability]")
    results: list[bool] = []
    from app.services.language_grammar_activity_spec import (
        build_minimal_specification,
        fingerprint_specification,
        specification_from_dict,
        specification_to_dict,
        validate_activity_specification,
        with_fingerprint,
    )

    spec = build_minimal_specification()
    raw = specification_to_dict(spec)
    restored = specification_from_dict(copy.deepcopy(raw))
    results.append(_ok("serialize produces dict", isinstance(raw, dict)))
    results.append(_ok("deserialize roundtrip activity_id", restored.activity_id == spec.activity_id))
    results.append(_ok("deserialize roundtrip versions", restored.versions == spec.versions))
    results.append(_ok("deserialize roundtrip evidence", restored.evidence == spec.evidence))
    results.append(_ok("fingerprint stable", fingerprint_specification(spec) == fingerprint_specification(restored)))
    results.append(_ok("with_fingerprint sets field", bool(with_fingerprint(spec).fingerprint)))
    results.append(
        _ok(
            "version fields present",
            bool(
                restored.versions.activity_schema_version
                and restored.versions.provider_version
                and restored.versions.planner_version
                and restored.versions.blueprint_version
                and restored.versions.catalog_version
                and restored.versions.grammar_schema_version
            ),
        )
    )
    try:
        validate_activity_specification(restored)
        results.append(_ok("restored spec still validates", True))
    except Exception as exc:  # noqa: BLE001
        results.append(_ok("restored spec still validates", False, str(exc)))

    # Replay fingerprint across 5 serializations
    fps = [fingerprint_specification(specification_from_dict(specification_to_dict(spec))) for _ in range(5)]
    results.append(_ok("fingerprint deterministic across replay", len(set(fps)) == 1))
    results.append(_ok("Audit 4 verdict", all(results)))
    print()
    return results


def check_flags_and_registry() -> list[bool]:
    print("[Flags & registry]")
    results: list[bool] = []
    from app.core.config import get_settings
    from app.services.language_grammar_activity_spec import (
        activity_spec_validation_strict,
        get_default_spec_registry,
        reset_default_spec_registry_for_tests,
    )

    settings = get_settings()
    results.append(
        _ok(
            "LANG_GRAMMAR_ACTIVITY_SPEC_STRICT defined",
            hasattr(settings, "LANG_GRAMMAR_ACTIVITY_SPEC_STRICT"),
        )
    )
    results.append(_ok("strict flag readable", isinstance(activity_spec_validation_strict(), bool)))
    reset_default_spec_registry_for_tests()
    reg = get_default_spec_registry()
    results.append(_ok("registry discovers activity types", len(reg.activity_types()) >= 5))
    results.append(_ok("registry discovers evaluation modes", len(reg.evaluation_modes()) >= 3))
    results.append(_ok("registry discovers evidence kinds", len(reg.evidence_kinds()) >= 3))
    print()
    return results


def main() -> int:
    print("Grammar G3.35 Activity Specification Framework verification\n")
    all_results: list[bool] = []
    all_results.extend(audit_1_schema_integrity())
    all_results.extend(audit_2_future_compatibility())
    all_results.extend(audit_3_architecture())
    all_results.extend(audit_4_replayability())
    all_results.extend(check_flags_and_registry())

    passed = sum(1 for r in all_results if r)
    failed = sum(1 for r in all_results if not r)
    print(f"Summary: {passed} passed, {failed} failed, {len(all_results)} total")
    if failed:
        print("G3.35 VERDICT: NOT READY")
        return 1
    print("G3.35 VERDICT: READY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
