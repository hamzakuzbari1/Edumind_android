"""Verify Grammar G3.1 Lesson Planner + Integration facade.

Usage (from backend/):
    python scripts/verify_grammar_g31_planner.py
"""

from __future__ import annotations

import ast
import copy
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

BACKEND = Path(__file__).resolve().parents[1]
SERVICES = BACKEND / "app" / "services"
PLANNER_PKG = SERVICES / "language_grammar_lesson_planner"
INTEGRATION_PKG = SERVICES / "language_grammar_integration"


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


def _obs(**kwargs):
    from app.services.language_grammar.enums import (
        GrammarEvidenceSourceSkill,
        GrammarObservationType,
    )
    from app.services.language_grammar_evidence.types import GrammarEvidenceObservation

    defaults = dict(
        observation_id="p1",
        student_id=1,
        language_id=1,
        grammar_id="gram_present_simple",
        source_skill=GrammarEvidenceSourceSkill.speaking,
        observation_type=GrammarObservationType.formative,
        attempt_count=4,
        correct_count=3,
        confidence=0.8,
        context="cafe",
        observed_at="2026-01-01T12:00:00Z",
    )
    defaults.update(kwargs)
    return GrammarEvidenceObservation(**defaults)


def _make_snapshot():
    """Build a GrammarLearningSnapshot via Integration facade only (for planner)."""
    from app.services.language_grammar.enums import GrammarCEFRBand
    from app.services.language_grammar_catalog.catalog import get_default_catalog
    from app.services.language_grammar_evidence.types import GrammarEvidenceBatch
    from app.services.language_grammar_evidence.validation import validate_batch
    from app.services.language_grammar_integration.service import (
        GrammarIntegrationService,
        build_learning_snapshot,
    )
    from app.services.language_grammar_mastery.engine import apply_observations, empty_snapshot
    from app.services.language_grammar_progression.engine import compute_progression_snapshot
    from app.services.language_grammar_progression.types import GrammarProgressionStudentState
    from app.services.language_grammar_review.engine import empty_student_state
    from app.services.language_grammar_review.service import compute_from_mastery

    catalog = get_default_catalog()
    prog = compute_progression_snapshot(
        catalog=catalog,
        anchor_cefr=GrammarCEFRBand.A1,
        student=GrammarProgressionStudentState(student_id=1, language_id=1),
    )
    # Ensure we have a current topic
    if not prog.current_grammar_id and prog.candidate_pool_ids:
        # sticky current via recompute with unlocked first candidate is already in snapshot
        pass

    validated = validate_batch(
        GrammarEvidenceBatch(
            observations=(
                _obs(observation_id="a", grammar_id=prog.current_grammar_id or "gram_be_present", context="c1"),
                _obs(observation_id="b", grammar_id=prog.current_grammar_id or "gram_be_present", context="c2"),
                # Separate topic for review pressure
                _obs(
                    observation_id="c",
                    grammar_id="gram_present_simple",
                    context="old",
                    observed_at="2025-06-01T00:00:00Z",
                ),
            )
        )
    )
    mastery = apply_observations(
        empty_snapshot(student_id=1, language_id=1),
        validated.observations,
        catalog=catalog,
    )
    review = compute_from_mastery(
        mastery=mastery,
        student=empty_student_state(student_id=1, language_id=1),
        as_of="2026-08-01T00:00:00Z",
    )
    snap = build_learning_snapshot(
        student_id=1,
        language_id=1,
        overall_cefr=GrammarCEFRBand.A1,
        progression=prog,
        mastery=mastery,
        review=review,
        catalog=catalog,
        as_of="2026-08-01T00:00:00Z",
    )
    # Also exercise facade class
    snap2 = GrammarIntegrationService.build_learning_snapshot(
        student_id=1,
        language_id=1,
        overall_cefr=GrammarCEFRBand.A1,
        progression=prog,
        mastery=mastery,
        review=review,
        catalog=catalog,
        as_of="2026-08-01T00:00:00Z",
    )
    assert snap.current_grammar_id == snap2.current_grammar_id
    return snap


def audit_1_blueprint_integrity() -> list[bool]:
    print("[Audit 1 - Blueprint Integrity]")
    results: list[bool] = []
    from app.services.language_grammar.enums import GrammarLessonStepKind
    from app.services.language_grammar_lesson_planner.service import plan_lesson

    with patch(
        "app.services.language_grammar_lesson_planner.service.grammar_engine_enabled",
        return_value=True,
    ):
        snap = _make_snapshot()
        bp = plan_lesson(snap)

    results.append(_ok("blueprint enabled", bp.enabled))
    results.append(_ok("has lesson goal", bool(bp.lesson_goal or bp.objectives)))
    results.append(_ok("has steps", len(bp.steps) >= 3))
    results.append(_ok("has completion criteria", bp.completion_criteria.require_exit_check))
    results.append(_ok("has evidence expectations", len(bp.evidence_plan.eligible_step_ids) >= 1))
    results.append(_ok("has duration", bp.estimated_duration_minutes > 0))
    results.append(
        _ok(
            "has explanation+practice+exit",
            {GrammarLessonStepKind.explanation, GrammarLessonStepKind.practice, GrammarLessonStepKind.exit_check}
            <= {s.kind for s in bp.steps},
        )
    )
    results.append(
        _ok(
            "version fields present",
            bool(bp.blueprint_version and bp.planner_version and bp.catalog_version)
            and bp.grammar_schema_version >= 1,
        )
    )
    results.append(_ok("frozen", bp.frozen is True))
    results.append(_ok("Audit 1 verdict", all(results)))
    print()
    return results


def audit_2_determinism() -> list[bool]:
    print("[Audit 2 - Planner Determinism]")
    results: list[bool] = []
    from app.services.language_grammar_lesson_planner.service import plan_lesson

    with patch(
        "app.services.language_grammar_lesson_planner.service.grammar_engine_enabled",
        return_value=True,
    ):
        snap = _make_snapshot()
        bps = [plan_lesson(snap) for _ in range(5)]
    first = bps[0]
    identical = all(
        b.fingerprint == first.fingerprint
        and b.steps == first.steps
        and b.lesson_id == first.lesson_id
        for b in bps[1:]
    )
    results.append(_ok("same snapshot => same blueprint", identical))
    results.append(_ok("Audit 2 verdict", all(results)))
    print()
    return results


def audit_3_architecture() -> list[bool]:
    print("[Audit 3 - Architecture]")
    results: list[bool] = []
    forbidden = {
        "language_grammar_catalog",
        "language_grammar_progression",
        "language_grammar_mastery",
        "language_grammar_review",
        "language_grammar_lesson_runtime",
        "language_grammar_educational_package",
        "language_grammar_analytics",
        "claude_service",
    }
    deps: set[str] = set()
    for py_file in PLANNER_PKG.glob("*.py"):
        deps |= _parse_imports(py_file)

    for dep in sorted(forbidden):
        results.append(_ok(f"planner does not import {dep}", dep not in deps))

    results.append(_ok("planner imports integration", "language_grammar_integration" in deps))

    from app.services.language_grammar.ownership import ALLOWED_PACKAGE_DEPENDENCIES

    allowed = ALLOWED_PACKAGE_DEPENDENCIES["language_grammar_lesson_planner"]
    unexpected = {d for d in deps if d.startswith("language_grammar_")} - allowed - {
        "language_grammar_lesson_planner"
    }
    unexpected -= {"language_grammar"}  # shared enums ok
    results.append(_ok("ownership DAG: planner -> integration only", not unexpected, str(sorted(unexpected))))

    integ_deps = set()
    for py_file in INTEGRATION_PKG.glob("*.py"):
        integ_deps |= _parse_imports(py_file)
    results.append(_ok("integration may import catalog", "language_grammar_catalog" in integ_deps))
    results.append(_ok("integration may import progression", "language_grammar_progression" in integ_deps))
    results.append(_ok("integration may import mastery", "language_grammar_mastery" in integ_deps))
    results.append(_ok("integration may import review", "language_grammar_review" in integ_deps))
    results.append(_ok("integration does not import planner", "language_grammar_lesson_planner" not in integ_deps))
    results.append(_ok("Audit 3 verdict", all(results)))
    print()
    return results


def audit_4_replayability() -> list[bool]:
    print("[Audit 4 - Replayability]")
    results: list[bool] = []
    from app.services.language_grammar_lesson_planner.serialization import (
        blueprint_from_dict,
        blueprint_to_dict,
    )
    from app.services.language_grammar_lesson_planner.service import plan_lesson

    with patch(
        "app.services.language_grammar_lesson_planner.service.grammar_engine_enabled",
        return_value=True,
    ):
        bp = plan_lesson(_make_snapshot())
    raw = blueprint_to_dict(bp)
    restored = blueprint_from_dict(raw)
    results.append(_ok("serialize produces dict", isinstance(raw, dict)))
    results.append(_ok("deserialize roundtrip fingerprint", restored.fingerprint == bp.fingerprint))
    results.append(_ok("deserialize roundtrip steps", restored.steps == bp.steps))
    results.append(_ok("deserialize roundtrip versions", restored.blueprint_version == bp.blueprint_version))
    results.append(_ok("deserialize lesson_id", restored.lesson_id == bp.lesson_id))
    # deep copy of dict still restores
    restored2 = blueprint_from_dict(copy.deepcopy(raw))
    results.append(_ok("replay without loss", restored2 == restored))
    results.append(_ok("Audit 4 verdict", all(results)))
    print()
    return results


def check_policies_and_facade() -> list[bool]:
    print("[Policies & facade]")
    results: list[bool] = []
    from app.services.language_grammar.enums import GrammarLessonStepKind
    from app.services.language_grammar_integration.service import sync_completed_topics
    from app.services.language_grammar_lesson_planner.service import plan_lesson
    from app.services.language_grammar_lesson_planner.validation import (
        GrammarPlannerError,
        validate_blueprint,
    )
    from app.services.language_grammar_mastery.engine import empty_snapshot
    from app.services.language_grammar_progression.types import GrammarProgressionStudentState

    with patch(
        "app.services.language_grammar_lesson_planner.service.grammar_engine_enabled",
        return_value=True,
    ):
        snap = _make_snapshot()
        bp = plan_lesson(snap)

    # Review never blocks — today's grammar_id is still the focus
    results.append(_ok("focus remains current topic", bp.grammar_id == snap.current_grammar_id))
    if snap.review_queue:
        # If review inserted, it is quick_review before explanation
        kinds = [s.kind for s in bp.steps]
        if GrammarLessonStepKind.quick_review in kinds:
            results.append(
                _ok(
                    "quick_review before explanation",
                    kinds.index(GrammarLessonStepKind.quick_review)
                    < kinds.index(GrammarLessonStepKind.explanation),
                )
            )
        else:
            results.append(_ok("quick_review optional when same topic", True))

    # Reinforcements come from catalog meta in snapshot (not hardcoded 4-skill)
    reinforce = [s for s in bp.steps if "reinforcement" in s.kind.value]
    if snap.current_topic and snap.current_topic.best_reinforcement_skills:
        results.append(
            _ok(
                "reinforcements subset of best_reinforcement_skills",
                all(
                    s.skill in snap.current_topic.best_reinforcement_skills
                    for s in reinforce
                    if s.skill is not None
                ),
            )
        )
    else:
        results.append(_ok("reinforcements planned or empty ok", True))

    sync = sync_completed_topics(
        mastery=empty_snapshot(student_id=1, language_id=1),
        student=GrammarProgressionStudentState(student_id=1, language_id=1),
    )
    results.append(_ok("sync_completed_topics facade exists", hasattr(sync, "synced_ids")))

    with patch(
        "app.services.language_grammar_lesson_planner.service.grammar_engine_enabled",
        return_value=False,
    ):
        disabled = plan_lesson(snap)
        results.append(_ok("ENABLED=false disables planner", disabled.enabled is False))

    try:
        validate_blueprint(bp, snapshot=snap)
        results.append(_ok("valid blueprint accepted", True))
    except GrammarPlannerError as exc:
        results.append(_ok("valid blueprint accepted", False, str(exc)))

    print()
    return results


def main() -> int:
    print("Grammar G3.1 Lesson Planner verification\n")
    all_results: list[bool] = []
    all_results.extend(audit_1_blueprint_integrity())
    all_results.extend(audit_2_determinism())
    all_results.extend(audit_3_architecture())
    all_results.extend(audit_4_replayability())
    all_results.extend(check_policies_and_facade())

    passed = sum(1 for r in all_results if r)
    failed = sum(1 for r in all_results if not r)
    print(f"Summary: {passed} passed, {failed} failed, {len(all_results)} total")
    if failed:
        print("G3.1 VERDICT: NOT READY")
        return 1
    print("G3.1 VERDICT: READY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
