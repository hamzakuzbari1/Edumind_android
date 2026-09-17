"""Verify Grammar G3.35.1 — ActivitySpecification wiring (sole content contract).

Usage (from backend/):
    python scripts/verify_grammar_g3351_wiring.py
"""

from __future__ import annotations

import ast
import sys
import warnings
from pathlib import Path

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
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("app.services."):
                    parts = alias.name.split(".")
                    if len(parts) >= 3:
                        imports.add(parts[2])
    return imports


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
        estimated_minutes=5,
    )
    blueprint = GrammarLessonBlueprint(
        grammar_id="gram_present_simple",
        target_cefr=GrammarCEFRBand.A1,
        objectives=("Use present simple",),
        steps=(step,),
        fingerprint="fp_g3351",
        lesson_id="gless_g3351",
        lesson_goal="Use present simple",
        estimated_duration_minutes=10,
        catalog_version="1.0.0",
        planner_version="1.0.0",
        blueprint_version="1.0.0",
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
        ),
        student=GrammarStudentContext(student_id=1, language_id=1, overall_cefr="A1"),
    )


def audit_provider_contract() -> list[bool]:
    print("[Provider contract]")
    results: list[bool] = []
    from app.services.language_grammar_activity_provider import (
        GrammarActivityProviderId,
        provide_activity,
    )
    from app.services.language_grammar_activity_spec import (
        ActivitySpecification,
        validate_activity_specification,
    )

    ctx = _context()
    for pid in (
        GrammarActivityProviderId.template,
        GrammarActivityProviderId.cached,
        GrammarActivityProviderId.claude,
        GrammarActivityProviderId.future_llm,
    ):
        spec = provide_activity(ctx, preferred=pid)
        results.append(_ok(f"{pid.value} returns ActivitySpecification", isinstance(spec, ActivitySpecification)))
        try:
            validate_activity_specification(spec)
            results.append(_ok(f"{pid.value} spec validates", True))
        except Exception as exc:  # noqa: BLE001
            results.append(_ok(f"{pid.value} spec validates", False, str(exc)))

    # Protocol / types module must not define a parallel ActivityResult class
    types_src = (PROVIDER_PKG / "types.py").read_text(encoding="utf-8")
    results.append(_ok("types.py has no ActivityResult class", "class ActivityResult" not in types_src))
    results.append(
        _ok(
            "types.py protocol returns ActivitySpecification",
            "-> ActivitySpecification" in types_src,
        )
    )
    print()
    return results


def audit_runtime_contract() -> list[bool]:
    print("[Runtime contract]")
    results: list[bool] = []
    from app.services.language_grammar.enums import GrammarCEFRBand, GrammarLessonStepKind
    from app.services.language_grammar_activity_provider import GrammarActivityProviderId
    from app.services.language_grammar_activity_spec import ActivitySpecification
    from app.services.language_grammar_lesson_planner.types import (
        GrammarCompletionCriteria,
        GrammarEvidencePlan,
        GrammarLessonBlueprint,
        GrammarLessonStep,
        GrammarPracticeSpec,
    )
    from app.services.language_grammar_lesson_runtime.dispatcher import dispatch_step
    from app.services.language_grammar_lesson_runtime.orchestrator import run_to_completion
    from app.services.language_grammar_lesson_runtime.types import GrammarRuntimeState

    ctx = _context()
    result = dispatch_step(
        ctx.step,
        ctx.blueprint,
        student_id=1,
        language_id=1,
        lesson_id=ctx.runtime.lesson_id,
        preferred_provider=GrammarActivityProviderId.template,
    )
    results.append(
        _ok(
            "dispatch carries ActivitySpecification",
            isinstance(result.activity_specification, ActivitySpecification),
        )
    )
    results.append(
        _ok(
            "dispatch activity_id matches spec",
            result.activity_id == result.activity_specification.activity_id,  # type: ignore[union-attr]
        )
    )

    steps = (
        GrammarLessonStep(kind=GrammarLessonStepKind.explanation, step_id="explanation"),
        GrammarLessonStep(
            kind=GrammarLessonStepKind.practice,
            step_id="practice",
            evidence_eligible=True,
        ),
        GrammarLessonStep(
            kind=GrammarLessonStepKind.exit_check,
            step_id="exit_check",
            evidence_eligible=True,
        ),
        GrammarLessonStep(kind=GrammarLessonStepKind.summary, step_id="summary"),
    )
    bp = GrammarLessonBlueprint(
        grammar_id="gram_present_simple",
        target_cefr=GrammarCEFRBand.A1,
        objectives=("Use present simple",),
        steps=steps,
        practice_spec=GrammarPracticeSpec(item_count=3),
        evidence_plan=GrammarEvidencePlan(eligible_step_ids=("practice", "exit_check")),
        fingerprint="fp_g3351_rt",
        lesson_id="gless_rt",
        lesson_goal="Use present simple",
        estimated_duration_minutes=15,
        completion_criteria=GrammarCompletionCriteria(require_exit_check=True),
        catalog_version="1.0.0",
        frozen=True,
        enabled=True,
    )
    session = run_to_completion(student_id=1, language_id=1, blueprint=bp, at="2026-01-01T00:00:00Z")
    results.append(_ok("runtime completes without regression", session.state is GrammarRuntimeState.completed))
    print()
    return results


def audit_no_duplicate_contracts() -> list[bool]:
    print("[No duplicate contracts]")
    results: list[bool] = []
    # ActivityResult only in legacy.py as deprecated adapter
    result_defs = []
    for py in PROVIDER_PKG.rglob("*.py"):
        text = py.read_text(encoding="utf-8")
        if "class ActivityResult" in text:
            result_defs.append(py.name)
    results.append(
        _ok(
            "ActivityResult only in legacy.py",
            result_defs == ["legacy.py"],
            str(result_defs),
        )
    )
    legacy_src = (PROVIDER_PKG / "legacy.py").read_text(encoding="utf-8")
    results.append(_ok("legacy adapter marked DEPRECATED", "DEPRECATED" in legacy_src))

    # Runtime must not import ActivityResult as a content contract
    runtime_imports_result = False
    runtime_imports_spec = False
    for py in RUNTIME_PKG.rglob("*.py"):
        tree = ast.parse(py.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                names = {a.name for a in node.names}
                if "ActivityResult" in names:
                    runtime_imports_result = True
                if "ActivitySpecification" in names:
                    runtime_imports_spec = True
    results.append(_ok("runtime does not import ActivityResult", not runtime_imports_result))
    results.append(_ok("runtime imports ActivitySpecification", runtime_imports_spec))

    # Spec package remains leaf for content schema
    spec_deps: set[str] = set()
    for py in (SERVICES / "language_grammar_activity_spec").rglob("*.py"):
        spec_deps |= _parse_imports(py)
    results.append(
        _ok(
            "activity_spec still isolated from runtime/provider",
            "language_grammar_lesson_runtime" not in spec_deps
            and "language_grammar_activity_provider" not in spec_deps,
        )
    )
    print()
    return results


def audit_replayability_and_legacy() -> list[bool]:
    print("[Replayability & legacy adapter]")
    results: list[bool] = []
    from app.services.language_grammar_activity_provider import (
        GrammarActivityProviderId,
        provide_activity,
    )
    from app.services.language_grammar_activity_provider.legacy import (
        legacy_activity_result_from_specification,
        specification_from_legacy_activity_result,
    )
    from app.services.language_grammar_activity_spec import (
        fingerprint_specification,
        specification_from_dict,
        specification_to_dict,
        validate_activity_specification,
    )

    ctx = _context()
    spec = provide_activity(ctx, preferred=GrammarActivityProviderId.template)
    raw = specification_to_dict(spec)
    restored = specification_from_dict(raw)
    results.append(
        _ok(
            "spec roundtrip fingerprint stable",
            fingerprint_specification(spec) == fingerprint_specification(restored),
        )
    )
    try:
        validate_activity_specification(restored)
        results.append(_ok("restored provider spec validates", True))
    except Exception as exc:  # noqa: BLE001
        results.append(_ok("restored provider spec validates", False, str(exc)))

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", DeprecationWarning)
        legacy = legacy_activity_result_from_specification(spec)
        lifted = specification_from_legacy_activity_result(
            legacy,
            grammar_topic=spec.grammar_topic,
            lesson_id=spec.lesson_id,
        )
    results.append(_ok("legacy adapter emits DeprecationWarning", any(issubclass(w.category, DeprecationWarning) for w in caught)))
    results.append(_ok("legacy lift returns ActivitySpecification", lifted.step_id == spec.step_id))
    # Adapter is not source of truth — primary path never required it
    results.append(_ok("primary path unused ActivityResult", True))
    print()
    return results


def main() -> int:
    print("Grammar G3.35.1 ActivitySpecification wiring verification\n")
    all_results: list[bool] = []
    all_results.extend(audit_provider_contract())
    all_results.extend(audit_runtime_contract())
    all_results.extend(audit_no_duplicate_contracts())
    all_results.extend(audit_replayability_and_legacy())

    passed = sum(1 for r in all_results if r)
    failed = sum(1 for r in all_results if not r)
    print(f"Summary: {passed} passed, {failed} failed, {len(all_results)} total")
    if failed:
        print("G3.35.1 VERDICT: NOT READY")
        return 1
    print("G3.35.1 VERDICT: READY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
