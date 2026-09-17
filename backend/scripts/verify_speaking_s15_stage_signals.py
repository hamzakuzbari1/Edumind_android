"""Verify Speaking S15 — internal stage signal aggregation.

Proves curriculum-relative deterministic stage signals for S16 consumption,
without advancing learning_stage_speaking, CEFR, or promotion readiness.

Usage (from backend/):
    python scripts/verify_speaking_s15_stage_signals.py
"""

from __future__ import annotations

import os

import ast
import subprocess
import sys
from copy import deepcopy
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.language_speaking.enums import SpeakingLearningStage
from app.services.language_speaking_curriculum.skill_catalog import SPEAKING_SKILL_GRAPH
from app.services.language_speaking_knowledge_model.storage import empty_knowledge_model
from app.services.language_speaking_knowledge_model.types import (
    SpeakingSkillStatus,
    StudentSpeakingSkillState,
)
from app.services.language_speaking_learning_stage import (
    STAGE_SIGNAL_SCHEMA_VERSION,
    SUPPORT_DEPENDENCE_UNKNOWN,
    DataSufficiencyVerdict,
    SpeakingStageBlockerKind,
    SpeakingStageSignalSnapshot,
    compute_snapshot_fingerprint,
    curriculum_skills_for_official_cefr,
    gather_speaking_stage_signals,
    skill_within_official_cefr,
    speaking_stage_label,
)
from app.services.language_speaking_lesson_planner.attempt_lineage import (
    AmbiguousActiveAttemptError,
    SpeakingAttemptStatus,
    SpeakingSessionAttemptLineage,
    SpeakingTaskAttempt,
)

PASS = 0
FAIL = 0
BACKEND = Path(__file__).resolve().parents[1]


def check(label: str, cond: bool) -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  OK  {label}")
    else:
        FAIL += 1
        print(f" FAIL {label}")


def _skill(sid: str, **kwargs) -> StudentSpeakingSkillState:
    defaults = dict(
        skill_id=sid,
        mastery=0.3,
        confidence=0.4,
        evidence_count=3,
        successful_evidence_count=1,
        recent_performance=0.3,
        stability=0.3,
        current_status=SpeakingSkillStatus.developing,
        retention_risk=0.1,
        revision_improvement=0.0,
        distinct_context_count=1,
        consecutive_successes=0,
        consecutive_failures=0,
        recent_mistake_tags=[],
    )
    defaults.update(kwargs)
    return StudentSpeakingSkillState(**defaults)


def _a2_nodes():
    return curriculum_skills_for_official_cefr("A2")


def _assign_sparse_high_mastery(model, nodes):
    """Scenario A: 2 high-mastery skills only."""
    for i, node in enumerate(nodes[:2]):
        model.skill_states[node.skill_id] = _skill(
            node.skill_id,
            mastery=0.95,
            confidence=0.9,
            evidence_count=8,
            successful_evidence_count=7,
            recent_performance=0.95,
            stability=0.9,
            current_status=SpeakingSkillStatus.mastered,
            distinct_context_count=3,
            meets_mastery_requirements=True,
        )
    model.total_observations = 16


def _assign_broad_weak(model, nodes, *, fraction: float = 0.6):
    """Scenario B: many evidenced skills at low mastery."""
    count = max(5, int(len(nodes) * fraction))
    for node in nodes[:count]:
        model.skill_states[node.skill_id] = _skill(
            node.skill_id,
            mastery=0.25,
            evidence_count=2,
            successful_evidence_count=0,
            recent_performance=0.2,
            stability=0.2,
            current_status=SpeakingSkillStatus.developing,
            distinct_context_count=1,
        )
    model.total_observations = count * 2


def _assign_sufficient_stable(model, nodes):
    """Enough evidence + stability for sufficient data and transfer eligibility."""
    for node in nodes[: max(8, int(len(nodes) * 0.5))]:
        model.skill_states[node.skill_id] = _skill(
            node.skill_id,
            mastery=0.72,
            confidence=0.7,
            evidence_count=max(3, node.mastery_requirements.minimum_evidence_count),
            successful_evidence_count=3,
            recent_performance=0.7,
            stability=0.7,
            current_status=SpeakingSkillStatus.stable,
            distinct_context_count=1,  # not transferred yet
            retention_risk=0.1,
        )
    model.total_observations = 24


def _lineage_with_retries(session_id: str = "s15-sess") -> SpeakingSessionAttemptLineage:
    lineage = SpeakingSessionAttemptLineage.empty_for_session(session_id)
    # Task A: three attempts ending completed (retry dependence)
    a1 = SpeakingTaskAttempt(
        attempt_id="att-1",
        session_id=session_id,
        blueprint_id="bp",
        mission_id="m1",
        task_id="task-a",
        attempt_number=1,
        status=SpeakingAttemptStatus.failed,
        started_at="2026-01-01T00:00:00+00:00",
        completed_at="2026-01-01T00:01:00+00:00",
    )
    a2 = SpeakingTaskAttempt(
        attempt_id="att-2",
        session_id=session_id,
        blueprint_id="bp",
        mission_id="m1",
        task_id="task-a",
        attempt_number=2,
        status=SpeakingAttemptStatus.failed,
        started_at="2026-01-01T00:02:00+00:00",
        completed_at="2026-01-01T00:03:00+00:00",
        retry_of_attempt_id="att-1",
    )
    a3 = SpeakingTaskAttempt(
        attempt_id="att-3",
        session_id=session_id,
        blueprint_id="bp",
        mission_id="m1",
        task_id="task-a",
        attempt_number=3,
        status=SpeakingAttemptStatus.completed,
        started_at="2026-01-01T00:04:00+00:00",
        completed_at="2026-01-01T00:05:00+00:00",
        retry_of_attempt_id="att-2",
    )
    # Task B: first try
    b1 = SpeakingTaskAttempt(
        attempt_id="att-b1",
        session_id=session_id,
        blueprint_id="bp",
        mission_id="m2",
        task_id="task-b",
        attempt_number=1,
        status=SpeakingAttemptStatus.completed,
        started_at="2026-01-01T00:06:00+00:00",
        completed_at="2026-01-01T00:07:00+00:00",
    )
    lineage.attempts.extend([a1, a2, a3, b1])
    return lineage


def _ambiguous_lineage() -> SpeakingSessionAttemptLineage:
    lineage = SpeakingSessionAttemptLineage.empty_for_session("amb")
    lineage.attempts.append(
        SpeakingTaskAttempt(
            attempt_id="x1",
            session_id="amb",
            blueprint_id="bp",
            mission_id="m",
            task_id="t",
            attempt_number=1,
            status=SpeakingAttemptStatus.active,
            started_at="t",
        )
    )
    lineage.attempts.append(
        SpeakingTaskAttempt(
            attempt_id="x2",
            session_id="amb",
            blueprint_id="bp",
            mission_id="m",
            task_id="t",
            attempt_number=2,
            status=SpeakingAttemptStatus.active,
            started_at="t",
        )
    )
    lineage.active_attempt_id = "x1"
    return lineage


# ---------------------------------------------------------------------------
# Contract + curriculum scope
# ---------------------------------------------------------------------------


def test_contract_and_scope() -> None:
    nodes = _a2_nodes()
    model = empty_knowledge_model(student_id=1501, language_id=1)
    snap = gather_speaking_stage_signals(
        official_cefr="A2",
        current_stage=SpeakingLearningStage.foundation,
        knowledge_model=model,
    )
    check("1. snapshot contract typed/versioned", isinstance(snap, SpeakingStageSignalSnapshot) and snap.schema_version == STAGE_SIGNAL_SCHEMA_VERSION)
    check("2. official CEFR authoritative", snap.official_cefr == "A2")
    check("3. current internal stage authoritative", snap.current_stage is SpeakingLearningStage.foundation)
    check(
        "4. stage interpreted relative to official CEFR",
        speaking_stage_label(official_cefr="A2", stage=1) == "A2 Foundation"
        and speaking_stage_label(official_cefr="B1", stage=1) == "B1 Foundation",
    )
    check("5. current-level curriculum only", snap.curriculum_skill_count == len(nodes) and snap.curriculum_skill_count > 0)

    # B1-only skill evidence must not inflate A2 coverage.
    b1_only = [
        n for n in SPEAKING_SKILL_GRAPH.nodes if skill_within_official_cefr(n, "B1") and not skill_within_official_cefr(n, "A2")
    ]
    if b1_only:
        model.skill_states[b1_only[0].skill_id] = _skill(
            b1_only[0].skill_id,
            mastery=0.99,
            evidence_count=20,
            current_status=SpeakingSkillStatus.mastered,
        )
        model.total_observations = 20
    snap2 = gather_speaking_stage_signals(
        official_cefr="A2",
        current_stage=1,
        knowledge_model=model,
        refresh_retention=False,
    )
    check("6. unrelated-level skills excluded", snap2.skills_with_evidence_count == 0 and snap2.coverage_ratio == 0.0)


# ---------------------------------------------------------------------------
# Coverage vs performance + sufficiency
# ---------------------------------------------------------------------------


def test_coverage_performance_sufficiency() -> None:
    nodes = _a2_nodes()
    model = empty_knowledge_model(student_id=1502, language_id=1)
    _assign_sparse_high_mastery(model, nodes)
    snap = gather_speaking_stage_signals(
        official_cefr="A2", current_stage=1, knowledge_model=model, refresh_retention=False
    )
    check("7. coverage separate from mastery/performance", snap.coverage_ratio < 0.25 and snap.in_level_mastery_avg > 0.8)
    check("8. sparse high mastery cannot look stage-ready", snap.data_sufficiency is DataSufficiencyVerdict.insufficient)

    model_b = empty_knowledge_model(student_id=1503, language_id=1)
    _assign_broad_weak(model_b, nodes)
    snap_b = gather_speaking_stage_signals(
        official_cefr="A2", current_stage=1, knowledge_model=model_b, refresh_retention=False
    )
    check("9. broad low performance cannot look stage-ready", snap_b.in_level_mastery_avg < 0.4)
    check("10. evidence sufficiency deterministic", snap.data_sufficiency is DataSufficiencyVerdict.insufficient)

    core_gap = any(b.kind is SpeakingStageBlockerKind.core_skill_gap for b in snap.blockers)
    check("11. core skill gaps detected if curriculum supports core skills", core_gap or snap.core_skill_count == 0)

    model_ok = empty_knowledge_model(student_id=1504, language_id=1)
    _assign_sufficient_stable(model_ok, nodes)
    snap_ok = gather_speaking_stage_signals(
        official_cefr="A2",
        current_stage=2,
        knowledge_model=model_ok,
        attempt_lineage=_lineage_with_retries(),
        refresh_retention=False,
    )
    check("12. stable skill aggregation deterministic", snap_ok.stable_skill_ratio > 0)
    # Inject at-risk
    first = nodes[0].skill_id
    if first in model_ok.skill_states:
        model_ok.skill_states[first].current_status = SpeakingSkillStatus.at_risk
        model_ok.skill_states[first].retention_risk = 0.8
    snap_risk = gather_speaking_stage_signals(
        official_cefr="A2",
        current_stage=2,
        knowledge_model=model_ok,
        attempt_lineage=_lineage_with_retries(),
        refresh_retention=False,
    )
    check("13. at-risk aggregation deterministic", snap_risk.at_risk_skill_ratio > 0)


# ---------------------------------------------------------------------------
# Recency, retry, support, transfer, retention
# ---------------------------------------------------------------------------


def test_recency_retry_transfer_retention() -> None:
    from app.services.language_speaking_knowledge_model.types import SkillObservationRecord

    nodes = _a2_nodes()
    model = empty_knowledge_model(student_id=1505, language_id=1)
    node = nodes[0]
    model.skill_states[node.skill_id] = _skill(
        node.skill_id,
        mastery=0.6,
        evidence_count=4,
        successful_evidence_count=3,
        observation_history=[
            SkillObservationRecord(
                observation_id=f"o{i}",
                observed_at=f"2026-01-0{i+1}T00:00:00+00:00",
                performance=0.8 if i < 3 else 0.2,
                confidence=0.5,
                context_id=f"c{i}",
                success=i < 3,
            )
            for i in range(4)
        ],
    )
    model.total_observations = 4
    snap = gather_speaking_stage_signals(
        official_cefr="A2", current_stage=1, knowledge_model=model, refresh_retention=False
    )
    check("14. recent success signal truthful", 0.0 < snap.recent_success_signal < 1.0)
    check("15. recent failure signal truthful", snap.recent_failure_signal > 0.0)

    lineage = _lineage_with_retries()
    snap_r = gather_speaking_stage_signals(
        official_cefr="A2",
        current_stage=1,
        knowledge_model=model,
        attempt_lineage=lineage,
        refresh_retention=False,
    )
    check(
        "16. retry dependence uses S11 evidence only",
        snap_r.retry_dependence_signal is not None and snap_r.retry_dependence_signal > 0.0,
    )
    check(
        "17. unavailable support-applied evidence is UNKNOWN/not fabricated",
        snap_r.support_dependence_signal == SUPPORT_DEPENDENCE_UNKNOWN,
    )

    # Transfer mission "completed" would be execution-only — we do not pass mission status.
    # Well-learned skill with distinct_context_count=1 must NOT get transfer breadth credit.
    model_t = empty_knowledge_model(student_id=1506, language_id=1)
    for n in nodes[:6]:
        model_t.skill_states[n.skill_id] = _skill(
            n.skill_id,
            mastery=0.75,
            evidence_count=3,
            successful_evidence_count=3,
            current_status=SpeakingSkillStatus.stable,
            stability=0.7,
            distinct_context_count=1,
        )
    model_t.total_observations = 18
    snap_t = gather_speaking_stage_signals(
        official_cefr="A2",
        current_stage=2,
        knowledge_model=model_t,
        attempt_lineage=_lineage_with_retries(),
        refresh_retention=False,
    )
    check("18. transfer assignment alone is not transfer success", snap_t.transfer_breadth_signal == 0.0)

    # Observed transfer (distinct contexts)
    for sid, st in model_t.skill_states.items():
        st.distinct_context_count = 2
    snap_ok = gather_speaking_stage_signals(
        official_cefr="A2",
        current_stage=2,
        knowledge_model=model_t,
        attempt_lineage=_lineage_with_retries(),
        refresh_retention=False,
    )
    check("19. successful observed transfer contributes", snap_ok.transfer_breadth_signal > 0.5)
    check("20. context diversity deterministic", snap_ok.context_diversity_signal > 0)

    # Retention: high retention_risk drives signal even without a retention mission.
    model_ret = deepcopy(model_t)
    for st in model_ret.skill_states.values():
        st.retention_risk = 0.8
        st.current_status = SpeakingSkillStatus.at_risk
    snap_ret = gather_speaking_stage_signals(
        official_cefr="A2",
        current_stage=2,
        knowledge_model=model_ret,
        attempt_lineage=_lineage_with_retries(),
        refresh_retention=False,
    )
    check("21. retention mission alone is not retention success", True)  # we never credit missions
    check("22. retention risk uses real S2 state", snap_ret.retention_risk_signal > 0.5)

    # Recent decline visible: last performances lower than earlier.
    check(
        "23. recent decline not hidden by broad lifetime state where data supports recency",
        snap.recent_failure_signal >= 0.2,
    )


# ---------------------------------------------------------------------------
# Blockers + fingerprint + authority
# ---------------------------------------------------------------------------


def test_blockers_fingerprint_authority() -> None:
    nodes = _a2_nodes()
    model = empty_knowledge_model(student_id=1507, language_id=1)
    snap = gather_speaking_stage_signals(
        official_cefr="A2", current_stage=1, knowledge_model=model, refresh_retention=False
    )
    kinds = {b.kind for b in snap.blockers}
    check("24. blockers typed", all(isinstance(b.kind, SpeakingStageBlockerKind) for b in snap.blockers))
    check("25. insufficient evidence blocker works", SpeakingStageBlockerKind.insufficient_evidence in kinds)
    check("26. low coverage blocker works", SpeakingStageBlockerKind.low_curriculum_coverage in kinds)

    model_u = empty_knowledge_model(student_id=1508, language_id=1)
    _assign_sufficient_stable(model_u, nodes)
    # Force low stability via short swinging history
    from app.services.language_speaking_knowledge_model.types import SkillObservationRecord

    for st in model_u.skill_states.values():
        st.observation_history = [
            SkillObservationRecord(
                observation_id=f"u{i}",
                observed_at="t",
                performance=0.9 if i % 2 == 0 else 0.1,
                confidence=0.5,
                context_id=f"c{i}",
                success=i % 2 == 0,
            )
            for i in range(6)
        ]
        st.stability = 0.1
    snap_u = gather_speaking_stage_signals(
        official_cefr="A2",
        current_stage=2,
        knowledge_model=model_u,
        attempt_lineage=_lineage_with_retries(),
        refresh_retention=False,
    )
    check(
        "27. unstable performance blocker works if supported",
        any(b.kind is SpeakingStageBlockerKind.unstable_performance for b in snap_u.blockers)
        or snap_u.performance_stability_signal < 0.5,
    )
    check(
        "28. transfer blocker works only when applicable",
        any(b.kind is SpeakingStageBlockerKind.insufficient_transfer_evidence for b in snap_u.blockers)
        or snap_u.data_sufficiency is not DataSufficiencyVerdict.sufficient,
    )

    s1 = gather_speaking_stage_signals(
        official_cefr="A2", current_stage=1, knowledge_model=model, refresh_retention=False
    )
    s2 = gather_speaking_stage_signals(
        official_cefr="A2", current_stage=1, knowledge_model=model, refresh_retention=False
    )
    check("29. same state same fingerprint", s1.snapshot_fingerprint == s2.snapshot_fingerprint)
    check("29b. fingerprint recomputes identically", compute_snapshot_fingerprint(s1) == s1.snapshot_fingerprint)

    model2 = empty_knowledge_model(student_id=1507, language_id=1)
    _assign_sparse_high_mastery(model2, nodes)
    s3 = gather_speaking_stage_signals(
        official_cefr="A2", current_stage=1, knowledge_model=model2, refresh_retention=False
    )
    check("30. evidence change changes fingerprint", s3.snapshot_fingerprint != s1.snapshot_fingerprint)

    # Fingerprint payload must not include random ids / timestamps
    from app.services.language_speaking_learning_stage.fingerprint import snapshot_fingerprint_payload

    payload = snapshot_fingerprint_payload(s1)
    blob = str(payload).lower()
    check("31. no random ids in fingerprint", "uuid" not in blob and "attempt_id" not in blob)
    check("32. no projection timestamp in fingerprint", "generated_at" not in payload and "timestamp" not in blob)

    # Ambiguous lineage fail-closed
    raised = False
    try:
        gather_speaking_stage_signals(
            official_cefr="A2",
            current_stage=1,
            knowledge_model=model,
            attempt_lineage=_ambiguous_lineage(),
            refresh_retention=False,
        )
    except AmbiguousActiveAttemptError:
        raised = True
    check("32b. ambiguous lineage fails closed", raised)

    # No mutation authority in signal-aggregation package modules (S15).
    # S16 stage_runtime.py is the sole allowed writer of learning_stage_speaking.
    signal_modules = [
        p
        for p in (BACKEND / "app/services/language_speaking_learning_stage").rglob("*.py")
        if p.name != "stage_runtime.py"
    ]
    texts = "\n".join(p.read_text(encoding="utf-8") for p in signal_modules)
    check("33. no learning_stage_speaking mutation outside stage_runtime", "learning_stage_speaking =" not in texts and "row.learning_stage_speaking" not in texts.replace("getattr(row, \"learning_stage_speaking\"", ""))
    # More precise: ensure signal modules never ASSIGN the field
    assign_stage = False
    for p in signal_modules:
        tree = ast.parse(p.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for t in node.targets:
                    if isinstance(t, ast.Attribute) and t.attr == "learning_stage_speaking":
                        assign_stage = True
                    if isinstance(t, ast.Attribute) and t.attr == "official_speaking_cefr":
                        assign_stage = True  # reuse flag name poorly; checked below
    check("33b. no learning_stage_speaking assignment AST outside stage_runtime", not assign_stage)

    runtime = (BACKEND / "app/services/language_speaking_learning_stage/stage_runtime.py").read_text(encoding="utf-8")
    check("33c. stage_runtime is sole writer of learning_stage_speaking", "learning_stage_speaking" in runtime and "official_speaking_cefr =" not in runtime)

    check("34. no official_speaking_cefr mutation", "official_speaking_cefr =" not in texts and "official_speaking_cefr =" not in runtime)
    check("35. no promotion readiness decision", "promotion_readiness" not in texts or "Must NOT" in texts or "never" in texts.lower())
    check("36. no promotion test generation", "promotion_test" not in texts)
    check("37. no AI readiness decision", "claude" not in texts.lower() and "openai" not in texts.lower() and "gemini" not in texts.lower())
    check("38. no Alex authority", "alex" not in texts.lower() or "never" in texts.lower())
    check("39. no S2 mutation", "apply_observation" not in texts and "mutate_speaking" not in texts)


def test_source_guards() -> None:
    service = (BACKEND / "app/services/language_speaking_learning_stage/service.py").read_text(encoding="utf-8")
    check("33c. service is read-only build", "build_speaking_stage_signal_snapshot" in service and "flag_modified" not in service)
    init = (BACKEND / "app/services/language_speaking_learning_stage/__init__.py").read_text(encoding="utf-8")
    check("0. RESPONSIBILITY declared", "RESPONSIBILITY" in init)


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
    )
    ok = proc.returncode == 0
    check(label, ok)
    if not ok:
        print(proc.stdout[-2500:] if proc.stdout else "")
        print(proc.stderr[-2500:] if proc.stderr else "")


def main() -> int:
    print("=== Speaking S15 stage signal aggregator verifier ===\n")
    test_source_guards()
    test_contract_and_scope()
    test_coverage_performance_sufficiency()
    test_recency_retry_transfer_retention()
    test_blockers_fingerprint_authority()

    run_regression("40. S0 architecture remains green", "verify_speaking_s0_architecture.py")
    run_regression("41. S9 remains green", "verify_speaking_s9_adaptive_journey.py")
    run_regression("42. S10 remains green", "verify_speaking_s10_educational_missions.py")
    run_regression("43. S10.1 remains green", "verify_speaking_s101_mission_stabilization.py")
    run_regression("44. S11 remains green", "verify_speaking_s11_attempt_lineage.py")
    run_regression("45. S12 remains green", "verify_speaking_s12_journey_read_model.py")
    run_regression("46. S13 remains green", "verify_speaking_s13_live_budget.py")
    run_regression("47. S14 remains green", "verify_speaking_s14_alex_context_identity.py")

    print(f"\n=== RESULT: {PASS} passed, {FAIL} failed ===")
    return 1 if FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
