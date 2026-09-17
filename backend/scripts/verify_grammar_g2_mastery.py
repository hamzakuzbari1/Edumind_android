"""Verify Grammar G2.2 Mastery Engine (+ G2.1 patch sanity).

Usage (from backend/):
    python scripts/verify_grammar_g2_mastery.py
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

BACKEND = Path(__file__).resolve().parents[1]
SERVICES = BACKEND / "app" / "services"
MASTERY_PKG = SERVICES / "language_grammar_mastery"
EVIDENCE_PKG = SERVICES / "language_grammar_evidence"


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
        grammar_id="gram_present_simple",
        context="daily routines",
        attempt_count=4,
        correct_count=3,
        observation_type=GrammarObservationType.summative,
        source_skill=GrammarEvidenceSourceSkill.writing,
        student_id=1,
        language_id=1,
        observed_at="2026-01-01T00:00:00Z",
        confidence=0.9,
    )
    defaults.update(kwargs)
    return GrammarEvidenceObservation(**defaults)


def audit_1_evidence_integrity() -> list[bool]:
    print("[Audit 1 - Evidence Integrity]")
    results: list[bool] = []
    from app.services.language_grammar.enums import GrammarObservationType
    from app.services.language_grammar_evidence.types import GrammarEvidenceBatch
    from app.services.language_grammar_evidence.validation import (
        GrammarEvidenceError,
        validate_batch,
        validate_observation,
    )

    ok = validate_observation(_obs())
    results.append(_ok("valid evidence accepted", ok.grammar_id == "gram_present_simple"))

    try:
        validate_observation(_obs(grammar_id="gram_not_in_catalog_xyz"))
        results.append(_ok("unknown grammar_id rejected", False))
    except GrammarEvidenceError:
        results.append(_ok("unknown grammar_id rejected", True))

    try:
        validate_observation(_obs(attempt_count=-1))
        results.append(_ok("negative attempts rejected", False))
    except GrammarEvidenceError:
        results.append(_ok("negative attempts rejected", True))

    try:
        validate_observation(_obs(correct_count=9, attempt_count=2))
        results.append(_ok("impossible correct>attempt rejected", False))
    except GrammarEvidenceError:
        results.append(_ok("impossible correct>attempt rejected", True))

    batch = GrammarEvidenceBatch(
        observations=(
            _obs(observation_id="dup"),
            _obs(observation_id="dup", context="other"),
        )
    )
    result = validate_batch(batch)
    results.append(_ok("duplicate evidence IDs rejected", not result.valid))

    try:
        validate_observation(_obs(accuracy_signal=120.0))
        results.append(_ok("impossible signal rejected", False))
    except GrammarEvidenceError:
        results.append(_ok("impossible signal rejected", True))

    results.append(_ok("Audit 1 verdict", all(results)))
    print()
    return results


def audit_2_mastery_integrity() -> list[bool]:
    print("[Audit 2 - Mastery Integrity]")
    results: list[bool] = []
    from app.services.language_grammar_catalog.catalog import get_default_catalog
    from app.services.language_grammar_evidence.types import GrammarEvidenceBatch
    from app.services.language_grammar_mastery.engine import apply_observations, empty_snapshot
    from app.services.language_grammar_mastery.types import (
        derive_overall_mastery,
        to_public_view,
    )

    catalog = get_default_catalog()
    snap = empty_snapshot(student_id=1, language_id=1)
    batch = (
        _obs(observation_id="a1", correct_count=4, attempt_count=4, context="ctx-a"),
        _obs(observation_id="a2", correct_count=3, attempt_count=4, context="ctx-b"),
        _obs(observation_id="a3", correct_count=4, attempt_count=4, context="ctx-c"),
    )
    out = apply_observations(snap, batch, catalog=catalog)
    rec = out.record_for("gram_present_simple")
    results.append(_ok("record created", rec is not None))
    assert rec is not None
    derived = derive_overall_mastery(
        understanding=rec.dimensions.understanding,
        accuracy=rec.dimensions.accuracy,
        fluency=rec.dimensions.fluency,
        retention=rec.dimensions.retention,
    )
    results.append(_ok("overall always derived", abs(rec.dimensions.overall_mastery - derived) < 1e-9))
    results.append(_ok("dimensions independent fields present", rec.dimensions.accuracy != -1))
    results.append(_ok("scores in range", 0 <= rec.dimensions.overall_mastery <= 100))
    results.append(_ok("confidence in range", 0 <= rec.confidence <= 100))

    public = to_public_view(rec)
    results.append(_ok("public view has overall only", not hasattr(public, "understanding")))
    results.append(_ok("public overall matches", public.overall_mastery == rec.dimensions.overall_mastery))

    # No direct overall write path — build_dimensions re-derives
    from app.services.language_grammar_mastery.types import build_dimensions

    dims = build_dimensions(understanding=10, accuracy=20, fluency=30, retention=40)
    results.append(
        _ok(
            "build_dimensions derives overall",
            dims.overall_mastery == derive_overall_mastery(
                understanding=10, accuracy=20, fluency=30, retention=40
            ),
        )
    )
    results.append(_ok("Audit 2 verdict", all(results)))
    print()
    return results


def audit_3_architecture() -> list[bool]:
    print("[Audit 3 - Architecture]")
    results: list[bool] = []
    forbidden = {
        "language_grammar_review",
        "language_grammar_lesson_planner",
        "language_grammar_lesson_runtime",
        "language_grammar_educational_package",
        "language_grammar_analytics",
        "claude_service",
    }
    deps: set[str] = set()
    for py_file in MASTERY_PKG.glob("*.py"):
        deps |= _parse_imports(py_file)
    for dep in sorted(forbidden):
        results.append(_ok(f"mastery does not import {dep}", dep not in deps))

    results.append(_ok("mastery may import catalog", "language_grammar_catalog" in deps))
    results.append(_ok("mastery may import evidence", "language_grammar_evidence" in deps))
    results.append(
        _ok(
            "mastery does not import progression",
            "language_grammar_progression" not in deps,
        )
    )

    from app.services.language_grammar.ownership import ALLOWED_PACKAGE_DEPENDENCIES

    allowed = ALLOWED_PACKAGE_DEPENDENCIES["language_grammar_mastery"]
    unexpected = {d for d in deps if d.startswith("language_grammar_")} - allowed - {
        "language_grammar_mastery"
    }
    results.append(_ok("ownership DAG respected", not unexpected, str(sorted(unexpected))))

    evid_deps: set[str] = set()
    for py_file in EVIDENCE_PKG.glob("*.py"):
        evid_deps |= _parse_imports(py_file)
    results.append(_ok("evidence does not import mastery", "language_grammar_mastery" not in evid_deps))
    results.append(_ok("Audit 3 verdict", all(results)))
    print()
    return results


def audit_4_determinism() -> list[bool]:
    print("[Audit 4 - Determinism]")
    results: list[bool] = []
    from app.services.language_grammar_catalog.catalog import get_default_catalog
    from app.services.language_grammar_mastery.engine import apply_observations, empty_snapshot

    catalog = get_default_catalog()
    observations = (
        _obs(observation_id="z", context="c1", correct_count=2, attempt_count=4),
        _obs(observation_id="a", context="c2", correct_count=4, attempt_count=4),
        _obs(observation_id="m", context="c1", correct_count=3, attempt_count=3),
    )
    snaps = [
        apply_observations(empty_snapshot(student_id=1, language_id=1), observations, catalog=catalog)
        for _ in range(5)
    ]
    first = snaps[0].record_for("gram_present_simple")
    identical = all(
        s.record_for("gram_present_simple") == first for s in snaps[1:]
    ) and all(s.applied_observation_ids == snaps[0].applied_observation_ids for s in snaps[1:])
    results.append(_ok("identical evidence replay => identical mastery", identical))

    # Idempotent re-apply
    again = apply_observations(snaps[0], observations, catalog=catalog)
    results.append(
        _ok(
            "re-applying same evidence is idempotent",
            again.record_for("gram_present_simple") == first
            and again.applied_observation_ids == snaps[0].applied_observation_ids,
        )
    )
    results.append(_ok("Audit 4 verdict", all(results)))
    print()
    return results


def audit_5_migration_safety() -> list[bool]:
    print("[Audit 5 - Migration Safety]")
    results: list[bool] = []
    from app.services.language_grammar.enums import GrammarCandidatePriority, GrammarCEFRBand
    from app.services.language_grammar_legacy_bridge.maps import SPEAKING_GRAM_IDS
    from app.services.language_grammar_mastery.service import compute_mastery_from_evidence
    from app.services.language_grammar_evidence.types import GrammarEvidenceBatch
    from app.services.language_grammar_progression.engine import compute_progression_snapshot
    from app.services.language_grammar_progression.types import GrammarProgressionStudentState
    from app.services.language_grammar_catalog.catalog import get_default_catalog
    from app.services.language_speaking_curriculum_engine.grammar_catalog import (
        select_grammar_targets,
    )

    # G2.1 patch: completed_ids + priorities still work
    catalog = get_default_catalog()
    prog = compute_progression_snapshot(
        catalog=catalog,
        anchor_cefr=GrammarCEFRBand.A2,
        student=GrammarProgressionStudentState(
            student_id=1,
            language_id=1,
            completed_ids=frozenset({"gram_be_present"}),
            unlocked_ids=frozenset({"gram_be_present"}),
        ),
    )
    results.append(_ok("progression uses completed_ids", "completed:" in ",".join(prog.progression_reason)))
    results.append(_ok("progression emits candidate_priorities", len(prog.candidate_priorities) > 0))
    results.append(
        _ok(
            "primary priority present",
            any(e.priority is GrammarCandidatePriority.primary for e in prog.candidate_priorities),
        )
    )

    with patch(
        "app.services.language_grammar_mastery.service.grammar_engine_enabled",
        return_value=True,
    ):
        snap = compute_mastery_from_evidence(
            student_id=1,
            language_id=1,
            batch=GrammarEvidenceBatch(observations=(_obs(observation_id="mig-1"),)),
        )
        results.append(_ok("mastery scores without progression input", snap.enabled))

    # Progression snapshot unchanged after mastery compute (independence)
    prog_after = compute_progression_snapshot(
        catalog=catalog,
        anchor_cefr=GrammarCEFRBand.A2,
        student=GrammarProgressionStudentState(
            student_id=1,
            language_id=1,
            completed_ids=frozenset({"gram_be_present"}),
            unlocked_ids=frozenset({"gram_be_present"}),
        ),
    )
    results.append(
        _ok(
            "progression independent of mastery compute",
            prog.current_grammar_id == prog_after.current_grammar_id
            and prog.unlocked_ids == prog_after.unlocked_ids,
        )
    )

    results.append(_ok("speaking gram ids still mapped", "gram_present_simple" in SPEAKING_GRAM_IDS))
    results.append(_ok("speaking select still works", len(select_grammar_targets(cefr="A2", count=1)) == 1))
    results.append(
        _ok(
            "writing grammar package has no mastery engine",
            not (SERVICES / "language_writing_grammar_progression" / "engine.py").is_file(),
        )
    )
    results.append(_ok("Audit 5 verdict", all(results)))
    print()
    return results


def check_persistence_and_flags() -> list[bool]:
    print("[Persistence & flags]")
    results: list[bool] = []
    from app.services.language_grammar_evidence.types import GrammarEvidenceBatch
    from app.services.language_grammar_mastery.engine import apply_observations, empty_snapshot
    from app.services.language_grammar_mastery.service import compute_mastery_from_evidence
    from app.services.language_grammar_mastery.storage import (
        bucket_from_snapshot,
        snapshot_from_bucket,
    )
    from app.services.language_grammar_catalog.catalog import get_default_catalog
    from app.services.language_grammar_mastery.types import derive_overall_mastery

    with patch(
        "app.services.language_grammar_mastery.service.grammar_engine_enabled",
        return_value=False,
    ):
        disabled = compute_mastery_from_evidence(
            student_id=1,
            language_id=1,
            batch=GrammarEvidenceBatch(observations=(_obs(),)),
        )
        results.append(_ok("ENABLED=false disables mastery", disabled.enabled is False))

    catalog = get_default_catalog()
    snap = apply_observations(
        empty_snapshot(student_id=1, language_id=1),
        (_obs(observation_id="p1"), _obs(observation_id="p2", context="other")),
        catalog=catalog,
    )
    bucket = bucket_from_snapshot(snap)
    results.append(_ok("persistence omits no records key", "records" in bucket))
    roundtrip = snapshot_from_bucket(bucket, student_id=1, language_id=1)
    rec = roundtrip.record_for("gram_present_simple")
    assert rec is not None
    results.append(
        _ok(
            "load re-derives overall",
            abs(
                rec.dimensions.overall_mastery
                - derive_overall_mastery(
                    understanding=rec.dimensions.understanding,
                    accuracy=rec.dimensions.accuracy,
                    fluency=rec.dimensions.fluency,
                    retention=rec.dimensions.retention,
                )
            )
            < 1e-9,
        )
    )
    results.append(
        _ok(
            "contexts persist across reload",
            len(roundtrip.contexts_by_grammar_id.get("gram_present_simple", frozenset())) >= 2,
        )
    )
    print()
    return results


def audit_policy_patch() -> list[bool]:
    """G2.2 patch: replaceable MasteryScoringPolicy; default overall identical."""
    print("[Patch - MasteryScoringPolicy]")
    results: list[bool] = []
    from app.services.language_grammar_mastery.policy import (
        DefaultWeightedMasteryScoringPolicy,
        MasteryDimensionInputs,
        MasteryScoringPolicy,
        OVERALL_WEIGHT_ACCURACY,
        OVERALL_WEIGHT_FLUENCY,
        OVERALL_WEIGHT_RETENTION,
        OVERALL_WEIGHT_UNDERSTANDING,
        get_active_mastery_scoring_policy,
        set_active_mastery_scoring_policy,
    )
    from app.services.language_grammar_mastery.types import (
        build_dimensions,
        derive_overall_mastery,
    )

    policy = get_active_mastery_scoring_policy()
    results.append(_ok("active policy is MasteryScoringPolicy", isinstance(policy, MasteryScoringPolicy)))
    results.append(
        _ok(
            "default policy id",
            getattr(policy, "policy_id", "") == "default_weighted_v1",
        )
    )
    results.append(
        _ok(
            "default weights unchanged",
            (
                OVERALL_WEIGHT_UNDERSTANDING,
                OVERALL_WEIGHT_ACCURACY,
                OVERALL_WEIGHT_FLUENCY,
                OVERALL_WEIGHT_RETENTION,
            )
            == (0.30, 0.35, 0.20, 0.15),
        )
    )

    samples = (
        (0.0, 0.0, 0.0, 0.0),
        (10.0, 20.0, 30.0, 40.0),
        (100.0, 100.0, 100.0, 100.0),
        (77.1234, 12.5, 88.0, 3.1415),
        (55.0, 0.0, 100.0, 25.0),
    )
    identical = True
    for u, a, f, r in samples:
        # Golden pre-policy formula — must never drift.
        baseline = round(max(0.0, min(100.0, 0.30 * u + 0.35 * a + 0.20 * f + 0.15 * r)), 4)
        via_api = derive_overall_mastery(
            understanding=u, accuracy=a, fluency=f, retention=r, confidence=99.0
        )
        via_policy = policy.derive_overall(
            MasteryDimensionInputs(
                understanding=u, accuracy=a, fluency=f, retention=r, confidence=99.0
            )
        )
        if abs(via_api - baseline) > 1e-12 or abs(via_policy - baseline) > 1e-12:
            identical = False
            break
    results.append(_ok("overall values identical to pre-policy formula", identical))

    dims = build_dimensions(understanding=10, accuracy=20, fluency=30, retention=40)
    results.append(
        _ok(
            "build_dimensions uses policy",
            abs(dims.overall_mastery - round(0.30 * 10 + 0.35 * 20 + 0.20 * 30 + 0.15 * 40, 4))
            < 1e-12,
        )
    )

    engine_src = (MASTERY_PKG / "engine.py").read_text(encoding="utf-8")
    results.append(
        _ok(
            "engine has no overall weight hardcode",
            "OVERALL_WEIGHT_" not in engine_src
            and "0.30 * " not in engine_src
            and "weight_understanding" not in engine_src,
        )
    )

    # Replaceability without engine edits
    class _AltPolicy:
        policy_id = "alt_test"

        def derive_overall(self, dims: MasteryDimensionInputs) -> float:
            return round(dims.accuracy, 4)

    prev = get_active_mastery_scoring_policy()
    try:
        set_active_mastery_scoring_policy(_AltPolicy())  # type: ignore[arg-type]
        alt = derive_overall_mastery(understanding=1, accuracy=42, fluency=3, retention=4)
        results.append(_ok("active policy is replaceable", alt == 42.0))
    finally:
        set_active_mastery_scoring_policy(None)
    results.append(
        _ok(
            "reset restores default",
            get_active_mastery_scoring_policy().policy_id == "default_weighted_v1"
            and isinstance(get_active_mastery_scoring_policy(), DefaultWeightedMasteryScoringPolicy),
        )
    )
    results.append(_ok("no prior policy leak", prev.policy_id == "default_weighted_v1"))

    # Storage / ownership / API surface unchanged for this patch
    storage_src = (MASTERY_PKG / "storage.py").read_text(encoding="utf-8")
    results.append(_ok("storage does not import policy", "policy" not in storage_src))
    results.append(
        _ok(
            "schema version unchanged",
            "GRAMMAR_MASTERY_SCHEMA_VERSION = 1" in (MASTERY_PKG / "types.py").read_text(encoding="utf-8"),
        )
    )
    results.append(_ok("Audit policy patch verdict", all(results)))
    print()
    return results


def main() -> int:
    print("Grammar G2.2 Mastery Engine verification\n")
    all_results: list[bool] = []
    all_results.extend(audit_1_evidence_integrity())
    all_results.extend(audit_2_mastery_integrity())
    all_results.extend(audit_3_architecture())
    all_results.extend(audit_4_determinism())
    all_results.extend(audit_5_migration_safety())
    all_results.extend(check_persistence_and_flags())
    all_results.extend(audit_policy_patch())

    passed = sum(1 for r in all_results if r)
    failed = sum(1 for r in all_results if not r)
    print(f"Summary: {passed} passed, {failed} failed, {len(all_results)} total")
    if failed:
        print("G2.2 VERDICT: NOT READY")
        return 1
    print("G2.2 VERDICT: READY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
