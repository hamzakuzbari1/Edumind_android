"""Verify Grammar G3.4 — Skill Execution Framework.

Usage (from backend/):
    python scripts/verify_grammar_g34_skill_framework.py
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

BACKEND = Path(__file__).resolve().parents[1]
SERVICES = BACKEND / "app" / "services"
PKG = SERVICES / "language_grammar_skill_executor"

FORBIDDEN_IMPORTS = frozenset(
    {
        "language_grammar_lesson_planner",
        "language_grammar_lesson_runtime",
        "language_grammar_activity_provider",
        "language_grammar_mastery",
        "language_grammar_progression",
        "language_grammar_review",
        "language_grammar_analytics",
        "language_grammar_integration",
        "claude_service",
    }
)


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


def _context(*, activity_type: str = "multiple_choice", execution_id: str = "exec_g34_1"):
    from app.services.language_grammar_activity_spec import build_minimal_specification
    from app.services.language_grammar_skill_executor import (
        ExecutionContext,
        ExecutionFeatureFlags,
        ExecutionMetadata,
        StudentContext,
    )

    spec = build_minimal_specification(
        activity_id=f"act_{activity_type}",
        activity_type=activity_type,
        step_id="practice",
    )
    return ExecutionContext(
        specification=spec,
        student=StudentContext(student_id=1, language_id=1, overall_cefr="A1", locale="en"),
        runtime_session_id="sess_g34",
        blueprint_id="bp_g34",
        execution_id=execution_id,
        localization="en",
        feature_flags=ExecutionFeatureFlags(
            grammar_engine_enabled=True,
            skill_executor_enabled=True,
            skill_executor_strict=True,
        ),
        metadata=ExecutionMetadata(as_of="2026-01-01T00:00:00Z", attempt_index=0),
    )


def audit_1_registry_integrity() -> list[bool]:
    print("[Audit 1 - Registry Integrity]")
    results: list[bool] = []
    from app.services.language_grammar_skill_executor import (
        REQUIRED_PLACEHOLDER_EXECUTOR_IDS,
        SkillExecutorRegistry,
        builtin_placeholder_executors,
        get_default_skill_executor_registry,
        reset_default_skill_executor_registry_for_tests,
    )

    reset_default_skill_executor_registry_for_tests()
    reg = get_default_skill_executor_registry()
    ids = set(reg.ids())
    results.append(
        _ok(
            "all required placeholders registered",
            REQUIRED_PLACEHOLDER_EXECUTOR_IDS.issubset(ids),
            str(sorted(REQUIRED_PLACEHOLDER_EXECUTOR_IDS - ids)),
        )
    )
    builtins = builtin_placeholder_executors()
    results.append(_ok("builtin count matches unique ids", len(builtins) == len({e.executor_id for e in builtins})))
    try:
        SkillExecutorRegistry(executors=(builtins[0], builtins[0]))
        results.append(_ok("duplicate executor ids rejected", False))
    except ValueError:
        results.append(_ok("duplicate executor ids rejected", True))
    results.append(_ok("Audit 1 verdict", all(results)))
    print()
    return results


def audit_2_lifecycle_integrity() -> list[bool]:
    print("[Audit 2 - Lifecycle Integrity]")
    results: list[bool] = []
    from app.services.language_grammar_skill_executor import (
        LIFECYCLE_PHASES,
        get_default_skill_executor_registry,
        lifecycle_methods_present,
        reset_default_execution_id_guard_for_tests,
        run_lifecycle,
    )

    reset_default_execution_id_guard_for_tests()
    reg = get_default_skill_executor_registry()
    for executor in reg.all_executors():
        present = set(lifecycle_methods_present(executor))
        expected = {p.value for p in LIFECYCLE_PHASES}
        results.append(
            _ok(
                f"{executor.executor_id} full lifecycle",
                expected.issubset(present),
                str(sorted(expected - present)),
            )
        )

    ctx = _context(execution_id="exec_lifecycle_mc")
    executor = reg.get("multiple_choice")
    result = run_lifecycle(executor, ctx, emit_evidence=True)
    phases = set(result.executor_metadata.lifecycle_phases_completed)
    # cancel is not in happy path; cleanup runs in finally
    results.append(_ok("happy-path includes initialize", "initialize" in phases))
    results.append(_ok("happy-path includes prepare", "prepare" in phases))
    results.append(_ok("happy-path includes validate", "validate" in phases))
    results.append(_ok("happy-path includes execute", "execute" in phases))
    results.append(_ok("happy-path includes complete", "complete" in phases))
    results.append(_ok("happy-path includes cleanup", "cleanup" in phases))
    results.append(_ok("Audit 2 verdict", all(results)))
    print()
    return results


def audit_3_evidence_isolation() -> list[bool]:
    print("[Audit 3 - Evidence Isolation]")
    results: list[bool] = []
    pkg_imports: set[str] = set()
    for py in PKG.rglob("*.py"):
        pkg_imports |= _parse_imports(py)

    for forbidden in (
        "language_grammar_mastery",
        "language_grammar_progression",
        "language_grammar_review",
    ):
        results.append(_ok(f"executors never import {forbidden}", forbidden not in pkg_imports))

    # Source scan — no mastery write APIs
    src = "\n".join(p.read_text(encoding="utf-8") for p in PKG.rglob("*.py"))
    results.append(_ok("no apply_evidence_batch calls", "apply_evidence_batch" not in src))
    results.append(_ok("no mastery update symbols", "update_mastery" not in src and "MasteryEngine" not in src))

    from app.services.language_grammar_skill_executor import (
        adapt_execution_to_evidence,
        execute_activity,
        reset_default_execution_id_guard_for_tests,
    )

    reset_default_execution_id_guard_for_tests()
    ctx = _context(execution_id="exec_evidence_1")
    result = execute_activity(ctx, require_enabled=False, emit_evidence=True)
    results.append(_ok("execution emits evidence observations", len(result.generated_evidence) >= 1))
    adapted = adapt_execution_to_evidence(result, context=ctx)
    results.append(_ok("adapter returns GrammarEvidenceObservation tuple", len(adapted) >= 1))
    results.append(_ok("Audit 3 verdict", all(results)))
    print()
    return results


def audit_4_architecture() -> list[bool]:
    print("[Audit 4 - Architecture]")
    results: list[bool] = []
    pkg_imports: set[str] = set()
    for py in PKG.rglob("*.py"):
        pkg_imports |= _parse_imports(py)

    for forbidden in sorted(FORBIDDEN_IMPORTS):
        results.append(_ok(f"no import of {forbidden}", forbidden not in pkg_imports))

    results.append(_ok("depends on activity_spec", "language_grammar_activity_spec" in pkg_imports))
    results.append(_ok("depends on evidence", "language_grammar_evidence" in pkg_imports))

    from app.services.language_grammar.ownership import ALLOWED_PACKAGE_DEPENDENCIES

    allowed = ALLOWED_PACKAGE_DEPENDENCIES.get("language_grammar_skill_executor", frozenset())
    grammar_deps = {d for d in pkg_imports if d.startswith("language_grammar")}
    # language_grammar (shared) is infrastructure; strip self-imports too
    grammar_deps.discard("language_grammar")
    grammar_deps.discard("language_grammar_skill_executor")
    extra = grammar_deps - set(allowed)
    results.append(_ok("ownership DAG respected", not extra, str(sorted(extra))))

    # Runtime must not hardcode activity-type branches for skills
    runtime_pkg = SERVICES / "language_grammar_lesson_runtime"
    runtime_src = "\n".join(p.read_text(encoding="utf-8") for p in runtime_pkg.rglob("*.py"))
    bad_branches = [
        'if activity == "speaking"',
        "if activity == 'speaking'",
        'if activity == "writing"',
        "if activity_type == ActivityType.speaking",
    ]
    results.append(_ok("runtime has no skill activity if-branches", not any(b in runtime_src for b in bad_branches)))
    results.append(_ok("Audit 4 verdict", all(results)))
    print()
    return results


def audit_5_plugin_extensibility() -> list[bool]:
    print("[Audit 5 - Plugin Extensibility]")
    results: list[bool] = []
    from dataclasses import replace

    from app.services.language_grammar_activity_spec import (
        ExpectedOutputSpec,
        ExpectedOutputType,
        build_minimal_specification,
        get_default_spec_registry,
        validate_activity_specification,
        with_fingerprint,
    )
    from app.services.language_grammar_skill_executor import (
        ExecutionContext,
        ExecutionFeatureFlags,
        ExecutionMetadata,
        ExecutionStatus,
        SkillExecutorRegistry,
        StudentContext,
        execute_activity,
        load_builtin_plugins,
        load_plugins_from_factory_paths,
        reset_default_execution_id_guard_for_tests,
    )
    from app.services.language_grammar_skill_executor.base import PlaceholderSkillExecutor

    class _Custom(PlaceholderSkillExecutor):
        def __init__(self) -> None:
            super().__init__("custom_ext", frozenset({"custom_type_g34"}))

    # Register without touching Runtime / Planner / Provider packages
    reg = SkillExecutorRegistry(executors=load_builtin_plugins())
    reg.register(_Custom())
    reg.map_activity_type("custom_type_g34", "custom_ext")
    get_default_spec_registry().register_activity_type("custom_type_g34")

    spec = build_minimal_specification(
        activity_id="act_custom",
        activity_type="multiple_choice",
        validate=False,
    )
    spec = replace(
        spec,
        activity_type="custom_type_g34",
        expected_outputs=(
            ExpectedOutputSpec(
                output_id="out_custom",
                output_type=ExpectedOutputType.free_text.value,
                required=True,
            ),
        ),
    )
    spec = with_fingerprint(spec)

    try:
        validate_activity_specification(spec)
        valid = True
        results.append(_ok("custom spec validates after register", True))
    except Exception as exc:  # noqa: BLE001
        valid = False
        results.append(_ok("custom spec validates after register", False, str(exc)))

    if valid:
        ctx = ExecutionContext(
            specification=spec,
            student=StudentContext(student_id=1, language_id=1),
            runtime_session_id="sess_ext",
            blueprint_id="bp_ext",
            execution_id="exec_custom_1",
            feature_flags=ExecutionFeatureFlags(
                grammar_engine_enabled=True,
                skill_executor_enabled=True,
            ),
            metadata=ExecutionMetadata(as_of="2026-01-01T00:00:00Z"),
        )
        reset_default_execution_id_guard_for_tests()
        out = execute_activity(ctx, registry=reg, require_enabled=False)
        results.append(
            _ok(
                "custom executor runs without Runtime/Planner/Provider changes",
                out.status is ExecutionStatus.completed
                and out.executor_metadata.executor_id == "custom_ext",
            )
        )

    factories = load_plugins_from_factory_paths(
        ("app.services.language_grammar_skill_executor.plugins:builtin_placeholder_executors",)
    )
    results.append(_ok("plugin loader loads builtin factory", len(factories) >= 11))
    results.append(_ok("Audit 5 verdict", all(results)))
    print()
    return results


def audit_6_activity_coverage() -> list[bool]:
    print("[Audit 6 - Activity Coverage]")
    results: list[bool] = []
    from app.services.language_grammar_activity_spec.enums import ActivityType, BUILTIN_ACTIVITY_TYPES
    from app.services.language_grammar_skill_executor import (
        DEFAULT_ACTIVITY_TYPE_TO_EXECUTOR,
        execute_activity,
        get_default_skill_executor_registry,
        reset_default_execution_id_guard_for_tests,
    )

    reg = get_default_skill_executor_registry()
    for activity_type in sorted(BUILTIN_ACTIVITY_TYPES):
        mapped = DEFAULT_ACTIVITY_TYPE_TO_EXECUTOR.get(activity_type)
        results.append(_ok(f"map exists for {activity_type}", mapped is not None, str(mapped)))
        if mapped:
            try:
                executor = reg.get(mapped)
                results.append(
                    _ok(
                        f"executor supports {activity_type}",
                        executor.supports(activity_type),
                        mapped,
                    )
                )
            except KeyError:
                results.append(_ok(f"executor supports {activity_type}", False, f"missing {mapped}"))

    # End-to-end resolve+execute for every builtin type
    from dataclasses import replace

    from app.services.language_grammar_activity_spec import ExpectedOutputSpec, with_fingerprint
    from app.services.language_grammar_skill_executor import (
        ExecutionContext,
        ExecutionFeatureFlags,
        ExecutionMetadata,
        StudentContext,
    )

    reset_default_execution_id_guard_for_tests()
    for index, activity_type in enumerate(sorted(ActivityType)):
        base = _context(activity_type=activity_type.value, execution_id=f"exec_cover_{index}")
        out_type = activity_type.value
        spec = replace(
            base.specification,
            activity_type=activity_type.value,
            expected_outputs=(
                ExpectedOutputSpec(
                    output_id=f"out_{activity_type.value}",
                    output_type=out_type,
                    required=True,
                    options=("a", "b") if activity_type.value in {"multiple_choice", "selection"} else (),
                ),
            ),
        )
        spec = with_fingerprint(spec)
        ctx = ExecutionContext(
            specification=spec,
            student=StudentContext(student_id=1, language_id=1),
            runtime_session_id="sess_cover",
            blueprint_id="bp_cover",
            execution_id=f"exec_cover_{index}",
            feature_flags=ExecutionFeatureFlags(
                grammar_engine_enabled=True,
                skill_executor_enabled=True,
            ),
            metadata=ExecutionMetadata(as_of="2026-01-01T00:00:00Z"),
        )
        try:
            result = execute_activity(ctx, require_enabled=False)
            results.append(
                _ok(
                    f"execute {activity_type.value}",
                    result.status.value == "completed",
                    result.executor_metadata.executor_id,
                )
            )
        except Exception as exc:  # noqa: BLE001
            results.append(_ok(f"execute {activity_type.value}", False, str(exc)))

    results.append(_ok("Audit 6 verdict", all(results)))
    print()
    return results


def check_contracts_and_validation() -> list[bool]:
    print("[Contracts & validation]")
    results: list[bool] = []
    from app.core.config import get_settings
    from app.services.language_grammar_skill_executor import (
        BrokenSpecificationError,
        DuplicateExecutionIdError,
        ExecutionStatus,
        MissingExecutorError,
        SkillExecutorDisabledError,
        SkillExecutorRegistry,
        execute_activity,
        reset_default_execution_id_guard_for_tests,
        resolve_executor,
    )

    settings = get_settings()
    results.append(
        _ok(
            "LANG_GRAMMAR_SKILL_EXECUTOR_ENABLED defined",
            hasattr(settings, "LANG_GRAMMAR_SKILL_EXECUTOR_ENABLED"),
        )
    )
    results.append(
        _ok(
            "LANG_GRAMMAR_SKILL_EXECUTOR_STRICT defined",
            hasattr(settings, "LANG_GRAMMAR_SKILL_EXECUTOR_STRICT"),
        )
    )

    # Unknown activity type
    from dataclasses import replace
    from app.services.language_grammar_activity_spec import build_minimal_specification
    from app.services.language_grammar_skill_executor import (
        ExecutionContext,
        ExecutionFeatureFlags,
        ExecutionMetadata,
        StudentContext,
    )

    bad_spec = replace(build_minimal_specification(validate=False), activity_type="not_a_real_type")
    bad_ctx = ExecutionContext(
        specification=bad_spec,
        student=StudentContext(student_id=1, language_id=1),
        runtime_session_id="s",
        blueprint_id="b",
        execution_id="exec_bad_type",
        feature_flags=ExecutionFeatureFlags(grammar_engine_enabled=True, skill_executor_enabled=True),
        metadata=ExecutionMetadata(),
    )
    try:
        resolve_executor(bad_ctx)
        results.append(_ok("unknown activity type rejected", False))
    except Exception:  # noqa: BLE001
        results.append(_ok("unknown activity type rejected", True))

    # Missing completion rules
    reset_default_execution_id_guard_for_tests()
    bare = replace(build_minimal_specification(validate=False), completion_rules=())
    bare_ctx = ExecutionContext(
        specification=bare,
        student=StudentContext(student_id=1, language_id=1),
        runtime_session_id="s",
        blueprint_id="b",
        execution_id="exec_bare_rules",
        feature_flags=ExecutionFeatureFlags(grammar_engine_enabled=True, skill_executor_enabled=True),
        metadata=ExecutionMetadata(as_of="2026-01-01T00:00:00Z"),
    )
    try:
        execute_activity(bare_ctx, require_enabled=False)
        results.append(_ok("missing completion_rules rejected", False))
    except BrokenSpecificationError:
        results.append(_ok("missing completion_rules rejected", True))
    except Exception as exc:  # noqa: BLE001
        results.append(_ok("missing completion_rules rejected", False, str(exc)))

    # Duplicate execution ids
    reset_default_execution_id_guard_for_tests()
    ctx1 = _context(execution_id="exec_dup")
    execute_activity(ctx1, require_enabled=False)
    try:
        execute_activity(_context(execution_id="exec_dup"), require_enabled=False)
        results.append(_ok("duplicate execution_id rejected", False))
    except DuplicateExecutionIdError:
        results.append(_ok("duplicate execution_id rejected", True))

    # Missing executor (empty registry)
    empty = SkillExecutorRegistry(executors=())
    reset_default_execution_id_guard_for_tests()
    try:
        execute_activity(_context(execution_id="exec_empty_reg"), registry=empty, require_enabled=False)
        results.append(_ok("missing executor rejected", False))
    except MissingExecutorError:
        results.append(_ok("missing executor rejected", True))
    except Exception as exc:  # noqa: BLE001
        results.append(_ok("missing executor rejected", False, str(exc)))

    # Disabled by flags
    with patch(
        "app.services.language_grammar_skill_executor.lifecycle.skill_executor_enabled",
        return_value=False,
    ):
        reset_default_execution_id_guard_for_tests()
        disabled_ctx = _context(execution_id="exec_disabled")
        from app.services.language_grammar_skill_executor import ExecutionFeatureFlags

        disabled_ctx = ExecutionContext(
            specification=disabled_ctx.specification,
            student=disabled_ctx.student,
            runtime_session_id=disabled_ctx.runtime_session_id,
            blueprint_id=disabled_ctx.blueprint_id,
            execution_id="exec_disabled",
            feature_flags=ExecutionFeatureFlags(
                grammar_engine_enabled=False,
                skill_executor_enabled=False,
            ),
            metadata=disabled_ctx.metadata,
        )
        try:
            execute_activity(disabled_ctx, require_enabled=True)
            results.append(_ok("disabled flag rejects execution", False))
        except SkillExecutorDisabledError:
            results.append(_ok("disabled flag rejects execution", True))

    reset_default_execution_id_guard_for_tests()
    ok = execute_activity(_context(execution_id="exec_ok_final"), require_enabled=False)
    results.append(_ok("happy path completed", ok.status is ExecutionStatus.completed))
    print()
    return results


def main() -> int:
    print("Grammar G3.4 Skill Execution Framework verification\n")
    all_results: list[bool] = []
    all_results.extend(audit_1_registry_integrity())
    all_results.extend(audit_2_lifecycle_integrity())
    all_results.extend(audit_3_evidence_isolation())
    all_results.extend(audit_4_architecture())
    all_results.extend(audit_5_plugin_extensibility())
    all_results.extend(audit_6_activity_coverage())
    all_results.extend(check_contracts_and_validation())

    passed = sum(1 for r in all_results if r)
    failed = sum(1 for r in all_results if not r)
    print(f"Summary: {passed} passed, {failed} failed, {len(all_results)} total")
    if failed:
        print("G3.4 VERDICT: NOT READY")
        return 1
    print("G3.4 VERDICT: READY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
