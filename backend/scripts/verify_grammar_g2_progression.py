"""Verify Grammar G2.1 Progression Engine.

Usage (from backend/):
    python scripts/verify_grammar_g2_progression.py
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

BACKEND = Path(__file__).resolve().parents[1]
SERVICES = BACKEND / "app" / "services"
PROG_PKG = SERVICES / "language_grammar_progression"


def _ok(name: str, passed: bool, detail: str = "") -> bool:
    status = "PASS" if passed else "FAIL"
    suffix = f" - {detail}" if detail else ""
    print(f"  {name}: {status}{suffix}")
    return passed


def _parse_imports(py_file: Path) -> set[str]:
    try:
        tree = ast.parse(py_file.read_text(encoding="utf-8"))
    except SyntaxError as exc:
        raise RuntimeError(f"Syntax error in {py_file}: {exc}") from exc
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            if node.module.startswith("app.services."):
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


def audit_1_progression_integrity() -> list[bool]:
    print("[Audit 1 - Progression Integrity]")
    results: list[bool] = []
    from app.services.language_grammar.enums import GrammarCEFRBand
    from app.services.language_grammar_catalog.catalog import get_default_catalog
    from app.services.language_grammar_progression.engine import (
        GrammarProgressionError,
        compute_progression_snapshot,
    )
    from app.services.language_grammar_progression.types import GrammarProgressionStudentState

    catalog = get_default_catalog()
    by_id = {t.grammar_id: t for t in catalog.topics}

    state = GrammarProgressionStudentState(student_id=1, language_id=1)
    snap = compute_progression_snapshot(
        catalog=catalog, anchor_cefr=GrammarCEFRBand.A2, student=state
    )

    results.append(_ok("candidate pool non-empty", len(snap.candidate_pool_ids) > 0))
    results.append(
        _ok(
            "candidates are <= anchor CEFR",
            all(by_id[gid].cefr_band.value in {"A1", "A2"} for gid in snap.candidate_pool_ids),
        )
    )
    results.append(_ok("roots unlocked on cold start", "gram_be_present" in snap.unlocked_ids))
    results.append(
        _ok(
            "placement baseline unlocks anchor-band topics with lower-band prerequisites",
            "gram_past_simple" in snap.unlocked_ids,
        )
    )
    results.append(
        _ok(
            "no duplicate unlocked ids",
            len(snap.unlocked_ids) == len(set(snap.unlocked_ids)),
        )
    )
    results.append(
        _ok(
            "locked and unlocked disjoint",
            set(snap.locked_ids).isdisjoint(snap.unlocked_ids),
        )
    )
    results.append(
        _ok(
            "B1 topic not in A2 candidate pool",
            "gram_present_perfect" not in snap.candidate_pool_ids,
        )
    )
    results.append(
        _ok(
            "B1 topic is future when stretch off",
            "gram_present_perfect" in snap.future_ids,
        )
    )

    snap_bad = compute_progression_snapshot(
        catalog=catalog,
        anchor_cefr=GrammarCEFRBand.A2,
        student=GrammarProgressionStudentState(
            student_id=1,
            language_id=1,
            unlocked_ids=frozenset({"gram_past_simple"}),
        ),
    )
    results.append(
        _ok(
            "seeded unlock does not invent missing catalog topics",
            all(gid in by_id for gid in snap_bad.unlocked_ids),
        )
    )

    try:
        compute_progression_snapshot(
            catalog=catalog,
            anchor_cefr=GrammarCEFRBand.A2,
            student=GrammarProgressionStudentState(
                student_id=1,
                language_id=1,
                completed_ids=frozenset({"gram_not_real_topic"}),
            ),
        )
        results.append(_ok("rejects unknown grammar_id", False))
    except GrammarProgressionError:
        results.append(_ok("rejects unknown grammar_id", True))

    completed_state = GrammarProgressionStudentState(
        student_id=1,
        language_id=1,
        completed_ids=frozenset(
            {
                "gram_be_present",
                "gram_personal_pronouns",
                "gram_present_simple",
            }
        ),
        unlocked_ids=frozenset(
            {
                "gram_be_present",
                "gram_personal_pronouns",
                "gram_present_simple",
            }
        ),
    )
    snap2 = compute_progression_snapshot(
        catalog=catalog, anchor_cefr=GrammarCEFRBand.A2, student=completed_state
    )
    results.append(
        _ok(
            "completed parents unlock past_simple",
            "gram_past_simple" in snap2.unlocked_ids,
        )
    )
    results.append(_ok("no unreachable/unknown unlocks", set(snap2.unlocked_ids) <= set(by_id)))

    stretch_state = GrammarProgressionStudentState(
        student_id=1,
        language_id=1,
        stretch_allowed=True,
        completed_ids=completed_state.completed_ids,
        unlocked_ids=completed_state.unlocked_ids,
    )
    snap_s = compute_progression_snapshot(
        catalog=catalog, anchor_cefr=GrammarCEFRBand.A2, student=stretch_state
    )
    results.append(_ok("stretch pool non-empty when allowed", len(snap_s.stretch_ids) > 0))
    results.append(
        _ok(
            "stretch limited to early next-band topics",
            len(snap_s.stretch_ids) <= 2
            and all(by_id[g].cefr_band.value == "B1" for g in snap_s.stretch_ids),
        )
    )

    from app.services.language_grammar.enums import GrammarCandidatePriority

    pri_map = {e.grammar_id: e.priority for e in snap.candidate_priorities}
    results.append(_ok("candidate_priorities non-empty", len(snap.candidate_priorities) > 0))
    if snap.current_grammar_id:
        results.append(
            _ok(
                "current has PRIMARY priority",
                pri_map.get(snap.current_grammar_id) is GrammarCandidatePriority.primary,
            )
        )
    results.append(
        _ok(
            "stretch ids marked STRETCH",
            all(
                e.priority is GrammarCandidatePriority.stretch
                for e in snap_s.candidate_priorities
                if e.grammar_id in snap_s.stretch_ids
            )
            and len(snap_s.stretch_ids) > 0,
        )
    )

    results.append(_ok("Audit 1 verdict", all(results)))
    print()
    return results


def audit_2_determinism() -> list[bool]:
    print("[Audit 2 - Determinism]")
    results: list[bool] = []
    from app.services.language_grammar.enums import GrammarCEFRBand
    from app.services.language_grammar_catalog.catalog import get_default_catalog
    from app.services.language_grammar_progression.engine import compute_progression_snapshot
    from app.services.language_grammar_progression.types import GrammarProgressionStudentState

    catalog = get_default_catalog()
    state = GrammarProgressionStudentState(
        student_id=42,
        language_id=1,
        completed_ids=frozenset({"gram_be_present", "gram_personal_pronouns"}),
        unlocked_ids=frozenset({"gram_be_present", "gram_personal_pronouns"}),
        stretch_allowed=False,
    )
    snaps = [
        compute_progression_snapshot(
            catalog=catalog, anchor_cefr=GrammarCEFRBand.A2, student=state
        )
        for _ in range(5)
    ]
    first = snaps[0]
    identical = all(
        (
            s.current_grammar_id,
            s.next_grammar_id,
            s.unlocked_ids,
            s.locked_ids,
            s.future_ids,
            s.stretch_ids,
            s.candidate_pool_ids,
            s.progression_reason,
        )
        == (
            first.current_grammar_id,
            first.next_grammar_id,
            first.unlocked_ids,
            first.locked_ids,
            first.future_ids,
            first.stretch_ids,
            first.candidate_pool_ids,
            first.progression_reason,
        )
        for s in snaps[1:]
    )
    results.append(_ok("identical inputs => identical outputs (x5)", identical))

    state_b = GrammarProgressionStudentState(
        student_id=42,
        language_id=1,
        completed_ids=frozenset({"gram_personal_pronouns", "gram_be_present"}),
        unlocked_ids=frozenset({"gram_personal_pronouns", "gram_be_present"}),
    )
    snap_b = compute_progression_snapshot(
        catalog=catalog, anchor_cefr=GrammarCEFRBand.A2, student=state_b
    )
    results.append(
        _ok(
            "frozenset input order does not affect output",
            snap_b.unlocked_ids == first.unlocked_ids
            and snap_b.current_grammar_id == first.current_grammar_id,
        )
    )
    results.append(_ok("Audit 2 verdict", all(results)))
    print()
    return results


def audit_3_architecture() -> list[bool]:
    print("[Audit 3 - Architecture]")
    results: list[bool] = []
    forbidden = {
        "language_grammar_mastery",
        "language_grammar_review",
        "language_grammar_lesson_planner",
        "language_grammar_lesson_runtime",
        "language_grammar_educational_package",
        "language_grammar_analytics",
        "language_grammar_integration",
        "language_grammar_evidence",
        "claude_service",
    }
    deps: set[str] = set()
    for py_file in PROG_PKG.glob("*.py"):
        deps |= _parse_imports(py_file)

    for dep in sorted(forbidden):
        results.append(_ok(f"progression does not import {dep}", dep not in deps))

    results.append(_ok("progression may import catalog", "language_grammar_catalog" in deps))
    results.append(
        _ok(
            "progression may import legacy_bridge",
            "language_grammar_legacy_bridge" in deps,
        )
    )

    from app.services.language_grammar.ownership import ALLOWED_PACKAGE_DEPENDENCIES

    allowed = ALLOWED_PACKAGE_DEPENDENCIES["language_grammar_progression"]
    grammar_deps = {d for d in deps if d.startswith("language_grammar_")}
    unexpected = grammar_deps - allowed - {"language_grammar_progression"}
    results.append(_ok("ownership DAG respected", not unexpected, str(sorted(unexpected))))

    results.append(_ok("engine.py exists", (PROG_PKG / "engine.py").is_file()))
    results.append(_ok("storage.py exists", (PROG_PKG / "storage.py").is_file()))
    results.append(_ok("service.py exists", (PROG_PKG / "service.py").is_file()))
    results.append(_ok("Audit 3 verdict", all(results)))
    print()
    return results


def audit_4_migration_safety() -> list[bool]:
    print("[Audit 4 - Migration Safety]")
    results: list[bool] = []
    from app.services.language_grammar.enums import GrammarCEFRBand
    from app.services.language_grammar_legacy_bridge.maps import (
        BKT_GRAMMAR_TO_GRAMMAR_ID,
        SPEAKING_GRAM_IDS,
        WRITING_STRUCTURE_TO_GRAMMAR_ID,
    )
    from app.services.language_grammar_progression.legacy import normalize_to_grammar_id
    from app.services.language_grammar_progression.service import compute_from_state
    from app.services.language_grammar_progression.types import GrammarProgressionStudentState
    from app.services.language_speaking_curriculum_engine.grammar_catalog import (
        select_grammar_targets,
    )

    results.append(
        _ok(
            "legacy speaking id normalizes",
            normalize_to_grammar_id("gram_present_simple") == "gram_present_simple",
        )
    )
    results.append(
        _ok(
            "legacy BKT normalizes",
            normalize_to_grammar_id("grammar.present_simple") == "gram_present_simple",
        )
    )
    results.append(
        _ok(
            "legacy writing structure normalizes",
            normalize_to_grammar_id("present_simple") == "gram_present_simple",
        )
    )

    with patch(
        "app.services.language_grammar_progression.service.grammar_engine_enabled",
        return_value=True,
    ):
        state = GrammarProgressionStudentState(
            student_id=1,
            language_id=1,
            completed_ids=frozenset({"grammar.present_simple", "present_simple"}),
            unlocked_ids=frozenset(
                {"gram_be_present", "gram_personal_pronouns", "gram_present_simple"}
            ),
        )
        snap = compute_from_state(anchor_cefr=GrammarCEFRBand.A2, student=state)
        results.append(_ok("legacy completed ids accepted via normalize", snap.enabled))

    targets = select_grammar_targets(cefr="A2", count=2)
    results.append(_ok("speaking select_grammar_targets still works", len(targets) == 2))
    results.append(
        _ok(
            "speaking targets are catalog/speaking-compatible ids",
            all(t.grammar_topic_id.startswith("gram_") for t in targets),
        )
    )

    results.append(_ok("speaking gram set documented", len(SPEAKING_GRAM_IDS) >= 10))
    results.append(_ok("writing maps documented", len(WRITING_STRUCTURE_TO_GRAMMAR_ID) >= 5))
    results.append(_ok("BKT maps documented", len(BKT_GRAMMAR_TO_GRAMMAR_ID) >= 4))

    writing_gp = SERVICES / "language_writing_grammar_progression"
    results.append(_ok("writing grammar package remains separate contracts", writing_gp.is_dir()))
    results.append(
        _ok(
            "writing grammar package has no engine claiming shared progression",
            not (writing_gp / "engine.py").is_file(),
        )
    )

    results.append(_ok("Audit 4 verdict", all(results)))
    print()
    return results


def check_flags_and_storage() -> list[bool]:
    print("[Flags & storage]")
    results: list[bool] = []
    from app.services.language_grammar.enums import GrammarCEFRBand
    from app.services.language_grammar_progression.service import (
        compute_from_state,
        selection_snapshot_or_disabled,
    )
    from app.services.language_grammar_progression.storage import (
        bucket_from_student_state,
        merge_progression_into_payload,
        student_state_from_bucket,
    )
    from app.services.language_grammar_progression.types import GrammarProgressionStudentState

    with patch(
        "app.services.language_grammar_progression.service.grammar_engine_enabled",
        return_value=False,
    ):
        disabled = compute_from_state(
            anchor_cefr=GrammarCEFRBand.A2,
            student=GrammarProgressionStudentState(student_id=1, language_id=1),
        )
        results.append(_ok("ENABLED=false returns disabled snapshot", disabled.enabled is False))
        results.append(_ok("ENABLED=false has empty candidate pool", disabled.candidate_pool_ids == ()))

    with patch(
        "app.services.language_grammar_progression.service.grammar_engine_enabled",
        return_value=True,
    ):
        enabled = compute_from_state(
            anchor_cefr=GrammarCEFRBand.A2,
            student=GrammarProgressionStudentState(student_id=1, language_id=1),
        )
        results.append(_ok("ENABLED=true computes unlocks", len(enabled.unlocked_ids) > 0))

        with patch(
            "app.services.language_grammar_progression.service.grammar_engine_select_enabled",
            return_value=False,
        ):
            sel = selection_snapshot_or_disabled(enabled)
            results.append(
                _ok(
                    "SELECT=false hides current/next",
                    sel.current_grammar_id is None and sel.next_grammar_id is None,
                )
            )

    state = GrammarProgressionStudentState(
        student_id=1,
        language_id=1,
        completed_ids=frozenset({"gram_be_present"}),
        unlocked_ids=frozenset({"gram_be_present"}),
        stretch_allowed=True,
    )
    bucket = bucket_from_student_state(state)
    results.append(_ok("storage persists completed_ids sorted", bucket["completed_ids"] == ["gram_be_present"]))
    results.append(_ok("storage does not persist candidate_pool", "candidate_pool_ids" not in bucket))
    payload = merge_progression_into_payload({"speaking": {"x": 1}}, bucket)
    results.append(_ok("storage preserves sibling JSON keys", "speaking" in payload))
    results.append(_ok("storage nests under grammar.progression", "grammar" in payload))
    roundtrip = student_state_from_bucket(
        payload["grammar"]["progression"], student_id=1, language_id=1
    )
    results.append(_ok("storage roundtrip preserves completed", roundtrip.completed_ids == state.completed_ids))
    print()
    return results


def main() -> int:
    print("Grammar G2.1 Progression Engine verification\n")
    all_results: list[bool] = []
    all_results.extend(audit_1_progression_integrity())
    all_results.extend(audit_2_determinism())
    all_results.extend(audit_3_architecture())
    all_results.extend(audit_4_migration_safety())
    all_results.extend(check_flags_and_storage())

    passed = sum(1 for r in all_results if r)
    failed = sum(1 for r in all_results if not r)
    print(f"Summary: {passed} passed, {failed} failed, {len(all_results)} total")
    if failed:
        print("G2.1 VERDICT: NOT READY")
        return 1
    print("G2.1 VERDICT: READY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
