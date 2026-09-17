"""Verify Grammar G2.3 Review Engine.

Usage (from backend/):
    python scripts/verify_grammar_g2_review.py
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
REVIEW_PKG = SERVICES / "language_grammar_review"


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
        observation_id="obs-1",
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


def _mastery_with_evidence(*, as_of_anchor: str = "2026-01-01T12:00:00Z"):
    from app.services.language_grammar_catalog.catalog import get_default_catalog
    from app.services.language_grammar_mastery.engine import apply_observations, empty_snapshot

    catalog = get_default_catalog()
    snap = empty_snapshot(student_id=1, language_id=1)
    batch = (
        _obs(observation_id="r1", context="c1", observed_at=as_of_anchor),
        _obs(observation_id="r2", context="c2", observed_at=as_of_anchor, correct_count=4),
        _obs(observation_id="r3", context="c3", observed_at=as_of_anchor, correct_count=2),
    )
    return apply_observations(snap, batch, catalog=catalog), catalog


def audit_1_queue_integrity() -> list[bool]:
    print("[Audit 1 - Queue Integrity]")
    results: list[bool] = []
    from app.services.language_grammar_review.engine import compute_review_snapshot, empty_student_state

    mastery, catalog = _mastery_with_evidence()
    student = empty_student_state(student_id=1, language_id=1)
    # Far future as_of relative to evidence → many due
    as_of = "2026-03-01T12:00:00Z"
    snap = compute_review_snapshot(
        mastery=mastery, student=student, catalog=catalog, as_of=as_of
    )
    ids = [i.grammar_id for i in snap.queue.items]
    results.append(_ok("queue non-empty when overdue", len(ids) >= 1))
    results.append(_ok("no duplicate queue ids", len(ids) == len(set(ids))))
    results.append(
        _ok(
            "all queue ids in catalog",
            all(catalog.topic_by_id(g) is not None for g in ids),
        )
    )
    results.append(
        _ok(
            "all schedule ids in catalog",
            all(catalog.topic_by_id(i.grammar_id) is not None for i in snap.schedule),
        )
    )

    # Stable ordering: recompute and compare
    snap2 = compute_review_snapshot(
        mastery=mastery, student=student, catalog=catalog, as_of=as_of
    )
    results.append(
        _ok(
            "stable ordering",
            [i.grammar_id for i in snap.queue.items]
            == [i.grammar_id for i in snap2.queue.items]
            and [i.priority for i in snap.queue.items]
            == [i.priority for i in snap2.queue.items],
        )
    )
    # Priority rank non-decreasing
    from app.services.language_grammar.enums import GrammarReviewPriority

    rank = {
        GrammarReviewPriority.critical: 0,
        GrammarReviewPriority.high: 1,
        GrammarReviewPriority.medium: 2,
        GrammarReviewPriority.low: 3,
    }
    ranks = [rank[i.priority] for i in snap.queue.items]
    results.append(_ok("priority ordering non-decreasing", ranks == sorted(ranks)))
    results.append(_ok("Audit 1 verdict", all(results)))
    print()
    return results


def audit_2_architecture() -> list[bool]:
    print("[Audit 2 - Architecture]")
    results: list[bool] = []
    forbidden = {
        "language_grammar_progression",
        "language_grammar_lesson_planner",
        "language_grammar_lesson_runtime",
        "language_grammar_educational_package",
        "language_grammar_analytics",
        "claude_service",
    }
    deps: set[str] = set()
    for py_file in REVIEW_PKG.glob("*.py"):
        deps |= _parse_imports(py_file)
    for dep in sorted(forbidden):
        results.append(_ok(f"review does not import {dep}", dep not in deps))

    results.append(_ok("review may import catalog", "language_grammar_catalog" in deps))
    results.append(_ok("review may import mastery", "language_grammar_mastery" in deps))

    from app.services.language_grammar.ownership import ALLOWED_PACKAGE_DEPENDENCIES

    allowed = ALLOWED_PACKAGE_DEPENDENCIES["language_grammar_review"]
    unexpected = {d for d in deps if d.startswith("language_grammar_")} - allowed - {
        "language_grammar_review"
    }
    # language_grammar shared infra is ok via app.services.language_grammar
    unexpected -= {"language_grammar"}
    results.append(_ok("ownership DAG respected", not unexpected, str(sorted(unexpected))))
    results.append(_ok("Audit 2 verdict", all(results)))
    print()
    return results


def audit_3_determinism() -> list[bool]:
    print("[Audit 3 - Determinism]")
    results: list[bool] = []
    from app.services.language_grammar_review.engine import compute_review_snapshot, empty_student_state

    mastery, catalog = _mastery_with_evidence()
    student = empty_student_state(student_id=1, language_id=1)
    as_of = "2026-02-15T08:00:00Z"
    snaps = [
        compute_review_snapshot(
            mastery=mastery, student=student, catalog=catalog, as_of=as_of
        )
        for _ in range(5)
    ]
    first = snaps[0]
    identical = all(
        s.queue.items == first.queue.items and s.schedule == first.schedule for s in snaps[1:]
    )
    results.append(_ok("identical mastery replay => identical queue", identical))
    results.append(_ok("Audit 3 verdict", all(results)))
    print()
    return results


def audit_4_progression_independence() -> list[bool]:
    print("[Audit 4 - Progression Independence]")
    results: list[bool] = []
    from app.services.language_grammar.enums import GrammarCEFRBand
    from app.services.language_grammar_progression.engine import compute_progression_snapshot
    from app.services.language_grammar_progression.types import GrammarProgressionStudentState
    from app.services.language_grammar_catalog.catalog import get_default_catalog
    from app.services.language_grammar_review.engine import (
        compute_review_snapshot,
        empty_student_state,
        record_review_completed,
    )
    from app.services.language_grammar.enums import GrammarReviewMode

    catalog = get_default_catalog()
    prog_state = GrammarProgressionStudentState(
        student_id=1,
        language_id=1,
        completed_ids=frozenset(),
        unlocked_ids=frozenset(),
        current_grammar_id=None,
        stretch_allowed=False,
    )
    before = compute_progression_snapshot(
        catalog=catalog,
        anchor_cefr=GrammarCEFRBand.A1,
        student=prog_state,
    )
    before_copy = copy.deepcopy(
        (
            before.current_grammar_id,
            before.next_grammar_id,
            before.unlocked_ids,
            before.locked_ids,
            before.candidate_pool_ids,
        )
    )

    mastery, _ = _mastery_with_evidence()
    review_state = empty_student_state(student_id=1, language_id=1)
    _ = compute_review_snapshot(
        mastery=mastery,
        student=review_state,
        catalog=catalog,
        as_of="2026-03-01T00:00:00Z",
    )
    review_state = record_review_completed(
        review_state,
        grammar_id="gram_present_simple",
        reviewed_at="2026-03-01T00:00:00Z",
        mode=GrammarReviewMode.spaced_practice,
        catalog=catalog,
    )

    after = compute_progression_snapshot(
        catalog=catalog,
        anchor_cefr=GrammarCEFRBand.A1,
        student=prog_state,
    )
    after_tuple = (
        after.current_grammar_id,
        after.next_grammar_id,
        after.unlocked_ids,
        after.locked_ids,
        after.candidate_pool_ids,
    )
    results.append(_ok("review does not change current/next/unlock", before_copy == after_tuple))
    results.append(
        _ok(
            "review history updated independently",
            review_state.history_for("gram_present_simple") is not None
            and review_state.history_for("gram_present_simple").review_count == 1,
        )
    )
    results.append(_ok("Audit 4 verdict", all(results)))
    print()
    return results


def check_scheduling_and_validation() -> list[bool]:
    print("[Scheduling & validation]")
    results: list[bool] = []
    from app.services.language_grammar.enums import GrammarReviewMode
    from app.services.language_grammar_review.engine import (
        GrammarReviewError,
        compute_review_snapshot,
        empty_student_state,
        record_review_completed,
    )
    from app.services.language_grammar_review.service import compute_from_mastery
    from app.services.language_grammar_review.storage import (
        bucket_from_student_state,
        student_state_from_bucket,
    )

    mastery, catalog = _mastery_with_evidence(as_of_anchor="2026-01-01T12:00:00Z")
    student = empty_student_state(student_id=1, language_id=1)

    soon = compute_review_snapshot(
        mastery=mastery,
        student=student,
        catalog=catalog,
        as_of="2026-01-01T12:00:00Z",
    )
    later = compute_review_snapshot(
        mastery=mastery,
        student=student,
        catalog=catalog,
        as_of="2026-06-01T12:00:00Z",
    )
    results.append(
        _ok(
            "later as_of yields more/equal due items",
            len(later.queue.items) >= len(soon.queue.items),
        )
    )
    results.append(
        _ok(
            "schedule entries have required fields",
            all(
                i.grammar_id
                and i.due_at
                and i.priority
                and i.reason
                and i.recommended_review_mode
                for i in later.schedule
            ),
        )
    )

    # Completing a review should push due_at forward
    reviewed = record_review_completed(
        student,
        grammar_id="gram_present_simple",
        reviewed_at="2026-06-01T12:00:00Z",
        mode=GrammarReviewMode.quick_recall,
        catalog=catalog,
    )
    after_review = compute_review_snapshot(
        mastery=mastery,
        student=reviewed,
        catalog=catalog,
        as_of="2026-06-01T12:00:00Z",
    )
    item_before = later.item_for("gram_present_simple")
    item_after = after_review.item_for("gram_present_simple")
    results.append(_ok("schedule has present_simple", item_before is not None and item_after is not None))
    if item_before and item_after:
        results.append(
            _ok(
                "review completion extends due_at",
                item_after.due_at >= item_before.due_at,
            )
        )

    try:
        record_review_completed(
            student,
            grammar_id="gram_not_a_real_topic_zzz",
            reviewed_at="2026-06-01T12:00:00Z",
            mode=GrammarReviewMode.spaced_practice,
            catalog=catalog,
        )
        results.append(_ok("unknown grammar_id rejected", False))
    except GrammarReviewError:
        results.append(_ok("unknown grammar_id rejected", True))

    # Persistence roundtrip
    bucket = bucket_from_student_state(reviewed)
    restored = student_state_from_bucket(bucket, student_id=1, language_id=1)
    results.append(
        _ok(
            "history persists",
            restored.history_for("gram_present_simple") is not None
            and restored.history_for("gram_present_simple").review_count == 1,
        )
    )

    with patch(
        "app.services.language_grammar_review.service.grammar_engine_enabled",
        return_value=False,
    ):
        disabled = compute_from_mastery(mastery=mastery, as_of="2026-06-01T12:00:00Z")
        results.append(_ok("ENABLED=false disables review", disabled.enabled is False))

    # Broken state
    try:
        student_state_from_bucket(
            {
                "schema_version": 1,
                "history": [
                    {"grammar_id": "gram_present_simple", "review_count": -1},
                ],
            },
            student_id=1,
            language_id=1,
        )
        results.append(_ok("negative review_count rejected", False))
    except ValueError:
        results.append(_ok("negative review_count rejected", True))

    print()
    return results


def check_legacy_compatibility() -> list[bool]:
    print("[Legacy compatibility]")
    results: list[bool] = []
    from app.services.language_grammar_legacy_bridge.maps import SPEAKING_GRAM_IDS
    from app.services.language_grammar_review.types import GrammarReviewItem, GrammarReviewQueue

    results.append(_ok("G0 GrammarReviewQueue still exists", GrammarReviewQueue is not None))
    results.append(_ok("G0 GrammarReviewItem still exists", GrammarReviewItem is not None))
    results.append(_ok("speaking gram map non-empty", len(SPEAKING_GRAM_IDS) > 0))
    # Review must not own speaking IDs — only consume mastery which uses canonical ids
    results.append(
        _ok(
            "review package has no speaking adapter rewrite",
            not (REVIEW_PKG / "legacy.py").is_file(),
        )
    )
    print()
    return results


def main() -> int:
    print("Grammar G2.3 Review Engine verification\n")
    all_results: list[bool] = []
    all_results.extend(audit_1_queue_integrity())
    all_results.extend(audit_2_architecture())
    all_results.extend(audit_3_determinism())
    all_results.extend(audit_4_progression_independence())
    all_results.extend(check_scheduling_and_validation())
    all_results.extend(check_legacy_compatibility())

    passed = sum(1 for r in all_results if r)
    failed = sum(1 for r in all_results if not r)
    print(f"Summary: {passed} passed, {failed} failed, {len(all_results)} total")
    if failed:
        print("G2.3 VERDICT: NOT READY")
        return 1
    print("G2.3 VERDICT: READY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
