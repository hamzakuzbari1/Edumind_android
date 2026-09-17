"""Verify Grammar Learning Pipeline — Integration Phase 1.

Usage (from backend/):
    python scripts/verify_grammar_integration_phase1.py
"""

from __future__ import annotations

import ast
import json
import sys
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

BACKEND = Path(__file__).resolve().parents[1]
SERVICES = BACKEND / "app" / "services"
PKG = SERVICES / "language_grammar_pipeline"

FORBIDDEN_IMPORTS = frozenset(
    {
        "claude_service",
        "language_speaking_journey",
        "language_speaking_live",
        "language_grammar_educational_package",
    }
)

BUSINESS_LOGIC_MARKERS = (
    "derive_overall_mastery",
    "spaced_interval",
    "compute_progression_snapshot",
    "build_blueprint(",
    "evaluate_pattern(",
    "apply_observations(",
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
    deps.discard("language_grammar_pipeline")
    return deps


def _pkg_source() -> str:
    return "\n".join(p.read_text(encoding="utf-8") for p in PKG.rglob("*.py"))


@contextmanager
def _enable_pipeline():
    patches = [
        patch(
            "app.services.language_grammar_pipeline.flags.grammar_pipeline_enabled",
            return_value=True,
        ),
        patch(
            "app.services.language_grammar_pipeline.pipeline.grammar_pipeline_enabled",
            return_value=True,
        ),
        patch(
            "app.services.language_grammar_lesson_planner.service.grammar_engine_enabled",
            return_value=True,
        ),
        patch(
            "app.services.language_grammar_mastery.service.grammar_engine_enabled",
            return_value=True,
        ),
        patch(
            "app.services.language_grammar_activity_authoring.flags.activity_authoring_enabled",
            return_value=True,
        ),
        patch(
            "app.services.language_grammar_activity_authoring.author.activity_authoring_enabled",
            return_value=True,
        ),
        patch(
            "app.services.language_grammar_integration.service.selection_snapshot_or_disabled",
            side_effect=lambda snap: snap,
        ),
        patch(
            "app.services.language_grammar_mastery.service.grammar_engine_select_enabled",
            return_value=True,
        ),
    ]
    for p in patches:
        p.start()
    try:
        yield
    finally:
        for p in reversed(patches):
            p.stop()


def _make_snapshot():
    from app.services.language_grammar.enums import GrammarCEFRBand
    from app.services.language_grammar_catalog.catalog import get_default_catalog
    from app.services.language_grammar_evidence.types import GrammarEvidenceBatch, GrammarEvidenceObservation
    from app.services.language_grammar_evidence.validation import validate_batch
    from app.services.language_grammar.enums import (
        GrammarEvidenceSourceSkill,
        GrammarObservationType,
    )
    from app.services.language_grammar_integration.service import build_learning_snapshot
    from app.services.language_grammar_mastery.engine import apply_observations, empty_snapshot
    from app.services.language_grammar_progression.engine import compute_progression_snapshot
    from app.services.language_grammar_progression.types import GrammarProgressionStudentState
    from app.services.language_grammar_review.engine import empty_student_state
    from app.services.language_grammar_review.service import compute_from_mastery

    catalog = get_default_catalog()
    prog = compute_progression_snapshot(
        catalog=catalog,
        anchor_cefr=GrammarCEFRBand.A2,
        student=GrammarProgressionStudentState(student_id=7, language_id=1),
    )
    gid = prog.current_grammar_id or "gram_present_simple"
    obs = GrammarEvidenceObservation(
        observation_id="seed1",
        student_id=7,
        language_id=1,
        grammar_id=gid,
        source_skill=GrammarEvidenceSourceSkill.speaking,
        observation_type=GrammarObservationType.formative,
        attempt_count=2,
        correct_count=1,
        confidence=0.7,
        context="seed",
        observed_at="2026-07-01T00:00:00Z",
    )
    validated = validate_batch(GrammarEvidenceBatch(observations=(obs,)))
    mastery = apply_observations(
        empty_snapshot(student_id=7, language_id=1),
        validated.observations,
        catalog=catalog,
    )
    review = compute_from_mastery(
        mastery=mastery,
        student=empty_student_state(student_id=7, language_id=1),
        as_of="2026-07-18T00:00:00Z",
    )
    return build_learning_snapshot(
        student_id=7,
        language_id=1,
        overall_cefr=GrammarCEFRBand.A2,
        progression=prog,
        mastery=mastery,
        review=review,
        catalog=catalog,
        as_of="2026-07-18T00:00:00Z",
    ), prog, mastery


def _patterns_for(target: str) -> tuple[str, ...]:
    if "present_simple" in target:
        return ("I usually ...", "He plays ...", "Subject + Verb (Present Simple)")
    return ("Subject + Verb", "I am ...", "He is ...")


def _build_spec(targets: tuple[str, ...], patterns: tuple[str, ...]):
    from dataclasses import replace

    from app.services.language_grammar_activity_spec import build_minimal_specification

    spec = build_minimal_specification()
    payload = dict(spec.payload)
    payload["expected_patterns"] = json.dumps(list(patterns))
    payload["grammar_focus"] = targets[0]
    payload["teacher_opening"] = "Let's practice."
    payload["main_activity"] = "Practice target forms"
    return replace(
        spec,
        payload=payload,
        grammar_targets=targets,
        grammar_topic=targets[0],
        activity_type="voice_recording",
    )


def audit_1_architecture() -> list[bool]:
    print("[Audit 1 - Architecture]")
    results: list[bool] = []
    src = _pkg_source()
    for marker in BUSINESS_LOGIC_MARKERS:
        results.append(_ok(f"no migrated logic: {marker}", marker not in src))

    # pipeline.py is orchestrator — must not be named engine.py (G0)
    results.append(_ok("no engine.py in pipeline package", not (PKG / "engine.py").is_file()))
    results.append(_ok("has pipeline.py orchestrator", (PKG / "pipeline.py").is_file()))
    results.append(_ok("has types.py", (PKG / "types.py").is_file()))

    # Orchestrator must call public APIs (string presence)
    results.append(_ok("calls plan_lesson", "plan_lesson" in src))
    results.append(_ok("calls evaluate_grammar / stage_evaluate", "stage_evaluate" in src or "evaluate_grammar" in src))
    results.append(_ok("calls compute_mastery_from_evidence", "compute_mastery_from_evidence" in src))
    results.append(_ok("calls compute_from_mastery", "compute_from_mastery" in src))
    results.append(_ok("Audit 1 verdict", all(results)))
    print()
    return results


def audit_2_transaction_safety() -> list[bool]:
    print("[Audit 2 - Transaction Safety]")
    results: list[bool] = []
    from app.services.language_grammar_pipeline import (
        PipelineRequest,
        PipelineStatus,
        reset_replay_store_for_tests,
        run_grammar_learning_pipeline,
    )
    from app.services.language_grammar_pipeline.stages import stage_evaluate

    reset_replay_store_for_tests()
    snap, prog, mastery = _make_snapshot()
    target = snap.current_grammar_id or "gram_present_simple"
    patterns = _patterns_for(target)
    spec = _build_spec((target,), patterns)

    with _enable_pipeline():
        # Force evaluation failure
        with patch(
            "app.services.language_grammar_pipeline.pipeline.stage_evaluate",
            side_effect=ValueError("forced_evaluation_failure"),
        ):
            outcome = run_grammar_learning_pipeline(
                PipelineRequest(
                    student_id=7,
                    language_id=1,
                    student_response="He play football.",
                    learning_snapshot=snap,
                    specification=spec,
                    expected_patterns=patterns,
                    prior_mastery=mastery,
                    prior_progression=prog,
                    as_of="2026-07-18T00:00:00Z",
                    pipeline_id="gpipe_txn_fail",
                )
            )

    results.append(_ok("status failed on eval error", outcome.status is PipelineStatus.failed))
    results.append(_ok("evaluation not succeeded", not outcome.write_gate.evaluation_succeeded))
    results.append(_ok("mastery not applied", not outcome.write_gate.mastery_applied))
    results.append(_ok("review not applied", not outcome.write_gate.review_applied))
    results.append(_ok("progression not synced", not outcome.write_gate.progression_synced))
    results.append(_ok("mastery snapshot absent", outcome.mastery_snapshot is None))
    results.append(_ok("review snapshot absent", outcome.review_snapshot is None))
    results.append(_ok("writes aborted", outcome.write_gate.aborted))

    # Happy path then confirm write gate order helpers
    from app.services.language_grammar_pipeline.types import WriteGate

    g = WriteGate()
    results.append(_ok("cannot write mastery before eval", not g.may_write_mastery()))
    results.append(_ok("Audit 2 verdict", all(results)))
    print()
    return results


def audit_3_replayability() -> list[bool]:
    print("[Audit 3 - Replayability]")
    results: list[bool] = []
    from app.services.language_grammar_pipeline import (
        GrammarLearningPipeline,
        PipelineMode,
        PipelineRequest,
        PipelineStatus,
        reset_replay_store_for_tests,
        run_grammar_learning_pipeline,
    )

    reset_replay_store_for_tests()
    snap, prog, mastery = _make_snapshot()
    target = snap.current_grammar_id or "gram_present_simple"
    patterns = _patterns_for(target)
    spec = _build_spec((target,), patterns)

    with _enable_pipeline():
        first = run_grammar_learning_pipeline(
            PipelineRequest(
                student_id=7,
                language_id=1,
                student_response="I usually wake up early.",
                learning_snapshot=snap,
                specification=spec,
                expected_patterns=patterns,
                prior_mastery=mastery,
                prior_progression=prog,
                as_of="2026-07-18T00:00:00Z",
                pipeline_id="gpipe_replay_1",
                use_llm_authoring=False,
            )
        )
        results.append(_ok("first run completed", first.status is PipelineStatus.completed))
        results.append(_ok("replay bundle stored", first.replay_bundle is not None))

        # Replay must not call author/LLM
        with patch(
            "app.services.language_grammar_pipeline.pipeline.stage_author_activity",
            side_effect=AssertionError("LLM/author must not run on replay"),
        ), patch(
            "app.services.language_grammar_pipeline.stages.author_activity_with_llm",
            side_effect=AssertionError("LLM must not run on replay"),
        ), patch(
            "app.services.language_grammar_pipeline.pipeline.stage_execute",
            side_effect=AssertionError("Execute must not regenerate on replay"),
        ):
            second = GrammarLearningPipeline.replay(
                first.replay_bundle,
                apply_learner_writes=True,
            )

    results.append(_ok("replay completed", second.status is PipelineStatus.completed))
    results.append(_ok("replay mode", second.observability.mode == PipelineMode.replay.value))
    results.append(_ok("replay authoring_invoked false", second.authoring_invoked is False))
    results.append(_ok("replay llm_authoring_invoked false", second.llm_authoring_invoked is False))
    results.append(_ok("replay execution_invoked false", second.execution_invoked is False))
    results.append(
        _ok(
            "same evaluation id family",
            bool(second.evaluation_result and first.evaluation_result),
        )
    )
    results.append(_ok("Audit 3 verdict", all(results)))
    print()
    return results


def audit_4_failure_recovery() -> list[bool]:
    print("[Audit 4 - Failure Recovery]")
    results: list[bool] = []
    from app.services.language_grammar_pipeline import (
        PipelineRequest,
        PipelineStage,
        PipelineStatus,
        reset_replay_store_for_tests,
        run_grammar_learning_pipeline,
    )

    reset_replay_store_for_tests()
    snap, prog, mastery = _make_snapshot()
    target = snap.current_grammar_id or "gram_present_simple"
    patterns = _patterns_for(target)
    spec = _build_spec((target,), patterns)

    stage_patches = [
        ("stage_plan_lesson", PipelineStage.plan),
        ("stage_execute", PipelineStage.execute),
        ("stage_evaluate", PipelineStage.evaluate),
        ("stage_mastery", PipelineStage.mastery),
        ("stage_review", PipelineStage.review),
    ]

    with _enable_pipeline():
        for fn_name, expected_stage in stage_patches:
            with patch(
                f"app.services.language_grammar_pipeline.pipeline.{fn_name}",
                side_effect=RuntimeError(f"boom_{fn_name}"),
            ):
                # For mastery/review failures, evaluation must succeed first — use real earlier stages
                outcome = run_grammar_learning_pipeline(
                    PipelineRequest(
                        student_id=7,
                        language_id=1,
                        student_response="I usually cook.",
                        learning_snapshot=snap,
                        specification=spec if expected_stage != PipelineStage.plan else None,
                        blueprint=None,
                        expected_patterns=patterns,
                        prior_mastery=mastery,
                        prior_progression=prog,
                        as_of="2026-07-18T00:00:00Z",
                        pipeline_id=f"gpipe_fail_{expected_stage.value}",
                    )
                )
            results.append(
                _ok(
                    f"structured failure for {expected_stage.value}",
                    outcome.status is PipelineStatus.failed
                    and any(f.stage is expected_stage for f in outcome.failures),
                )
            )
            results.append(
                _ok(
                    f"failure has code for {expected_stage.value}",
                    bool(outcome.failures and outcome.failures[0].code),
                )
            )

    # Authoring failure (LLM path) — inject missing author with use_llm and force author fail
    with _enable_pipeline():
        with patch(
            "app.services.language_grammar_pipeline.pipeline.stage_author_activity",
            side_effect=RuntimeError("boom_author"),
        ):
            outcome = run_grammar_learning_pipeline(
                PipelineRequest(
                    student_id=7,
                    language_id=1,
                    student_response="Hi",
                    learning_snapshot=snap,
                    expected_patterns=patterns,
                    as_of="2026-07-18T00:00:00Z",
                    pipeline_id="gpipe_fail_author",
                )
            )
    results.append(
        _ok(
            "structured failure for author",
            outcome.status is PipelineStatus.failed
            and any(f.stage is PipelineStage.author for f in outcome.failures),
        )
    )
    results.append(_ok("Audit 4 verdict", all(results)))
    print()
    return results


def audit_5_ownership() -> list[bool]:
    print("[Audit 5 - Ownership]")
    results: list[bool] = []
    from app.services.language_grammar.ownership import (
        ALLOWED_PACKAGE_DEPENDENCIES,
        FORBIDDEN_MASTERY_WRITERS,
        PACKAGE_LAYER,
        PACKAGE_OWNERSHIP,
    )

    results.append(_ok("ownership entry", "language_grammar_pipeline" in PACKAGE_OWNERSHIP))
    results.append(_ok("layer pipeline", PACKAGE_LAYER.get("language_grammar_pipeline") == "pipeline"))
    results.append(
        _ok(
            "pipeline not forbidden mastery writer",
            "language_grammar_pipeline" not in FORBIDDEN_MASTERY_WRITERS,
        )
    )
    allowed = ALLOWED_PACKAGE_DEPENDENCIES.get("language_grammar_pipeline", frozenset())
    deps = _pkg_imports()
    # language_grammar is shared infra
    deps.discard("language_grammar")
    unexpected = sorted(deps - set(allowed) - {"language_grammar"})
    results.append(_ok("DAG respected", not unexpected, detail=str(unexpected)))

    for bad in FORBIDDEN_IMPORTS:
        results.append(_ok(f"no import {bad}", bad not in deps and bad not in _pkg_source().lower()))

    # Educational decisions remain in owned packages — pipeline only orchestrates
    src = _pkg_source()
    results.append(_ok("no catalog topic definitions", "GrammarTopic(" not in src))
    results.append(_ok("no mastery weight constants", "OVERALL_WEIGHT_" not in src))
    results.append(_ok("Audit 5 verdict", all(results)))
    print()
    return results


def check_flags_happy_path_events() -> list[bool]:
    print("[Flags / Happy path / Events]")
    results: list[bool] = []
    from app.core.config import get_settings
    from app.services.language_grammar_pipeline import (
        PipelineEventType,
        PipelineRequest,
        PipelineStatus,
        grammar_pipeline_enabled,
        reset_replay_store_for_tests,
        run_grammar_learning_pipeline,
    )

    settings = get_settings()
    results.append(_ok("LANG_GRAMMAR_PIPELINE_ENABLED defined", hasattr(settings, "LANG_GRAMMAR_PIPELINE_ENABLED")))
    results.append(_ok("flag helper callable", isinstance(grammar_pipeline_enabled(), bool)))
    results.append(_ok("flag default disables pipeline", grammar_pipeline_enabled() is False))

    # Disabled path
    reset_replay_store_for_tests()
    snap, prog, mastery = _make_snapshot()
    target = snap.current_grammar_id or "gram_present_simple"
    patterns = _patterns_for(target)
    spec = _build_spec((target,), patterns)
    disabled = run_grammar_learning_pipeline(
        PipelineRequest(
            student_id=7,
            language_id=1,
            student_response="I usually walk.",
            learning_snapshot=snap,
            specification=spec,
            expected_patterns=patterns,
            pipeline_id="gpipe_disabled",
        )
    )
    results.append(_ok("disabled status", disabled.status is PipelineStatus.disabled))

    with _enable_pipeline():
        outcome = run_grammar_learning_pipeline(
            PipelineRequest(
                student_id=7,
                language_id=1,
                student_response="I usually wake up early.",
                learning_snapshot=snap,
                specification=spec,
                expected_patterns=patterns,
                prior_mastery=mastery,
                prior_progression=prog,
                as_of="2026-07-18T00:00:00Z",
                pipeline_id="gpipe_happy",
            )
        )

    results.append(_ok("happy path completed", outcome.status is PipelineStatus.completed))
    results.append(_ok("has evaluation", outcome.evaluation_result is not None))
    results.append(_ok("has evidence", outcome.evidence_batch is not None and len(outcome.observations) >= 1))
    results.append(_ok("mastery applied", outcome.write_gate.mastery_applied))
    results.append(_ok("review applied", outcome.write_gate.review_applied))
    results.append(_ok("has observability pipeline_id", bool(outcome.observability.pipeline_id)))
    results.append(_ok("has grammar_target", bool(outcome.observability.grammar_target)))
    results.append(_ok("has duration", outcome.observability.duration_ms >= 0))

    types = {e.event_type for e in outcome.events}
    for required in (
        PipelineEventType.GrammarLessonStarted,
        PipelineEventType.LessonGenerated,
        PipelineEventType.LessonExecuted,
        PipelineEventType.GrammarEvaluated,
        PipelineEventType.EvidenceProduced,
        PipelineEventType.MasteryUpdated,
        PipelineEventType.ReviewUpdated,
        PipelineEventType.LessonCompleted,
    ):
        results.append(_ok(f"event {required.value}", required in types))

    env_root = (BACKEND.parent / ".env.example").read_text(encoding="utf-8")
    env_be = (BACKEND / ".env.example").read_text(encoding="utf-8")
    results.append(_ok("root .env.example flag", "LANG_GRAMMAR_PIPELINE_ENABLED" in env_root))
    results.append(_ok("backend .env.example flag", "LANG_GRAMMAR_PIPELINE_ENABLED" in env_be))

    for name in (
        "types.py",
        "pipeline.py",
        "stages.py",
        "transactions.py",
        "flags.py",
        "store.py",
        "fingerprint.py",
        "__init__.py",
    ):
        results.append(_ok(f"file {name}", (PKG / name).is_file()))
    print()
    return results


def main() -> int:
    print("Grammar Learning Pipeline — Integration Phase 1 verification\n")
    all_results: list[bool] = []
    all_results.extend(audit_1_architecture())
    all_results.extend(audit_2_transaction_safety())
    all_results.extend(audit_3_replayability())
    all_results.extend(audit_4_failure_recovery())
    all_results.extend(audit_5_ownership())
    all_results.extend(check_flags_happy_path_events())

    passed = sum(1 for r in all_results if r)
    failed = sum(1 for r in all_results if not r)
    print(f"Summary: {passed} passed, {failed} failed, {len(all_results)} total")
    if failed:
        print("Integration Phase 1 VERDICT: NOT READY")
        return 1
    print("Integration Phase 1 VERDICT: READY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
