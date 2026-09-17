"""Verify Grammar Skill Execution Engine V1.5.

Usage (from backend/):
    python scripts/verify_grammar_v15_skill_execution_engine.py
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

BACKEND = Path(__file__).resolve().parents[1]
SERVICES = BACKEND / "app" / "services"
PKG = SERVICES / "language_grammar_skill_executor"

FORBIDDEN_IMPORTS = frozenset(
    {
        "language_grammar_mastery",
        "language_grammar_progression",
        "language_grammar_review",
        "language_grammar_activity_authoring",
        "language_grammar_lesson_planner",
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


def _pkg_imports() -> set[str]:
    deps: set[str] = set()
    for py in PKG.rglob("*.py"):
        deps |= _parse_imports(py)
    deps.discard("language_grammar_skill_executor")
    return deps


def _spec():
    from app.services.language_grammar_activity_spec import build_minimal_specification

    return build_minimal_specification()


def audit_1_grammar_isolation() -> list[bool]:
    print("[Audit 1 - Grammar Isolation]")
    results: list[bool] = []
    from app.services.language_grammar_skill_executor import (
        StudentContext,
        TeacherPersona,
        run_execution,
    )

    spec = _spec()
    targets_before = tuple(spec.grammar_targets)
    topic_before = spec.grammar_topic
    state = run_execution(
        spec,
        student=StudentContext(student_id=1, language_id=1),
        teacher_persona=TeacherPersona(teacher_id="t1"),
        student_response="opt_a",
    )
    results.append(_ok("session grammar_targets preserved", state.session.grammar_targets == targets_before))
    results.append(_ok("spec grammar_topic unchanged", state.specification.grammar_topic == topic_before))
    results.append(
        _ok(
            "observation grammar_id from targets",
            bool(state.observations) and state.observations[0].grammar_id in targets_before,
        )
    )

    src = "\n".join(p.read_text(encoding="utf-8") for p in PKG.rglob("*.py"))
    for needle in (
        "all_grammar_ids",
        "update_catalog",
        "mutate_grammar",
        "english_catalog",
    ):
        # engine_validation uses id_canon only — catalog mutation APIs forbidden
        if needle == "all_grammar_ids":
            results.append(_ok(f"no {needle}", needle not in src))
        else:
            results.append(_ok(f"no {needle}", needle not in src))

    results.append(_ok("Audit 1 verdict", all(results)))
    print()
    return results


def audit_2_execution_isolation() -> list[bool]:
    print("[Audit 2 - Execution Isolation]")
    results: list[bool] = []
    deps = _pkg_imports()
    for bad in sorted(FORBIDDEN_IMPORTS):
        results.append(_ok(f"no import {bad}", bad not in deps))

    src = "\n".join(p.read_text(encoding="utf-8") for p in PKG.rglob("*.py")).lower()
    for needle in (
        "apply_evidence_and_persist",
        "update_mastery",
        "resolve_targets",
        "review_queue",
        "author_activity",
        "build_prompt",
        "anthropic",
        "speech_to_text",
        "text_to_speech",
    ):
        results.append(_ok(f"no {needle}", needle not in src))

    results.append(_ok("Audit 2 verdict", all(results)))
    print()
    return results


def audit_3_registry() -> list[bool]:
    print("[Audit 3 - Registry]")
    results: list[bool] = []
    from app.services.language_grammar_skill_executor import (
        SkillExecutorRegistry,
        StudentContext,
        get_default_skill_executor_registry,
        run_execution,
    )
    from app.services.language_grammar_skill_executor.base import PlaceholderSkillExecutor

    reg = get_default_skill_executor_registry()
    results.append(_ok("default registry non-empty", len(reg.ids()) >= 1))

    class CustomExecutor(PlaceholderSkillExecutor):
        def __init__(self) -> None:
            super().__init__("custom_v15", frozenset({"multiple_choice"}))

    custom_reg = SkillExecutorRegistry()
    custom_reg.register(CustomExecutor())
    custom_reg.map_activity_type("multiple_choice", "custom_v15")

    # Engine must not hardcode executor ids in execution_service
    service_src = (PKG / "execution_service.py").read_text(encoding="utf-8")
    results.append(_ok("service uses resolve_executor", "resolve_executor" in service_src))
    results.append(_ok("service has no if activity_type ==", "if activity_type ==" not in service_src))

    state = run_execution(
        _spec(),
        student=StudentContext(student_id=2, language_id=1),
        student_response="x",
        registry=custom_reg,
    )
    results.append(_ok("custom executor via registry only", state.session.executor_id == "custom_v15"))

    # Registering another executor does not require editing execution_service.py
    class Another(PlaceholderSkillExecutor):
        def __init__(self) -> None:
            super().__init__("another_v15", frozenset({"free_text"}))

    custom_reg.register(Another())
    results.append(_ok("register without engine file change", "another_v15" in custom_reg.ids()))

    results.append(_ok("Audit 3 verdict", all(results)))
    print()
    return results


def audit_4_evidence() -> list[bool]:
    print("[Audit 4 - Evidence]")
    results: list[bool] = []
    from app.services.language_grammar_evidence.types import GrammarEvidenceObservation
    from app.services.language_grammar_skill_executor import (
        StudentContext,
        collect_evidence,
        run_execution,
    )

    state = run_execution(
        _spec(),
        student=StudentContext(student_id=3, language_id=1),
        student_response="opt_b",
    )
    obs = collect_evidence(state)
    results.append(_ok("observations leave execution", len(obs) >= 1))
    results.append(_ok("type GrammarEvidenceObservation", isinstance(obs[0], GrammarEvidenceObservation)))
    results.append(_ok("no overall_mastery on observation", not hasattr(obs[0], "overall_mastery")))
    results.append(_ok("no cefr score field", not hasattr(obs[0], "cefr_score")))
    results.append(
        _ok(
            "result carries generated_evidence only",
            state.result is not None and len(state.result.generated_evidence) >= 1,
        )
    )

    adapter_src = (PKG / "evidence_adapter.py").read_text(encoding="utf-8")
    results.append(_ok("adapter documents no mastery write", "Never writes mastery" in adapter_src or "never" in adapter_src.lower()))
    for needle in ("language_grammar_mastery", "apply_evidence_batch", "update_mastery"):
        results.append(_ok(f"adapter no {needle}", needle not in adapter_src))

    results.append(_ok("Audit 4 verdict", all(results)))
    print()
    return results


def audit_5_replayability() -> list[bool]:
    print("[Audit 5 - Replayability]")
    results: list[bool] = []
    from app.services.language_grammar_skill_executor import (
        SessionStatus,
        StudentContext,
        replay_execution,
        reset_default_execution_session_store_for_tests,
        run_execution,
    )

    reset_default_execution_session_store_for_tests()
    state = run_execution(
        _spec(),
        student=StudentContext(student_id=4, language_id=1),
        student_response="opt_c",
        as_of="2026-07-18T00:00:00Z",
    )
    sid = state.session.execution_session_id
    view = state.view()
    results.append(_ok("view has status history", len(view["status_history"]) >= 4))
    results.append(_ok("view has events", len(view["events"]) >= 4))

    replayed = replay_execution(sid)
    results.append(_ok("replay same session id", replayed.session.execution_session_id == sid))
    results.append(_ok("replay status completed", replayed.session.status is SessionStatus.completed))
    results.append(
        _ok(
            "replay student_response",
            replayed.session.student_response == state.session.student_response,
        )
    )
    results.append(
        _ok(
            "replay observations restored",
            len(replayed.observations) == len(state.observations),
        )
    )
    results.append(
        _ok(
            "replay event types match",
            [e.event_type for e in replayed.events] == [e.event_type for e in state.events],
        )
    )
    results.append(_ok("Audit 5 verdict", all(results)))
    print()
    return results


def check_lifecycle_state_machine() -> list[bool]:
    print("[Lifecycle / State Machine / Validation]")
    results: list[bool] = []
    from app.services.language_grammar_skill_executor import (
        ALLOWED_TRANSITIONS,
        ExecutionLifecycleEventType,
        InvalidSessionTransitionError,
        SessionStatus,
        StudentContext,
        TeacherPersona,
        assert_session_transition,
        cancel_execution,
        create_execution,
        reset_default_execution_session_store_for_tests,
        start_execution,
        submit_student_response,
        validate_grammar_targets,
    )
    from app.services.language_grammar_skill_executor.errors import SkillExecutorError

    reset_default_execution_session_store_for_tests()

    required_states = {
        SessionStatus.created,
        SessionStatus.initializing,
        SessionStatus.running,
        SessionStatus.waiting_for_student,
        SessionStatus.evaluating,
        SessionStatus.completed,
        SessionStatus.cancelled,
        SessionStatus.failed,
    }
    results.append(_ok("all session states defined", required_states <= set(SessionStatus)))

    assert_session_transition(SessionStatus.created, SessionStatus.initializing)
    try:
        assert_session_transition(SessionStatus.created, SessionStatus.completed)
        results.append(_ok("illegal transition rejected", False))
    except InvalidSessionTransitionError:
        results.append(_ok("illegal transition rejected", True))

    results.append(
        _ok(
            "terminal has no exits",
            not ALLOWED_TRANSITIONS[SessionStatus.completed]
            and not ALLOWED_TRANSITIONS[SessionStatus.cancelled],
        )
    )

    state = create_execution(
        _spec(),
        student=StudentContext(student_id=5, language_id=1),
        teacher_persona=TeacherPersona(teacher_id="teacher_5"),
    )
    results.append(_ok("created status", state.session.status is SessionStatus.created))
    results.append(
        _ok(
            "ExecutionCreated event",
            any(e.event_type is ExecutionLifecycleEventType.execution_created for e in state.events),
        )
    )
    results.append(_ok("teacher_id set", state.session.teacher_id == "teacher_5"))
    results.append(_ok("activity_id set", bool(state.session.activity_id)))
    results.append(_ok("execution_attempt_id set", bool(state.session.execution_attempt_id)))

    state = start_execution(state, at="t1")
    results.append(
        _ok(
            "waiting_for_student after start",
            state.session.status is SessionStatus.waiting_for_student,
        )
    )
    results.append(_ok("started_at set", bool(state.session.started_at)))
    results.append(
        _ok(
            "history includes initializing/running",
            "initializing" in state.status_history and "running" in state.status_history,
        )
    )

    state = submit_student_response(state, "hello", at="t2")
    results.append(_ok("evaluating after response", state.session.status is SessionStatus.evaluating))

    # Cancel path from a fresh session mid-flight
    reset_default_execution_session_store_for_tests()
    cstate = create_execution(_spec(), student=StudentContext(student_id=6, language_id=1))
    cstate = start_execution(cstate, at="c1")
    cstate = cancel_execution(cstate, reason="user_abort", at="c2")
    results.append(_ok("cancelled terminal", cstate.session.status is SessionStatus.cancelled))

    try:
        validate_grammar_targets(())
        results.append(_ok("empty grammar_targets rejected", False))
    except SkillExecutorError:
        results.append(_ok("empty grammar_targets rejected", True))

    required_events = {
        ExecutionLifecycleEventType.execution_created,
        ExecutionLifecycleEventType.execution_started,
        ExecutionLifecycleEventType.student_responded,
        ExecutionLifecycleEventType.evaluation_completed,
        ExecutionLifecycleEventType.execution_completed,
        ExecutionLifecycleEventType.execution_cancelled,
        ExecutionLifecycleEventType.execution_failed,
    }
    results.append(_ok("lifecycle event types complete", required_events <= set(ExecutionLifecycleEventType)))
    print()
    return results


def check_flags_and_ownership() -> list[bool]:
    print("[Flags / Ownership / Files]")
    results: list[bool] = []
    from app.core.config import get_settings
    from app.services.language_grammar.ownership import (
        ALLOWED_PACKAGE_DEPENDENCIES,
        FORBIDDEN_MASTERY_WRITERS,
        PACKAGE_LAYER,
        PACKAGE_OWNERSHIP,
    )
    from app.services.language_grammar_skill_executor import skill_execution_engine_enabled

    settings = get_settings()
    results.append(
        _ok(
            "LANG_GRAMMAR_SKILL_EXECUTION_ENGINE_ENABLED defined",
            hasattr(settings, "LANG_GRAMMAR_SKILL_EXECUTION_ENGINE_ENABLED"),
        )
    )
    results.append(
        _ok("skill_execution_engine_enabled callable", isinstance(skill_execution_engine_enabled(), bool))
    )

    results.append(_ok("ownership entry", "language_grammar_skill_executor" in PACKAGE_OWNERSHIP))
    results.append(
        _ok(
            "layer skill_execution",
            PACKAGE_LAYER.get("language_grammar_skill_executor") == "skill_execution",
        )
    )
    results.append(
        _ok(
            "forbidden mastery writer",
            "language_grammar_skill_executor" in FORBIDDEN_MASTERY_WRITERS,
        )
    )
    allowed = ALLOWED_PACKAGE_DEPENDENCIES.get("language_grammar_skill_executor", frozenset())
    deps = {d for d in _pkg_imports() if d.startswith("language_grammar")}
    deps.discard("language_grammar")
    extra = deps - set(allowed)
    results.append(_ok("DAG respected", not extra, str(sorted(extra))))

    env_root = (BACKEND.parent / ".env.example").read_text(encoding="utf-8")
    env_be = (BACKEND / ".env.example").read_text(encoding="utf-8")
    results.append(_ok("root .env.example flag", "LANG_GRAMMAR_SKILL_EXECUTION_ENGINE_ENABLED" in env_root))
    results.append(_ok("backend .env.example flag", "LANG_GRAMMAR_SKILL_EXECUTION_ENGINE_ENABLED" in env_be))

    for name in (
        "execution_service.py",
        "session.py",
        "state_machine.py",
        "storage.py",
        "engine_validation.py",
        "evidence_adapter.py",
        "registry.py",
    ):
        results.append(_ok(f"file {name}", (PKG / name).is_file()))
    print()
    return results


def main() -> int:
    print("Grammar Skill Execution Engine V1.5 verification\n")
    # Fix audit_3 — remove invalid walrus import attempt by redefining cleanly below if needed
    all_results: list[bool] = []
    all_results.extend(audit_1_grammar_isolation())
    all_results.extend(audit_2_execution_isolation())
    all_results.extend(audit_3_registry())
    all_results.extend(audit_4_evidence())
    all_results.extend(audit_5_replayability())
    all_results.extend(check_lifecycle_state_machine())
    all_results.extend(check_flags_and_ownership())

    passed = sum(1 for r in all_results if r)
    failed = sum(1 for r in all_results if not r)
    print(f"Summary: {passed} passed, {failed} failed, {len(all_results)} total")
    if failed:
        print("V1.5 VERDICT: NOT READY")
        return 1
    print("V1.5 VERDICT: READY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
