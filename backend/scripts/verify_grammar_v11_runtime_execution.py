"""Verify Grammar V1.1 — Runtime Skill Execution Wiring.

Usage (from backend/):
    python scripts/verify_grammar_v11_runtime_execution.py
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

BACKEND = Path(__file__).resolve().parents[1]
SERVICES = BACKEND / "app" / "services"
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


def _sample_blueprint():
    from app.services.language_grammar.enums import (
        GrammarCEFRBand,
        GrammarLessonStepKind,
        GrammarReinforcementSkill,
    )
    from app.services.language_grammar_lesson_planner.types import (
        GrammarCompletionCriteria,
        GrammarEvidencePlan,
        GrammarLessonBlueprint,
        GrammarLessonStep,
        GrammarPracticeSpec,
    )

    steps = (
        GrammarLessonStep(kind=GrammarLessonStepKind.explanation, step_id="explanation"),
        GrammarLessonStep(
            kind=GrammarLessonStepKind.practice,
            step_id="practice",
            evidence_eligible=True,
            context_hint="cafe",
        ),
        GrammarLessonStep(
            kind=GrammarLessonStepKind.speaking_reinforcement,
            step_id="reinforce_speaking",
            skill=GrammarReinforcementSkill.speaking,
            evidence_eligible=True,
        ),
        GrammarLessonStep(
            kind=GrammarLessonStepKind.exit_check,
            step_id="exit_check",
            evidence_eligible=True,
        ),
        GrammarLessonStep(kind=GrammarLessonStepKind.summary, step_id="summary"),
    )
    return GrammarLessonBlueprint(
        grammar_id="gram_present_simple",
        target_cefr=GrammarCEFRBand.A1,
        objectives=("Use present simple",),
        steps=steps,
        practice_spec=GrammarPracticeSpec(item_count=3),
        evidence_plan=GrammarEvidencePlan(eligible_step_ids=("practice", "reinforce_speaking", "exit_check")),
        fingerprint="fp_v11",
        lesson_id="gless_v11",
        lesson_goal="Use present simple",
        estimated_duration_minutes=20,
        completion_criteria=GrammarCompletionCriteria(require_exit_check=True),
        catalog_version="1.0.0",
        frozen=True,
        enabled=True,
    )


def audit_1_registry_wiring() -> list[bool]:
    print("[Audit 1 - Registry Wiring]")
    results: list[bool] = []
    from app.services.language_grammar_lesson_runtime.dispatcher import dispatch_step
    from app.services.language_grammar_lesson_runtime.executors import get_default_registry
    from app.services.language_grammar_skill_executor import (
        ExecutionIdGuard,
        get_default_skill_executor_registry,
    )

    bp = _sample_blueprint()
    step = bp.steps[1]  # practice -> multiple_choice activity
    skill_reg = get_default_skill_executor_registry()
    result = dispatch_step(
        step,
        bp,
        registry=get_default_registry(),
        student_id=1,
        language_id=1,
        lesson_id=bp.lesson_id,
        step_index=1,
        as_of="2026-01-01T00:00:00Z",
        skill_registry=skill_reg,
        execution_guard=ExecutionIdGuard(),
    )
    results.append(_ok("dispatch succeeds", result.success))
    results.append(_ok("skill_executor_id set", bool(result.skill_executor_id)))
    results.append(_ok("execution_id set", bool(result.execution_id)))
    results.append(
        _ok(
            "skill executor resolved from registry",
            result.skill_executor_id in skill_reg.ids(),
            str(result.skill_executor_id),
        )
    )
    results.append(_ok("Audit 1 verdict", all(results)))
    print()
    return results


def audit_2_runtime_isolation() -> list[bool]:
    print("[Audit 2 - Runtime Isolation]")
    results: list[bool] = []
    deps: set[str] = set()
    for py in RUNTIME_PKG.rglob("*.py"):
        deps |= _parse_imports(py)

    results.append(_ok("runtime depends on skill_executor", "language_grammar_skill_executor" in deps))
    # Must not import concrete plugin classes into dispatcher
    dispatcher = (RUNTIME_PKG / "dispatcher.py").read_text(encoding="utf-8")
    bridge = (RUNTIME_PKG / "skill_execution_bridge.py").read_text(encoding="utf-8")
    combined = dispatcher + bridge
    for bad in (
        "SpeakingExecutor",
        "ReadingExecutor",
        "WritingExecutor",
        "ListeningExecutor",
        "MultipleChoiceExecutor",
        "from app.services.language_grammar_skill_executor.plugins",
    ):
        results.append(_ok(f"no concrete plugin import: {bad.split('.')[-1]}", bad not in combined))

    runtime_src = "\n".join(p.read_text(encoding="utf-8") for p in RUNTIME_PKG.rglob("*.py"))
    for bad in (
        'if activity == "speaking"',
        "if activity == 'speaking'",
        "if activity_type ==",
        'if activity == "writing"',
    ):
        results.append(_ok(f"no hardcoded route: {bad!r}", bad not in runtime_src))

    for forbidden in (
        "language_grammar_mastery",
        "language_grammar_progression",
        "language_grammar_review",
        "claude_service",
    ):
        results.append(_ok(f"runtime does not import {forbidden}", forbidden not in deps))

    results.append(_ok("Audit 2 verdict", all(results)))
    print()
    return results


def audit_3_lifecycle_execution() -> list[bool]:
    print("[Audit 3 - Lifecycle Execution]")
    results: list[bool] = []
    from app.services.language_grammar_lesson_runtime.dispatcher import dispatch_step
    from app.services.language_grammar_skill_executor import ExecutionIdGuard, ExecutionStatus

    bp = _sample_blueprint()
    result = dispatch_step(
        bp.steps[1],
        bp,
        student_id=1,
        language_id=1,
        lesson_id=bp.lesson_id,
        step_index=1,
        as_of="2026-02-01T00:00:00Z",
        execution_guard=ExecutionIdGuard(),
    )
    exe = result.execution_result
    results.append(_ok("execution_result present", exe is not None))
    assert exe is not None
    phases = set(exe.executor_metadata.lifecycle_phases_completed)
    for phase in ("initialize", "prepare", "validate", "execute", "complete", "cleanup"):
        results.append(_ok(f"lifecycle phase {phase}", phase in phases))
    results.append(_ok("status completed", exe.status is ExecutionStatus.completed))
    results.append(_ok("Audit 3 verdict", all(results)))
    print()
    return results


def audit_4_evidence_flow() -> list[bool]:
    print("[Audit 4 - Evidence Flow]")
    results: list[bool] = []
    from app.services.language_grammar_evidence.types import GrammarEvidenceObservation
    from app.services.language_grammar_lesson_runtime.dispatcher import dispatch_step
    from app.services.language_grammar_lesson_runtime.orchestrator import run_to_completion
    from app.services.language_grammar_skill_executor import ExecutionIdGuard

    bp = _sample_blueprint()
    result = dispatch_step(
        bp.steps[1],
        bp,
        student_id=1,
        language_id=1,
        lesson_id=bp.lesson_id,
        step_index=1,
        as_of="2026-03-01T00:00:00Z",
        execution_guard=ExecutionIdGuard(),
    )
    exe = result.execution_result
    assert exe is not None
    results.append(_ok("generated_evidence non-empty", len(exe.generated_evidence) >= 1))
    results.append(
        _ok(
            "evidence is GrammarEvidenceObservation",
            all(isinstance(o, GrammarEvidenceObservation) for o in exe.generated_evidence),
        )
    )
    results.append(_ok("compat evidence_request present", result.evidence_request is not None))

    session = run_to_completion(student_id=1, language_id=1, blueprint=bp, at="2026-03-02T00:00:00Z")
    results.append(_ok("session stores step_executions", len(session.step_executions) == len(bp.steps)))
    results.append(
        _ok(
            "step records track evidence ids",
            any(r.evidence_observation_ids for r in session.step_executions),
        )
    )
    results.append(_ok("Audit 4 verdict", all(results)))
    print()
    return results


def audit_5_error_handling() -> list[bool]:
    print("[Audit 5 - Error Handling]")
    results: list[bool] = []
    from dataclasses import replace

    from app.services.language_grammar_activity_spec import build_minimal_specification
    from app.services.language_grammar_lesson_runtime.dispatcher import GrammarRuntimeError, dispatch_step
    from app.services.language_grammar_lesson_runtime.skill_execution_bridge import (
        SkillExecutionBridgeError,
        run_skill_execution,
    )
    from app.services.language_grammar_skill_executor import ExecutionIdGuard, SkillExecutorRegistry

    bp = _sample_blueprint()

    # Missing executor via empty registry
    try:
        dispatch_step(
            bp.steps[1],
            bp,
            student_id=1,
            language_id=1,
            lesson_id="err_missing",
            step_index=1,
            as_of="2026-04-01T00:00:00Z",
            skill_registry=SkillExecutorRegistry(executors=()),
            execution_guard=ExecutionIdGuard(),
        )
        results.append(_ok("missing executor raises", False))
    except GrammarRuntimeError as exc:
        results.append(_ok("missing executor raises", "missing_executor" in str(exc)))

    # Unknown activity type
    bad_spec = replace(build_minimal_specification(validate=False), activity_type="not_a_type_v11")
    try:
        run_skill_execution(
            bad_spec,
            student_id=1,
            language_id=1,
            lesson_id="err_type",
            blueprint_fingerprint="fp",
            step_index=0,
            as_of="2026-04-02T00:00:00Z",
            guard=ExecutionIdGuard(),
        )
        results.append(_ok("unknown activity type raises", False))
    except SkillExecutionBridgeError as exc:
        results.append(_ok("unknown activity type raises", exc.code == "unknown_activity_type"))

    # Validation failure (missing completion rules)
    bare = replace(build_minimal_specification(validate=False), completion_rules=())
    try:
        run_skill_execution(
            bare,
            student_id=1,
            language_id=1,
            lesson_id="err_val",
            blueprint_fingerprint="fp",
            step_index=0,
            as_of="2026-04-03T00:00:00Z",
            guard=ExecutionIdGuard(),
        )
        results.append(_ok("validation failure raises", False))
    except SkillExecutionBridgeError as exc:
        results.append(_ok("validation failure raises", exc.code == "validation_failure"))

    # Duplicate execution id
    guard = ExecutionIdGuard()
    run_skill_execution(
        build_minimal_specification(),
        student_id=1,
        language_id=1,
        lesson_id="err_dup",
        blueprint_fingerprint="fp",
        step_index=0,
        as_of="same-stamp",
        guard=guard,
    )
    try:
        run_skill_execution(
            build_minimal_specification(),
            student_id=1,
            language_id=1,
            lesson_id="err_dup",
            blueprint_fingerprint="fp",
            step_index=0,
            as_of="same-stamp",
            guard=guard,
        )
        results.append(_ok("duplicate execution_id raises", False))
    except SkillExecutionBridgeError as exc:
        results.append(_ok("duplicate execution_id raises", exc.code == "duplicate_execution_id"))

    # Cancellation
    cancelled = run_skill_execution(
        build_minimal_specification(),
        student_id=1,
        language_id=1,
        lesson_id="err_cancel",
        blueprint_fingerprint="fp",
        step_index=0,
        as_of="2026-04-04T00:00:00Z",
        guard=ExecutionIdGuard(),
        cancel=True,
        cancel_reason="user_cancel",
    )
    results.append(_ok("cancellation status", cancelled.status.value == "cancelled"))

    results.append(_ok("Audit 5 verdict", all(results)))
    print()
    return results


def audit_6_backward_compatibility() -> list[bool]:
    print("[Audit 6 - Backward Compatibility]")
    results: list[bool] = []
    from app.services.language_grammar_lesson_runtime.dispatcher import dispatch_step
    from app.services.language_grammar_lesson_runtime.executors import get_default_registry
    from app.services.language_grammar_lesson_runtime.orchestrator import run_to_completion
    from app.services.language_grammar_lesson_runtime.types import GrammarRuntimeState
    from app.services.language_grammar_skill_executor import ExecutionIdGuard

    bp = _sample_blueprint()
    reg = get_default_registry()
    for step in bp.steps:
        ex = reg.resolve(step.kind)
        result = dispatch_step(
            step,
            bp,
            registry=reg,
            student_id=1,
            language_id=1,
            lesson_id=bp.lesson_id,
            step_index=list(bp.steps).index(step),
            as_of=f"2026-05-01T00:00:0{list(bp.steps).index(step)}Z",
            execution_guard=ExecutionIdGuard(),
        )
        results.append(
            _ok(
                f"compat executor_id for {step.step_id}",
                result.success and result.executor_id == ex.executor_id,
                f"{result.executor_id} vs {ex.executor_id}",
            )
        )
        results.append(_ok(f"compat activity_specification {step.step_id}", result.activity_specification is not None))

    session = run_to_completion(student_id=1, language_id=1, blueprint=bp, at="2026-05-02T00:00:00Z")
    results.append(_ok("run_to_completion completes", session.state is GrammarRuntimeState.completed))
    results.append(_ok("evidence_requests still emitted", len(session.evidence_requests) >= 1))

    # G3.2 verify still passes
    import subprocess

    proc = subprocess.run(
        [sys.executable, str(BACKEND / "scripts" / "verify_grammar_g32_runtime.py")],
        cwd=str(BACKEND),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    results.append(_ok("G3.2 verify still READY", proc.returncode == 0, (proc.stdout or "")[-200:]))

    results.append(_ok("Audit 6 verdict", all(results)))
    print()
    return results


def check_tracking() -> list[bool]:
    print("[Tracking]")
    results: list[bool] = []
    from app.services.language_grammar_lesson_runtime.orchestrator import run_to_completion
    from app.services.language_grammar_lesson_runtime.storage import (
        bucket_from_session,
        session_from_bucket,
    )

    bp = _sample_blueprint()
    session = run_to_completion(student_id=1, language_id=1, blueprint=bp, at="2026-06-01T00:00:00Z")
    rec = session.step_executions[0]
    results.append(_ok("tracks execution_id", bool(rec.execution_id)))
    results.append(_ok("tracks skill_executor_id", bool(rec.skill_executor_id)))
    results.append(_ok("tracks status", bool(rec.status)))
    results.append(_ok("tracks lifecycle phases", len(rec.lifecycle_phases) >= 5))
    results.append(_ok("tracks duration_ms", rec.duration_ms >= 0))

    bucket = bucket_from_session(session, blueprint=bp)
    restored = session_from_bucket(bucket)
    assert restored is not None
    results.append(
        _ok(
            "step_executions roundtrip",
            restored.step_executions == session.step_executions,
        )
    )
    print()
    return results


def main() -> int:
    print("Grammar V1.1 Runtime Skill Execution Wiring verification\n")
    all_results: list[bool] = []
    all_results.extend(audit_1_registry_wiring())
    all_results.extend(audit_2_runtime_isolation())
    all_results.extend(audit_3_lifecycle_execution())
    all_results.extend(audit_4_evidence_flow())
    all_results.extend(audit_5_error_handling())
    all_results.extend(audit_6_backward_compatibility())
    all_results.extend(check_tracking())

    passed = sum(1 for r in all_results if r)
    failed = sum(1 for r in all_results if not r)
    print(f"Summary: {passed} passed, {failed} failed, {len(all_results)} total")
    if failed:
        print("V1.1 VERDICT: NOT READY")
        return 1
    print("V1.1 VERDICT: READY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
