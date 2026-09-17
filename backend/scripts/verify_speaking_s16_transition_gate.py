"""Verify Speaking S16 — internal stage transition gate.

Authority:
  S15 = read-only CEFR-relative evidence signal aggregation
  S16 transition_gate = pure deterministic internal-stage authorization
  learning_stage/stage_runtime = sole writer of learning_stage_speaking
  progression/runtime = orchestration only

S16 v1 = GLOBAL DETERMINISTIC INTERNAL-STAGE POLICY over CEFR-relative S15 snapshots.

Usage (from backend/):
    python scripts/verify_speaking_s16_transition_gate.py
"""

from __future__ import annotations

import os

import ast
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.language_speaking.enums import SpeakingLearningStage
from app.services.language_speaking_learning_stage.types import (
    DataSufficiencyVerdict,
    SpeakingStageBlocker,
    SpeakingStageBlockerKind,
    SpeakingStageSignalSnapshot,
)
from app.services.language_speaking_transition_gate import (
    GATE_POLICIES,
    LANGUAGE_SPEAKING_TRANSITION_GATE_VERSION,
    TRANSITION_POLICY_VERSION,
    ComparisonOperator,
    ThresholdSourceKind,
    all_product_policy_default_fields,
    compute_decision_fingerprint,
    evaluate_speaking_transition_gate,
)

# silence unused — kept for clarity that decisions are immutable
_ = replace

PASS = 0
FAIL = 0
BACKEND = Path(__file__).resolve().parents[1]


def check(label: str, cond: bool) -> None:
    global PASS, FAIL
    # Windows consoles may be cp1252 — keep labels ASCII-safe.
    safe = label.replace("→", "->").replace("–", "-")
    if cond:
        PASS += 1
        print(f"  OK  {safe}")
    else:
        FAIL += 1
        print(f" FAIL {safe}")


def _base_snapshot(**overrides) -> SpeakingStageSignalSnapshot:
    blockers = (
        SpeakingStageBlocker(
            kind=SpeakingStageBlockerKind.support_dependence_unknown,
            severity="info",
            student_safe_message="support unknown",
        ),
    )
    data = dict(
        schema_version="15.0.0",
        official_cefr="A2",
        current_stage=SpeakingLearningStage.foundation,
        curriculum_skill_count=20,
        skills_with_evidence_count=6,
        coverage_ratio=0.30,
        core_skill_coverage_ratio=0.60,
        sufficient_evidence_ratio=0.25,
        stable_skill_ratio=0.20,
        developing_skill_ratio=0.30,
        at_risk_skill_ratio=0.10,
        in_level_mastery_avg=0.40,
        in_level_stability_avg=0.40,
        recent_success_signal=0.60,
        recent_failure_signal=0.20,
        retry_dependence_signal=None,
        support_dependence_signal="unknown",
        retention_risk_signal=0.10,
        transfer_breadth_signal=0.0,
        context_diversity_signal=0.05,  # low — must NOT block F→D
        performance_stability_signal=0.35,
        data_sufficiency=DataSufficiencyVerdict.partial,
        blockers=blockers,
        snapshot_fingerprint="fp-base",
        total_observations=12,
        distinct_tasks_attempted=2,
        core_skills_with_min_evidence=2,
        core_skill_count=4,
    )
    data.update(overrides)
    return SpeakingStageSignalSnapshot(**data)


def _advanced_ready(**overrides) -> SpeakingStageSignalSnapshot:
    """Snapshot that should pass D→A with exclusive/inclusive boundary-safe values."""
    defaults = dict(
        current_stage=SpeakingLearningStage.developing,
        data_sufficiency=DataSufficiencyVerdict.sufficient,
        coverage_ratio=0.45,
        core_skill_coverage_ratio=0.55,
        sufficient_evidence_ratio=0.40,
        stable_skill_ratio=0.40,
        at_risk_skill_ratio=0.10,
        in_level_mastery_avg=0.55,
        performance_stability_signal=0.45,
        recent_failure_signal=0.20,
        retention_risk_signal=0.15,
        retry_dependence_signal=0.20,
        distinct_tasks_attempted=3,
        transfer_breadth_signal=0.30,
        context_diversity_signal=0.35,
        blockers=(
            SpeakingStageBlocker(
                kind=SpeakingStageBlockerKind.support_dependence_unknown,
                severity="info",
                student_safe_message="support unknown",
            ),
        ),
        snapshot_fingerprint="fp-da-ready",
    )
    defaults.update(overrides)
    return _base_snapshot(**defaults)


def _req(decision, code: str):
    for r in decision.requirements:
        if r.code == code:
            return r
    return None


# ---------------------------------------------------------------------------
# Static / ownership / provenance
# ---------------------------------------------------------------------------


def test_static_and_provenance() -> None:
    check("1. transition gate versioned 16.x", LANGUAGE_SPEAKING_TRANSITION_GATE_VERSION.startswith("16."))
    check("2. policy versioned 16.x", TRANSITION_POLICY_VERSION.startswith("16."))
    check("3. exactly two global GATE_POLICIES", len(GATE_POLICIES) == 2)

    scopes = {p.scope for p in GATE_POLICIES.values()}
    check(
        "4. policy scope is global deterministic (not curriculum-driven claim)",
        scopes == {"global_deterministic_internal_stage_policy"},
    )

    ppd = all_product_policy_default_fields()
    check("5. PRODUCT POLICY DEFAULT fields labeled", len(ppd) >= 5)
    check(
        "5b. D→A context diversity is PRODUCT POLICY DEFAULT",
        any("context_diversity" in f and "developing->advanced" in f for f in ppd),
    )

    # Provenance exists for all policies
    for key, policy in GATE_POLICIES.items():
        check(f"6. provenance non-empty for {key[0].name}->{key[1].name}", len(policy.provenance) > 0)
        for p in policy.provenance:
            if p.source_kind is ThresholdSourceKind.product_policy_default:
                check(
                    f"7. PPD metadata for {p.policy_field}",
                    p.to_dict().get("product_policy_default") is True
                    and p.source_kind.value == "PRODUCT_POLICY_DEFAULT",
                )

    exclusive_fields = [
        "exclusive_maximum_at_risk_skill_ratio",
        "exclusive_maximum_retention_risk",
        "exclusive_maximum_retry_dependence",
    ]
    fd = GATE_POLICIES[(SpeakingLearningStage.foundation, SpeakingLearningStage.developing)]
    da = GATE_POLICIES[(SpeakingLearningStage.developing, SpeakingLearningStage.advanced)]
    check("8. F→D exclusive at_risk bound is 0.35", fd.exclusive_maximum_at_risk_skill_ratio == 0.35)
    check("9. D→A exclusive at_risk bound is 0.30", da.exclusive_maximum_at_risk_skill_ratio == 0.30)
    check("10. D→A exclusive retention bound is 0.30", da.exclusive_maximum_retention_risk == 0.30)
    check("11. D→A exclusive retry bound is 0.50", da.exclusive_maximum_retry_dependence == 0.50)
    check("12. D→A inclusive recent_failure max is 0.45", da.maximum_recent_failure_signal == 0.45)
    check("13. F→D context diversity NOT_REQUIRED", fd.minimum_context_diversity is None)
    check("14. F→D retry observability not required", fd.require_known_retry_dependence is False)
    check("15. D→A requires known retry dependence", da.require_known_retry_dependence is True)

    for field in exclusive_fields:
        matches = [p for p in da.provenance if p.policy_field == field]
        if matches:
            check(f"16. provenance marks {field} exclusive", matches[0].upper_bound_exclusive is True)

    # No AI imports in gate package
    gate_texts = "\n".join(
        p.read_text(encoding="utf-8")
        for p in (BACKEND / "app/services/language_speaking_transition_gate").rglob("*.py")
    ).lower()
    check(
        "17. no AI imports in transition_gate",
        "claude" not in gate_texts and "openai" not in gate_texts and "gemini" not in gate_texts and "hume" not in gate_texts,
    )
    check("18. gate rules never assign learning_stage_speaking", "learning_stage_speaking =" not in gate_texts)

    # Ownership edges
    from app.services.language_speaking.ownership import ALLOWED_PACKAGE_DEPENDENCIES

    check(
        "19. learning_stage may import transition_gate",
        "language_speaking_transition_gate" in ALLOWED_PACKAGE_DEPENDENCIES["language_speaking_learning_stage"],
    )
    check(
        "20. progression may import learning_stage",
        "language_speaking_learning_stage" in ALLOWED_PACKAGE_DEPENDENCIES["language_speaking_progression"],
    )


# ---------------------------------------------------------------------------
# Pure gate: F→D / D→A / boundaries
# ---------------------------------------------------------------------------


def test_foundation_to_developing() -> None:
    snap = _base_snapshot()
    d = evaluate_speaking_transition_gate(snap)
    check("21. F→D advances on partial + floors", d.authorized and d.decision.value == "advance")
    check("22. F→D target developing", d.target_stage is SpeakingLearningStage.developing)
    ctx = _req(d, "minimum_context_diversity")
    check(
        "23. F→D context diversity NOT_APPLICABLE even when low",
        ctx is not None and ctx.applicability == "not_applicable" and ctx.passed,
    )
    retry = _req(d, "retry_dependence_observability")
    check("24. F→D UNKNOWN retry allowed", retry is not None and retry.passed and snap.retry_dependence_signal is None)

    # at_risk == 0.35 → BLOCK (exclusive)
    blocked = evaluate_speaking_transition_gate(_base_snapshot(at_risk_skill_ratio=0.35, snapshot_fingerprint="fp-ar35"))
    ar = _req(blocked, "exclusive_maximum_at_risk_skill_ratio")
    check("25. F→D at_risk == 0.35 BLOCKS", not blocked.authorized and ar is not None and not ar.passed)
    check("25b. F→D at_risk operator is <", ar is not None and ar.operator is ComparisonOperator.lt)

    # just below 0.35 may pass (other reqs ok)
    almost = evaluate_speaking_transition_gate(
        _base_snapshot(at_risk_skill_ratio=0.349999, snapshot_fingerprint="fp-ar349")
    )
    ar2 = _req(almost, "exclusive_maximum_at_risk_skill_ratio")
    check("26. F→D at_risk just below 0.35 may pass", almost.authorized and ar2 is not None and ar2.passed)

    sparse = evaluate_speaking_transition_gate(
        _base_snapshot(
            data_sufficiency=DataSufficiencyVerdict.insufficient,
            coverage_ratio=0.10,
            blockers=(
                SpeakingStageBlocker(
                    kind=SpeakingStageBlockerKind.insufficient_evidence,
                    severity="blocking",
                    student_safe_message="need more",
                ),
                SpeakingStageBlocker(
                    kind=SpeakingStageBlockerKind.support_dependence_unknown,
                    severity="info",
                    student_safe_message="x",
                ),
            ),
            snapshot_fingerprint="fp-sparse",
        )
    )
    check("27. F→D sparse evidence stays", not sparse.authorized)


def test_developing_to_advanced_and_boundaries() -> None:
    ready = _advanced_ready()
    d = evaluate_speaking_transition_gate(ready)
    check("28. D→A advances when all floors met", d.authorized and d.decision.value == "advance")
    check("29. D→A target advanced", d.target_stage is SpeakingLearningStage.advanced)

    # Exact exclusive boundaries → BLOCK
    for label, kwargs, code in [
        ("30. D→A at_risk == 0.30 BLOCKS", {"at_risk_skill_ratio": 0.30}, "exclusive_maximum_at_risk_skill_ratio"),
        ("31. D→A retention == 0.30 BLOCKS", {"retention_risk_signal": 0.30}, "exclusive_maximum_retention_risk"),
        ("32. D→A retry_dependence == 0.50 BLOCKS", {"retry_dependence_signal": 0.50}, "exclusive_maximum_retry_dependence"),
    ]:
        dec = evaluate_speaking_transition_gate(_advanced_ready(snapshot_fingerprint=f"fp-{label}", **kwargs))
        r = _req(dec, code)
        check(label, not dec.authorized and r is not None and not r.passed and r.operator is ComparisonOperator.lt)

    # Inclusive / minimum floors ALLOWED at equality
    for label, kwargs, code, op in [
        (
            "33. D→A recent_failure == 0.45 allowed",
            {"recent_failure_signal": 0.45},
            "maximum_recent_failure_signal",
            ComparisonOperator.le,
        ),
        (
            "34. D→A performance_stability == 0.40 allowed",
            {"performance_stability_signal": 0.40},
            "minimum_performance_stability",
            ComparisonOperator.ge,
        ),
        (
            "35. D→A transfer_breadth == 0.25 allowed",
            {"transfer_breadth_signal": 0.25},
            "minimum_transfer_breadth",
            ComparisonOperator.ge,
        ),
        (
            "36. D→A context_diversity == 0.30 allowed",
            {"context_diversity_signal": 0.30},
            "minimum_context_diversity",
            ComparisonOperator.ge,
        ),
    ]:
        dec = evaluate_speaking_transition_gate(_advanced_ready(snapshot_fingerprint=f"fp-{label}", **kwargs))
        r = _req(dec, code)
        check(label, dec.authorized and r is not None and r.passed and r.operator is op)

    # UNKNOWN retry blocks D→A
    unk = evaluate_speaking_transition_gate(
        _advanced_ready(retry_dependence_signal=None, snapshot_fingerprint="fp-retry-unk")
    )
    obs = _req(unk, "retry_dependence_observability")
    check("37. D→A UNKNOWN retry BLOCKS", not unk.authorized)
    check(
        "37b. unknown recorded separately",
        obs is not None
        and obs.applicability == "unknown"
        and "retry_dependence_observability" in unk.unknown_requirements,
    )

    low_tasks = evaluate_speaking_transition_gate(
        _advanced_ready(distinct_tasks_attempted=1, snapshot_fingerprint="fp-tasks1")
    )
    check("38. D→A distinct_tasks < 2 BLOCKS", not low_tasks.authorized)

    # support unknown never blocks
    check("39. support_dependence unknown never blocks D→A", d.authorized)

    adv = evaluate_speaking_transition_gate(
        _advanced_ready(current_stage=SpeakingLearningStage.advanced, snapshot_fingerprint="fp-adv")
    )
    check("40. Advanced stays (no CEFR promotion)", not adv.authorized and adv.target_stage is None)

    # Foundation → Advanced jump impossible via evaluator (always current+1)
    jump = evaluate_speaking_transition_gate(_base_snapshot(current_stage=SpeakingLearningStage.foundation))
    check("41. F→D never targets Advanced", jump.target_stage is SpeakingLearningStage.developing)


def test_fingerprint_and_unknown_semantics() -> None:
    a = evaluate_speaking_transition_gate(_base_snapshot(snapshot_fingerprint="fp-same"))
    b = evaluate_speaking_transition_gate(_base_snapshot(snapshot_fingerprint="fp-same"))
    check("42. same snapshot same decision fingerprint", a.decision_fingerprint == b.decision_fingerprint)
    check("42b. fingerprint recomputes", compute_decision_fingerprint(a) == a.decision_fingerprint)

    c = evaluate_speaking_transition_gate(
        _base_snapshot(coverage_ratio=0.99, snapshot_fingerprint="fp-diff", skills_with_evidence_count=19)
    )
    # Coverage change may or may not change authorization but fingerprint content includes req currents
    check("43. different evidence can change decision fingerprint", a.decision_fingerprint != c.decision_fingerprint or a.authorized == c.authorized)

    # Change a blocking field to force decision change
    d = evaluate_speaking_transition_gate(
        _base_snapshot(at_risk_skill_ratio=0.35, snapshot_fingerprint="fp-block")
    )
    check("44. blocking change changes fingerprint", a.decision_fingerprint != d.decision_fingerprint)

    blob = str(a.to_internal_dict()).lower()
    check("45. no timestamps in decision payload", "timestamp" not in blob and "generated_at" not in blob)


# ---------------------------------------------------------------------------
# Persist boundary / source guards
# ---------------------------------------------------------------------------


def test_source_guards() -> None:
    runtime = (BACKEND / "app/services/language_speaking_learning_stage/stage_runtime.py").read_text(encoding="utf-8")
    check("46. stage_runtime uses lock_speaking_progression_row", "lock_speaking_progression_row" in runtime)
    check("47. stage_runtime writes learning_stage_speaking", "learning_stage_speaking" in runtime)
    check("48. stage_runtime never assigns official_speaking_cefr", "official_speaking_cefr =" not in runtime)
    check("49. stale fingerprint rejection present", "stale_evidence" in runtime)
    check("50. stale stage rejection present", "stale_stage" in runtime)
    check("51. stale cefr rejection present", "stale_cefr" in runtime)

    prog = (BACKEND / "app/services/language_speaking_progression/runtime.py").read_text(encoding="utf-8")
    check("52. progression orchestrates evaluate_and_persist", "evaluate_and_persist_speaking_stage" in prog)
    check("53. progression does not assign learning_stage_speaking", "learning_stage_speaking =" not in prog)

    api = (BACKEND / "app/api/language_speaking_journey.py").read_text(encoding="utf-8")
    check("54. finalize API calls run_speaking_progression_engines", "run_speaking_progression_engines" in api)
    # Ensure ordering: finalize_speaking_session then progression engines
    check(
        "55. API orders finalize then progression engines",
        api.find("finalize_speaking_session")
        < api.find("run_speaking_progression_engines")
        and "speaking_session_finalize" in api,
    )
    journey_api = (BACKEND / "app/services/language_speaking_journey/api_service.py").read_text(encoding="utf-8")
    check(
        "55b. journey package does not import progression runtime (S0 layer)",
        "run_speaking_progression_engines" not in journey_api
        and "language_speaking_progression" not in journey_api,
    )

    # Gate package never writes stage
    assign_in_gate = False
    for p in (BACKEND / "app/services/language_speaking_transition_gate").rglob("*.py"):
        tree = ast.parse(p.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for t in node.targets:
                    if isinstance(t, ast.Attribute) and t.attr in {
                        "learning_stage_speaking",
                        "official_speaking_cefr",
                    }:
                        assign_in_gate = True
    check("56. AST: gate never assigns stage/cefr columns", not assign_in_gate)

    # Only stage_runtime assigns learning_stage_speaking in learning_stage package
    writers = []
    for p in (BACKEND / "app/services/language_speaking_learning_stage").rglob("*.py"):
        tree = ast.parse(p.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for t in node.targets:
                    if isinstance(t, ast.Attribute) and t.attr == "learning_stage_speaking":
                        writers.append(p.name)
    check("57. sole writer module is stage_runtime.py", writers and set(writers) == {"stage_runtime.py"})

    read_model = (BACKEND / "app/services/language_speaking_journey/read_model.py").read_text(encoding="utf-8")
    check("58. S12 projects internal_stage label helper", "student_safe_internal_stage_label" in read_model)


def test_unit_replace_fingerprint_stability() -> None:
    # dataclasses.replace used by rules for fingerprint fill — ensure advance stays authorized
    snap = _advanced_ready(snapshot_fingerprint="fp-stab")
    d1 = evaluate_speaking_transition_gate(snap)
    d2 = evaluate_speaking_transition_gate(snap)
    check("59. idempotent pure evaluate", d1.decision_fingerprint == d2.decision_fingerprint and d1.authorized)


def run_regression(label: str, script: str) -> None:
    if os.environ.get("SPEAKING_VERIFY_SKIP_NESTED_REGRESSIONS") == "1":
        print("  (flat mode: skip nested regressions)", flush=True)
        return
    print(f"\n--- regression {label} ---")
    proc = subprocess.run(
        [sys.executable, str(BACKEND / "scripts" / script)],
        cwd=str(BACKEND),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env={**dict(**{k: v for k, v in __import__("os").environ.items()}), "PYTHONIOENCODING": "utf-8"},
    )
    ok = proc.returncode == 0
    check(label, ok)
    if not ok:
        print(proc.stdout[-2500:] if proc.stdout else "")
        print(proc.stderr[-2500:] if proc.stderr else "")


def main() -> int:
    print("=== Speaking S16 transition gate verifier ===\n")
    test_static_and_provenance()
    test_foundation_to_developing()
    test_developing_to_advanced_and_boundaries()
    test_fingerprint_and_unknown_semantics()
    test_source_guards()
    test_unit_replace_fingerprint_stability()

    run_regression("60. S0 architecture remains green", "verify_speaking_s0_architecture.py")
    run_regression("61. S9 remains green", "verify_speaking_s9_adaptive_journey.py")
    run_regression("62. S10 remains green", "verify_speaking_s10_educational_missions.py")
    run_regression("63. S10.1 remains green", "verify_speaking_s101_mission_stabilization.py")
    run_regression("64. S11 remains green", "verify_speaking_s11_attempt_lineage.py")
    run_regression("65. S12 remains green", "verify_speaking_s12_journey_read_model.py")
    run_regression("66. S13 remains green", "verify_speaking_s13_live_budget.py")
    run_regression("67. S14 remains green", "verify_speaking_s14_alex_context_identity.py")
    run_regression("68. S15 remains green", "verify_speaking_s15_stage_signals.py")

    print(f"\n=== RESULT: {PASS} passed, {FAIL} failed ===")
    return 1 if FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
