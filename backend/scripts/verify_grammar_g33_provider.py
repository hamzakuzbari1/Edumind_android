"""Verify Grammar G3.3 Activity Provider Framework.

Usage (from backend/):
    python scripts/verify_grammar_g33_provider.py
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

BACKEND = Path(__file__).resolve().parents[1]
SERVICES = BACKEND / "app" / "services"
PROVIDER_PKG = SERVICES / "language_grammar_activity_provider"
RUNTIME_PKG = SERVICES / "language_grammar_lesson_runtime"


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
                if len(parts) >= 4:
                    imports.add(f"{parts[2]}.{parts[3]}")
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("app.services."):
                    parts = alias.name.split(".")
                    if len(parts) >= 3:
                        imports.add(parts[2])
    return imports


def _pkg_deps(pkg_dir: Path) -> set[str]:
    deps: set[str] = set()
    for py in pkg_dir.rglob("*.py"):
        deps |= _parse_imports(py)
    return deps


def _context():
    from app.services.language_grammar.enums import GrammarCEFRBand, GrammarLessonStepKind
    from app.services.language_grammar_activity_provider import (
        ActivityExecutionContext,
        GrammarRuntimeContext,
        GrammarStudentContext,
    )
    from app.services.language_grammar_lesson_planner.types import (
        GrammarLessonBlueprint,
        GrammarLessonStep,
    )

    step = GrammarLessonStep(
        kind=GrammarLessonStepKind.practice,
        step_id="practice",
        evidence_eligible=True,
        title="Practice",
        context_hint="cafe",
    )
    blueprint = GrammarLessonBlueprint(
        grammar_id="gram_present_simple",
        target_cefr=GrammarCEFRBand.A1,
        objectives=("Use present simple",),
        steps=(step,),
        fingerprint="fp_g33",
        lesson_id="gless_g33",
        lesson_goal="Use present simple",
        estimated_duration_minutes=10,
        catalog_version="1.0.0",
        frozen=True,
        enabled=True,
    )
    return ActivityExecutionContext(
        blueprint=blueprint,
        step=step,
        runtime=GrammarRuntimeContext(
            lesson_id=blueprint.lesson_id,
            grammar_id=blueprint.grammar_id,
            blueprint_fingerprint=blueprint.fingerprint,
            step_index=0,
            as_of="2026-01-01T00:00:00Z",
        ),
        student=GrammarStudentContext(student_id=1, language_id=1, overall_cefr="A1"),
    )


def audit_1_provider_isolation() -> list[bool]:
    print("[Audit 1 - Provider Isolation]")
    results: list[bool] = []
    deps = _pkg_deps(PROVIDER_PKG)
    for bad in (
        "claude_service",
        "language_grammar_lesson_runtime",
        "language_grammar_mastery",
        "language_grammar_progression",
        "language_grammar_review",
        "language_grammar_educational_package",
    ):
        results.append(_ok(f"provider package does not import {bad}", bad not in deps))

    # No HTTP / anthropic style imports in provider package source
    src = "\n".join(p.read_text(encoding="utf-8") for p in PROVIDER_PKG.rglob("*.py"))
    results.append(_ok("no anthropic SDK usage", "anthropic" not in src.lower()))
    results.append(_ok("no httpx/openai client usage", "openai" not in src.lower() and "httpx" not in src))
    results.append(
        _ok(
            "claude provider is stub",
            "no API call" in src and "ClaudeProvider" in src,
        )
    )
    results.append(_ok("Audit 1 verdict", all(results)))
    print()
    return results


def audit_2_dependency_direction() -> list[bool]:
    print("[Audit 2 - Dependency Direction]")
    results: list[bool] = []
    from app.services.language_grammar.ownership import (
        ALLOWED_PACKAGE_DEPENDENCIES,
        ARCHITECTURE_LAYERS,
        PACKAGE_LAYER,
    )

    allowed = ALLOWED_PACKAGE_DEPENDENCIES["language_grammar_activity_provider"]
    deps = {d for d in _pkg_deps(PROVIDER_PKG) if d.startswith("language_grammar_")}
    unexpected = {d.split(".")[0] for d in deps} - set(allowed) - {"language_grammar_activity_provider", "language_grammar"}
    results.append(_ok("provider deps subset of allowed", not unexpected, str(sorted(unexpected))))
    results.append(
        _ok(
            "provider may import planner",
            "language_grammar_lesson_planner" in {d.split(".")[0] for d in deps},
        )
    )

    # Runtime -> activity_provider allowed; reverse forbidden
    runtime_deps = _pkg_deps(RUNTIME_PKG)
    results.append(
        _ok(
            "runtime depends on activity_provider",
            "language_grammar_activity_provider" in runtime_deps,
        )
    )
    results.append(
        _ok(
            "activity_provider does not depend on runtime",
            "language_grammar_lesson_runtime" not in deps,
        )
    )

    layer_index = {n: i for i, n in enumerate(ARCHITECTURE_LAYERS)}
    prov_layer = PACKAGE_LAYER["language_grammar_activity_provider"]
    run_layer = PACKAGE_LAYER["language_grammar_lesson_runtime"]
    results.append(
        _ok(
            "activity layer before runtime",
            layer_index[prov_layer] < layer_index[run_layer],
        )
    )
    results.append(_ok("Audit 2 verdict", all(results)))
    print()
    return results


def audit_3_runtime_independence() -> list[bool]:
    print("[Audit 3 - Runtime Independence]")
    results: list[bool] = []
    runtime_src = "\n".join(p.read_text(encoding="utf-8") for p in RUNTIME_PKG.rglob("*.py"))
    results.append(_ok("runtime does not import ClaudeProvider class", "ClaudeProvider" not in runtime_src))
    results.append(_ok("runtime does not import TemplateProvider class", "TemplateProvider" not in runtime_src))
    results.append(
        _ok(
            "runtime uses provide_activity / interface",
            "provide_activity" in runtime_src
            and "ActivityExecutionContext" in runtime_src,
        )
    )

    # Swapping provider via flag changes activity without Runtime code edits
    from app.services.language_grammar_activity_provider import (
        GrammarActivityProviderId,
        provide_activity,
    )
    from app.services.language_grammar_lesson_runtime.dispatcher import dispatch_step

    ctx = _context()
    with patch(
        "app.services.language_grammar_activity_provider.resolution.configured_provider_id",
        return_value=GrammarActivityProviderId.template,
    ):
        a1 = provide_activity(ctx)
    with patch(
        "app.services.language_grammar_activity_provider.resolution.configured_provider_id",
        return_value=GrammarActivityProviderId.cached,
    ):
        a2 = provide_activity(ctx)
    results.append(
        _ok(
            "swap provider without runtime edits",
            a1.provider_metadata.provider_id != a2.provider_metadata.provider_id,
        )
    )

    result = dispatch_step(
        ctx.step,
        ctx.blueprint,
        student_id=1,
        language_id=1,
        lesson_id=ctx.runtime.lesson_id,
        preferred_provider=GrammarActivityProviderId.template,
    )
    results.append(_ok("dispatcher attaches activity_id", bool(result.activity_id)))
    results.append(
        _ok(
            "dispatcher attaches provider_id",
            result.activity_provider_id == GrammarActivityProviderId.template.value,
        )
    )
    results.append(
        _ok(
            "dispatcher attaches ActivitySpecification",
            result.activity_specification is not None
            and result.activity_specification.activity_id == result.activity_id,
        )
    )
    results.append(_ok("Audit 3 verdict", all(results)))
    print()
    return results


def audit_4_future_extensibility() -> list[bool]:
    print("[Audit 4 - Future Extensibility]")
    results: list[bool] = []
    from app.services.language_grammar_activity_provider import (
        GrammarActivityProvider,
        GrammarActivityProviderId,
        GrammarActivityProviderRegistry,
        build_activity_specification,
        get_default_provider_registry,
        provide_activity,
        resolve_provider,
    )
    from app.services.language_grammar_activity_spec import ActivitySpecification

    reg = get_default_provider_registry()
    for pid in (
        GrammarActivityProviderId.template,
        GrammarActivityProviderId.cached,
        GrammarActivityProviderId.claude,
        GrammarActivityProviderId.future_llm,
    ):
        results.append(_ok(f"registry has {pid.value}", pid in reg.ids()))

    ctx = _context()

    class _Alt:
        provider_id = GrammarActivityProviderId.template

        def supports(self, context) -> bool:
            return True

        def provide(self, context) -> ActivitySpecification:
            spec = build_activity_specification(
                context,
                provider_id=GrammarActivityProviderId.template,
                title="alt",
                goal="alt goal",
                instructions="custom registry provider",
                generation_mode="template",
            )
            # Force stable id for injectability check
            from dataclasses import replace

            return replace(spec, activity_id="alt:custom")

    custom_reg = GrammarActivityProviderRegistry(providers=(_Alt(),))  # type: ignore[arg-type]
    out = provide_activity(ctx, registry=custom_reg)
    results.append(_ok("custom registry injectable", out.activity_id == "alt:custom"))
    results.append(_ok("provider satisfies protocol", isinstance(resolve_provider(ctx), GrammarActivityProvider)))

    # Deterministic selection
    runs = [provide_activity(ctx, preferred=GrammarActivityProviderId.claude) for _ in range(5)]
    results.append(
        _ok(
            "selection deterministic",
            all(
                r.provider_metadata.provider_id == GrammarActivityProviderId.claude.value
                and r.activity_id == runs[0].activity_id
                for r in runs
            ),
        )
    )
    results.append(
        _ok(
            "result is ActivitySpecification not runtime state",
            isinstance(runs[0], ActivitySpecification)
            and not hasattr(runs[0], "state")
            and runs[0].step_id == ctx.step.step_id,
        )
    )
    results.append(_ok("Audit 4 verdict", all(results)))
    print()
    return results


def check_contracts_and_flags() -> list[bool]:
    print("[Contracts & flags]")
    results: list[bool] = []
    from app.core.config import get_settings
    from app.services.language_grammar_activity_provider import (
        GrammarActivityProviderId,
        configured_provider_id,
        provide_activity,
    )
    from app.services.language_grammar_activity_spec import ActivitySpecification

    settings = get_settings()
    results.append(_ok("LANG_GRAMMAR_ACTIVITY_PROVIDER defined", hasattr(settings, "LANG_GRAMMAR_ACTIVITY_PROVIDER")))
    results.append(_ok("configured_provider_id valid", isinstance(configured_provider_id(), GrammarActivityProviderId)))

    ctx = _context()
    result = provide_activity(ctx, preferred=GrammarActivityProviderId.future_llm)
    results.append(_ok("returns ActivitySpecification", isinstance(result, ActivitySpecification)))
    results.append(_ok("ActivitySpecification fields", bool(result.activity_id and result.instructions)))
    results.append(
        _ok(
            "future_llm stub has deferred prompt",
            "deferred" in result.payload.get("prompt_stub", ""),
        )
    )

    with patch(
        "app.core.config.get_settings"
    ) as gs:
        class _S:
            LANG_GRAMMAR_ENGINE_ENABLED = True
            LANG_GRAMMAR_ACTIVITY_PROVIDER = "nope"

        gs.return_value = _S()
        from app.services.language_grammar_activity_provider.flags import configured_provider_id as cfg

        results.append(_ok("invalid provider falls back to template", cfg() is GrammarActivityProviderId.template))

    print()
    return results


def main() -> int:
    print("Grammar G3.3 Activity Provider Framework verification\n")
    all_results: list[bool] = []
    all_results.extend(audit_1_provider_isolation())
    all_results.extend(audit_2_dependency_direction())
    all_results.extend(audit_3_runtime_independence())
    all_results.extend(audit_4_future_extensibility())
    all_results.extend(check_contracts_and_flags())

    passed = sum(1 for r in all_results if r)
    failed = sum(1 for r in all_results if not r)
    print(f"Summary: {passed} passed, {failed} failed, {len(all_results)} total")
    if failed:
        print("G3.3 VERDICT: NOT READY")
        return 1
    print("G3.3 VERDICT: READY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
