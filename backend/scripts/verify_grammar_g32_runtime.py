"""Verify Grammar G3.2 Runtime Orchestrator.

Usage (from backend/):
    python scripts/verify_grammar_g32_runtime.py
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path
from unittest.mock import patch

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
                # track submodule for planner surface check
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
            kind=GrammarLessonStepKind.reading_reinforcement,
            step_id="reinforce_reading",
            skill=GrammarReinforcementSkill.reading,
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
        evidence_plan=GrammarEvidencePlan(
            eligible_step_ids=("practice", "reinforce_reading", "exit_check"),
            min_observations=1,
        ),
        fingerprint="fp_g32_test_001",
        lesson_id="gless_test_1",
        lesson_goal="Use present simple",
        estimated_duration_minutes=20,
        completion_criteria=GrammarCompletionCriteria(require_exit_check=True),
        catalog_version="1.0.0",
        frozen=True,
        enabled=True,
    )


def audit_1_runtime_integrity() -> list[bool]:
    print("[Audit 1 - Runtime Integrity]")
    results: list[bool] = []
    from app.services.language_grammar_lesson_runtime.orchestrator import (
        run_to_completion,
        to_view,
    )
    from app.services.language_grammar_lesson_runtime.types import GrammarRuntimeState

    bp = _sample_blueprint()
    session = run_to_completion(student_id=1, language_id=1, blueprint=bp, at="2026-01-01T00:00:00Z")
    view = to_view(session)
    results.append(_ok("reaches completed", session.state is GrammarRuntimeState.completed))
    results.append(_ok("all steps completed", len(session.completed_step_ids) == len(bp.steps)))
    results.append(_ok("no pending steps", session.pending_step_ids == ()))
    results.append(_ok("view exposes state", view.current_state is GrammarRuntimeState.completed))
    results.append(_ok("evidence requests emitted", len(view.expected_evidence_requests) >= 1))
    results.append(_ok("fingerprint bound", session.blueprint_fingerprint == bp.fingerprint))
    results.append(_ok("Audit 1 verdict", all(results)))
    print()
    return results


def audit_2_state_machine() -> list[bool]:
    print("[Audit 2 - State Machine]")
    results: list[bool] = []
    from app.services.language_grammar_lesson_runtime.dispatcher import GrammarRuntimeError
    from app.services.language_grammar_lesson_runtime.orchestrator import (
        cancel,
        complete_current_step,
        create_session,
        pause,
        prepare,
        resume,
        start,
    )
    from app.services.language_grammar_lesson_runtime.types import (
        ALLOWED_TRANSITIONS,
        GrammarRuntimeState,
    )

    bp = _sample_blueprint()
    at = "2026-01-01T00:00:00Z"
    s = create_session(student_id=1, language_id=1, blueprint=bp, at=at)
    results.append(_ok("created", s.state is GrammarRuntimeState.created))
    s = prepare(s, bp, at=at)
    results.append(_ok("ready", s.state is GrammarRuntimeState.ready))
    s = start(s, bp, at=at)
    results.append(_ok("running", s.state is GrammarRuntimeState.running))
    s = pause(s, at=at)
    results.append(_ok("paused", s.state is GrammarRuntimeState.paused))
    s = resume(s, bp, at=at)
    results.append(_ok("resumed running", s.state is GrammarRuntimeState.running))

    paused = pause(
        start(prepare(create_session(student_id=2, language_id=1, blueprint=bp, at=at), bp, at=at), bp, at=at),
        at=at,
    )
    try:
        complete_current_step(paused, bp, at=at)
        results.append(_ok("illegal complete from paused rejected", False))
    except GrammarRuntimeError:
        results.append(_ok("illegal complete from paused rejected", True))

    cancelled = cancel(
        start(prepare(create_session(student_id=3, language_id=1, blueprint=bp, at=at), bp, at=at), bp, at=at),
        at=at,
    )
    results.append(_ok("cancelled terminal", cancelled.state is GrammarRuntimeState.cancelled))
    results.append(
        _ok(
            "terminal has no outbound transitions",
            not ALLOWED_TRANSITIONS[GrammarRuntimeState.completed]
            and not ALLOWED_TRANSITIONS[GrammarRuntimeState.cancelled]
            and not ALLOWED_TRANSITIONS[GrammarRuntimeState.failed],
        )
    )
    results.append(_ok("Audit 2 verdict", all(results)))
    print()
    return results


def audit_3_replayability() -> list[bool]:
    print("[Audit 3 - Replayability]")
    results: list[bool] = []
    from app.services.language_grammar_lesson_runtime.orchestrator import run_to_completion
    from app.services.language_grammar_lesson_runtime.storage import (
        blueprint_from_runtime_bucket,
        bucket_from_session,
        session_from_bucket,
    )

    bp = _sample_blueprint()
    s1 = run_to_completion(student_id=1, language_id=1, blueprint=bp, at="2026-01-01T00:00:00Z")
    bucket = bucket_from_session(s1, blueprint=bp)
    s2 = session_from_bucket(bucket)
    bp2 = blueprint_from_runtime_bucket(bucket)
    results.append(_ok("session roundtrip state", s2 is not None and s2.state == s1.state))
    results.append(_ok("session roundtrip events", s2 is not None and s2.events == s1.events))
    results.append(_ok("blueprint persisted", bp2 is not None and bp2.fingerprint == bp.fingerprint))
    # Replay execution from restored blueprint
    s3 = run_to_completion(student_id=1, language_id=1, blueprint=bp2, at="2026-01-01T00:00:00Z")  # type: ignore[arg-type]
    results.append(
        _ok(
            "replay same completed steps",
            s3.completed_step_ids == s1.completed_step_ids,
        )
    )
    results.append(
        _ok(
            "replay same event types order",
            [e.event_type for e in s3.events] == [e.event_type for e in s1.events],
        )
    )
    results.append(_ok("Audit 3 verdict", all(results)))
    print()
    return results


def audit_4_executor_isolation() -> list[bool]:
    print("[Audit 4 - Executor Isolation]")
    results: list[bool] = []
    from app.services.language_grammar.enums import GrammarLessonStepKind
    from app.services.language_grammar_lesson_runtime.dispatcher import dispatch_step
    from app.services.language_grammar_lesson_runtime.executors import get_default_registry

    bp = _sample_blueprint()
    reg = get_default_registry()
    ids = set(reg.executor_ids())
    for name in (
        "ExplanationExecutor",
        "PracticeExecutor",
        "ReadingExecutor",
        "ListeningExecutor",
        "WritingExecutor",
        "SpeakingExecutor",
        "SummaryExecutor",
        "HomeworkExecutor",
        "ExitCheckExecutor",
    ):
        results.append(_ok(f"registry has {name}", name in ids))

    # Each step kind resolves uniquely
    for step in bp.steps:
        ex = reg.resolve(step.kind)
        result = dispatch_step(step, bp, registry=reg)
        results.append(_ok(f"dispatch {step.step_id}", result.success and result.executor_id == ex.executor_id))

    # Executors package must not import skill engines / claude
    exec_deps: set[str] = set()
    for py in (RUNTIME_PKG / "executors").glob("*.py"):
        exec_deps |= _parse_imports(py)
    for bad in (
        "claude_service",
        "language_speaking_lesson_runtime",
        "language_writing",
        "language_grammar_mastery",
    ):
        results.append(_ok(f"executors isolated from {bad}", bad not in exec_deps))

    results.append(
        _ok(
            "all step kinds registered",
            all(k in reg._by_kind for k in GrammarLessonStepKind),  # noqa: SLF001
        )
    )
    results.append(_ok("Audit 4 verdict", all(results)))
    print()
    return results


def audit_5_architecture() -> list[bool]:
    print("[Audit 5 - Architecture]")
    results: list[bool] = []
    forbidden_pkgs = {
        "language_grammar_progression",
        "language_grammar_mastery",
        "language_grammar_review",
        "language_grammar_integration",
        "language_grammar_educational_package",
        "language_grammar_evidence",
        "language_grammar_analytics",
        "claude_service",
    }
    # language_grammar_activity_provider is allowed (G3.3 interface only)
    deps: set[str] = set()
    for py in RUNTIME_PKG.rglob("*.py"):
        deps |= _parse_imports(py)

    for dep in sorted(forbidden_pkgs):
        results.append(_ok(f"runtime does not import {dep}", dep not in deps))

    # May depend on planner package for Blueprint contract only — not planner logic
    planner_logic = {
        "language_grammar_lesson_planner.builder",
        "language_grammar_lesson_planner.engine",
        "language_grammar_lesson_planner.service",
        "language_grammar_lesson_planner.policies",
    }
    for mod in sorted(planner_logic):
        results.append(_ok(f"runtime does not import {mod}", mod not in deps))

    results.append(
        _ok(
            "runtime may import planner types/serialization",
            "language_grammar_lesson_planner" in deps
            or "language_grammar_lesson_planner.types" in deps
            or "language_grammar_lesson_planner.serialization" in deps,
        )
    )

    from app.services.language_grammar.ownership import ALLOWED_PACKAGE_DEPENDENCIES

    allowed = ALLOWED_PACKAGE_DEPENDENCIES["language_grammar_lesson_runtime"]
    unexpected = {d for d in deps if d.startswith("language_grammar_")} - allowed - {
        "language_grammar_lesson_runtime"
    }
    # strip submodule suffixes for ownership check
    unexpected = {d.split(".")[0] for d in unexpected} - allowed - {"language_grammar_lesson_runtime"}
    unexpected -= {"language_grammar"}
    results.append(_ok("ownership DAG respected", not unexpected, str(sorted(unexpected))))
    results.append(_ok("Audit 5 verdict", all(results)))
    print()
    return results


def check_determinism_and_events() -> list[bool]:
    print("[Determinism & events]")
    results: list[bool] = []
    from app.services.language_grammar_lesson_runtime.orchestrator import run_to_completion
    from app.services.language_grammar_lesson_runtime.types import GrammarRuntimeEventType

    bp = _sample_blueprint()
    runs = [
        run_to_completion(student_id=1, language_id=1, blueprint=bp, at="2026-01-01T00:00:00Z")
        for _ in range(5)
    ]
    first = runs[0]
    identical = all(
        r.completed_step_ids == first.completed_step_ids
        and [e.event_type for e in r.events] == [e.event_type for e in first.events]
        and r.evidence_requests == first.evidence_requests
        for r in runs[1:]
    )
    results.append(_ok("deterministic full runs", identical))

    types = [e.event_type for e in first.events]
    results.append(_ok("LessonStarted present", GrammarRuntimeEventType.lesson_started in types))
    results.append(_ok("StepStarted present", GrammarRuntimeEventType.step_started in types))
    results.append(_ok("StepCompleted present", GrammarRuntimeEventType.step_completed in types))
    results.append(_ok("LessonCompleted present", GrammarRuntimeEventType.lesson_completed in types))
    results.append(
        _ok(
            "event sequences monotonic",
            all(
                first.events[i].sequence < first.events[i + 1].sequence
                for i in range(len(first.events) - 1)
            ),
        )
    )
    # LessonStarted before first StepCompleted
    results.append(
        _ok(
            "event ordering started before completed",
            types.index(GrammarRuntimeEventType.lesson_started)
            < types.index(GrammarRuntimeEventType.lesson_completed),
        )
    )

    with patch(
        "app.services.language_grammar_lesson_runtime.service.grammar_engine_enabled",
        return_value=False,
    ):
        from app.services.language_grammar_lesson_runtime.service import execute_blueprint

        view = execute_blueprint(student_id=1, language_id=1, blueprint=bp)
        results.append(_ok("ENABLED=false disables execution", view.session.enabled is False))

    print()
    return results


def main() -> int:
    print("Grammar G3.2 Runtime Orchestrator verification\n")
    all_results: list[bool] = []
    all_results.extend(audit_1_runtime_integrity())
    all_results.extend(audit_2_state_machine())
    all_results.extend(audit_3_replayability())
    all_results.extend(audit_4_executor_isolation())
    all_results.extend(audit_5_architecture())
    all_results.extend(check_determinism_and_events())

    passed = sum(1 for r in all_results if r)
    failed = sum(1 for r in all_results if not r)
    print(f"Summary: {passed} passed, {failed} failed, {len(all_results)} total")
    if failed:
        print("G3.2 VERDICT: NOT READY")
        return 1
    print("G3.2 VERDICT: READY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
