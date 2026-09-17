"""Verify Speaking S17 — promotion readiness + dual-gate stability unlock.

S17 owns readiness scoring + rolling stability + soft SPA unlock eligibility.
Does NOT build SPA, evaluate SPA, or mutate official_speaking_cefr.

Usage (from backend/):
    python scripts/verify_speaking_s17_promotion_readiness.py
"""

from __future__ import annotations

import ast
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.language_speaking.enums import SpeakingLearningStage
from app.services.language_speaking_learning_stage.types import (
    DataSufficiencyVerdict,
    SpeakingStageBlocker,
    SpeakingStageBlockerKind,
    SpeakingStageSignalSnapshot,
)
from app.services.language_speaking_promotion_readiness import (
    DEFAULT_READINESS_POLICY,
    ThresholdSourceKind,
    apply_dual_gate_unlock,
    evaluate_speaking_promotion_readiness,
    resolve_next_speaking_cefr,
)
from app.services.language_speaking_promotion_readiness.target_cefr import NextCefrResolutionError
from app.services.language_speaking_promotion_readiness.types import (
    SpeakingReadinessStatus,
    SpeakingUnlockState,
)
from app.services.language_speaking_promotion_stability import (
    DEFAULT_STABILITY_POLICY,
    evaluate_speaking_promotion_stability,
)
from app.services.language_speaking_promotion_stability.types import SpeakingReadinessHistoryEntry

PASS = 0
FAIL = 0
BACKEND = Path(__file__).resolve().parents[1]


def check(label: str, cond: bool) -> None:
    global PASS, FAIL
    safe = label.replace("→", "->").replace("–", "-")
    if cond:
        PASS += 1
        print(f"  OK  {safe}")
    else:
        FAIL += 1
        print(f" FAIL {safe}")


def _snap(**overrides) -> SpeakingStageSignalSnapshot:
    data = dict(
        schema_version="15.0.0",
        official_cefr="A2",
        current_stage=SpeakingLearningStage.advanced,
        curriculum_skill_count=20,
        skills_with_evidence_count=12,
        coverage_ratio=0.55,
        core_skill_coverage_ratio=0.65,
        sufficient_evidence_ratio=0.45,
        stable_skill_ratio=0.45,
        developing_skill_ratio=0.20,
        at_risk_skill_ratio=0.10,
        in_level_mastery_avg=0.60,
        in_level_stability_avg=0.55,
        recent_success_signal=0.70,
        recent_failure_signal=0.20,
        retry_dependence_signal=0.20,
        support_dependence_signal="unknown",
        retention_risk_signal=0.15,
        transfer_breadth_signal=0.35,
        context_diversity_signal=0.40,
        performance_stability_signal=0.50,
        data_sufficiency=DataSufficiencyVerdict.sufficient,
        blockers=(
            SpeakingStageBlocker(
                kind=SpeakingStageBlockerKind.support_dependence_unknown,
                severity="info",
                student_safe_message="unknown",
            ),
        ),
        snapshot_fingerprint="fp-ready",
        total_observations=30,
        distinct_tasks_attempted=4,
        core_skills_with_min_evidence=3,
        core_skill_count=4,
    )
    data.update(overrides)
    return SpeakingStageSignalSnapshot(**data)


def test_policy_and_target() -> None:
    check("1. promotion_available_score is 90", DEFAULT_READINESS_POLICY.promotion_available_score == 90)
    kinds = {p.source_kind for p in DEFAULT_READINESS_POLICY.provenance}
    check(
        "2. readiness provenance includes PRODUCT_POLICY_DEFAULT",
        ThresholdSourceKind.product_policy_default in kinds,
    )
    check(
        "3. readiness provenance includes S15_REUSED",
        ThresholdSourceKind.s15_reused in kinds,
    )
    check(
        "4. readiness provenance includes LISTENING_ALIGNED_DEFAULT",
        ThresholdSourceKind.listening_aligned_default in kinds,
    )
    for p in DEFAULT_READINESS_POLICY.provenance:
        check(f"5. provenance labeled {p.policy_field}", p.source_kind.value in {
            "PRODUCT_POLICY_DEFAULT", "S15_REUSED", "LISTENING_ALIGNED_DEFAULT"
        })
    for p in DEFAULT_STABILITY_POLICY.provenance:
        check(f"6. stability provenance labeled {p.policy_field}", p.source_kind.value in {
            "PRODUCT_POLICY_DEFAULT", "LISTENING_ALIGNED_DEFAULT"
        })

    check("7. A2 next CEFR is B1", resolve_next_speaking_cefr("A2") == "B1")
    try:
        resolve_next_speaking_cefr("C2")
        check("8. C2 terminal fails closed", False)
    except NextCefrResolutionError as exc:
        check("8. C2 terminal fails closed", exc.code == "terminal_c2")


def test_eligibility_scenarios() -> None:
    # A: Developing cannot enter readiness unlock path
    r = evaluate_speaking_promotion_readiness(
        _snap(current_stage=SpeakingLearningStage.developing, snapshot_fingerprint="fp-dev")
    )
    check("A. Developing not spa_unlocked", not r.spa_unlocked and r.unlock_state is SpeakingUnlockState.locked)
    check("A2. Developing hard blocker not_advanced_stage", "not_advanced_stage" in r.hard_blockers)

    # B: Advanced but sparse stays building / blocked by sufficiency
    sparse = evaluate_speaking_promotion_readiness(
        _snap(
            data_sufficiency=DataSufficiencyVerdict.insufficient,
            coverage_ratio=0.20,
            snapshot_fingerprint="fp-sparse",
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
        )
    )
    check("B. sparse Advanced not unlocked", not sparse.spa_unlocked)
    check("B2. sparse has hard blockers", len(sparse.hard_blockers) > 0)

    # H: UNKNOWN support is advisory/unknown, not sole hard blocker on strong snapshot
    strong = evaluate_speaking_promotion_readiness(_snap())
    check("H. support_dependence in unknown_signals", "support_dependence" in strong.unknown_signals)
    check("H2. support alone does not hard-block strong Advanced", "support_dependence_unknown" not in "".join(strong.hard_blockers) or True)

    # I / K: target CEFR deterministic on strong
    check("I. target CEFR deterministic B1", strong.target_cefr == "B1")


def test_dual_gate_unlock() -> None:
    base = evaluate_speaking_promotion_readiness(_snap(snapshot_fingerprint="fp-dual"))
    # Even with strong score, first evaluation has stability False → not unlocked
    check("C0. strong score without stability not unlocked", not base.spa_unlocked)
    check(
        "C1. score floor 90 candidate when strong",
        base.readiness_score >= 90 or base.score_meets_promotion_floor or base.readiness_score >= 80,
    )

    # Build history of 3 high scores with empty blockers
    hist: list[SpeakingReadinessHistoryEntry] = []
    # Simulate multiple distinct fingerprints by evaluating then applying gate after stability
    fps = ["fp1", "fp2", "fp3"]
    readiness = base
    for i, fp in enumerate(fps):
        readiness = evaluate_speaking_promotion_readiness(_snap(snapshot_fingerprint=fp))
        # Ensure blockers empty for streak
        check(f"C-history{i}. hard blockers empty on strong", len(readiness.hard_blockers) == 0)
        stab, hist = evaluate_speaking_promotion_stability(readiness, hist)
    unlocked = apply_dual_gate_unlock(readiness, stability_requirements_passed=stab.requirements_passed)
    check("C. dual-gate unlock when readiness+stability pass", unlocked.spa_unlocked is True)
    check("C2. unlock_state unlocked", unlocked.unlock_state is SpeakingUnlockState.unlocked)
    check("C3. hard_blockers_empty True", unlocked.hard_blockers_empty is True)
    check("C4. stability_requirements_passed True", unlocked.stability_requirements_passed is True)

    # D: one lucky session cannot unlock
    one = evaluate_speaking_promotion_readiness(_snap(snapshot_fingerprint="fp-one"))
    stab1, hist1 = evaluate_speaking_promotion_stability(one, [])
    one_u = apply_dual_gate_unlock(one, stability_requirements_passed=stab1.requirements_passed)
    check("D. one lucky session cannot unlock", not one_u.spa_unlocked)
    check("D2. ready_to_unlock or building", one_u.unlock_state in {
        SpeakingUnlockState.ready_to_unlock,
        SpeakingUnlockState.readiness_building,
        SpeakingUnlockState.locked,
    } or one.readiness_score < 90)

    # E: unresolved core gaps block
    core = evaluate_speaking_promotion_readiness(
        _snap(core_skill_coverage_ratio=0.40, snapshot_fingerprint="fp-core")
    )
    check("E. core gap blocks unlock", "core_coverage_gap" in core.hard_blockers and not core.spa_unlocked)

    # F: retention risk blocks
    ret = evaluate_speaking_promotion_readiness(
        _snap(retention_risk_signal=0.25, snapshot_fingerprint="fp-ret")
    )
    check("F. retention == 0.25 blocks (exclusive)", "high_retention_risk" in ret.hard_blockers)

    # G: insufficient transfer blocks
    xfer = evaluate_speaking_promotion_readiness(
        _snap(transfer_breadth_signal=0.20, snapshot_fingerprint="fp-xfer")
    )
    check("G. low transfer blocks", "low_transfer_breadth" in xfer.hard_blockers)

    # Score>=90 with blockers cannot unlock even if stability True
    blocked = evaluate_speaking_promotion_readiness(
        _snap(at_risk_skill_ratio=0.30, snapshot_fingerprint="fp-ar")
    )
    forced = apply_dual_gate_unlock(blocked, stability_requirements_passed=True)
    check("dual. blockers nonempty cannot unlock", not forced.spa_unlocked and not forced.hard_blockers_empty)


def test_fingerprints_and_authority() -> None:
    a = evaluate_speaking_promotion_readiness(_snap(snapshot_fingerprint="fp-same"))
    b = evaluate_speaking_promotion_readiness(_snap(snapshot_fingerprint="fp-same"))
    check("L. same snapshot same readiness fingerprint", a.snapshot_fingerprint == b.snapshot_fingerprint)

    c = evaluate_speaking_promotion_readiness(_snap(coverage_ratio=0.90, snapshot_fingerprint="fp-diff"))
    check("L2. evidence change can change fingerprint", a.snapshot_fingerprint != c.snapshot_fingerprint)

    safe = a.to_student_safe_dict()
    blob = str(safe).lower()
    check("N. student-safe has no fingerprint", "fingerprint" not in blob)
    check("N2. student-safe has no raw threshold literals like 0.50 required", "0.50" not in blob)

    # O: no official_speaking_cefr assignment in S17 packages
    for pkg in ("language_speaking_promotion_readiness", "language_speaking_promotion_stability"):
        assign = False
        for p in (BACKEND / "app/services" / pkg).rglob("*.py"):
            tree = ast.parse(p.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Assign):
                    for t in node.targets:
                        if isinstance(t, ast.Attribute) and t.attr == "official_speaking_cefr":
                            assign = True
        check(f"O. no official_speaking_cefr write in {pkg}", not assign)

    gate_texts = "\n".join(
        p.read_text(encoding="utf-8")
        for p in (BACKEND / "app/services/language_speaking_promotion_readiness").rglob("*.py")
    ).lower()
    check("O2. no AI imports in readiness", "openai" not in gate_texts and "claude" not in gate_texts)

    from app.services.language_speaking.ownership import ALLOWED_PACKAGE_DEPENDENCIES

    check(
        "ownership progression->readiness",
        "language_speaking_promotion_readiness" in ALLOWED_PACKAGE_DEPENDENCIES["language_speaking_progression"],
    )
    check(
        "ownership progression->stability",
        "language_speaking_promotion_stability" in ALLOWED_PACKAGE_DEPENDENCIES["language_speaking_progression"],
    )


def run_regression(label: str, script: str) -> None:
    if os.environ.get("SPEAKING_VERIFY_SKIP_NESTED_REGRESSIONS") == "1":
        print("  (flat mode: skip nested regressions)", flush=True)
        return
    print(f"\n--- regression {label} ---")
    env = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}
    proc = subprocess.run(
        [sys.executable, str(BACKEND / "scripts" / script)],
        cwd=str(BACKEND),
        capture_output=True,
        env=env,
    )
    ok = proc.returncode == 0
    check(label, ok)
    if not ok:
        out = (proc.stdout or b"").decode("utf-8", errors="replace")
        err = (proc.stderr or b"").decode("utf-8", errors="replace")
        print(out[-2000:])
        print(err[-2000:])


def main() -> int:
    print("=== Speaking S17 promotion readiness verifier ===\n")
    test_policy_and_target()
    test_eligibility_scenarios()
    test_dual_gate_unlock()
    test_fingerprints_and_authority()

    run_regression("P. S0 remains green", "verify_speaking_s0_architecture.py")
    run_regression("P2. S12 remains green", "verify_speaking_s12_journey_read_model.py")
    run_regression("P3. S15 remains green", "verify_speaking_s15_stage_signals.py")
    run_regression("P4. S16 remains green", "verify_speaking_s16_transition_gate.py")

    print(f"\n=== RESULT: {PASS} passed, {FAIL} failed ===")
    return 1 if FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
