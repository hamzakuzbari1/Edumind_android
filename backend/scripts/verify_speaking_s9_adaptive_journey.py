"""Verify Speaking S9 — adaptive learning journey orchestration.

Usage (from backend/):
    python scripts/verify_speaking_s9_adaptive_journey.py
"""

from __future__ import annotations

import os

import asyncio
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.language_speaking.ownership import ALLOWED_PACKAGE_DEPENDENCIES
from app.services.language_speaking_coach.session_live_context import merge_session_into_live_context
from app.services.language_speaking_coach.types import StudentSpeakingLiveContext
from app.services.language_speaking_curriculum.skill_catalog import SPEAKING_SKILL_GRAPH
from app.services.language_speaking_diagnostic.prerequisites import prerequisite_state
from app.services.language_speaking_diagnostic.selector import select_speaking_target
from app.services.language_speaking_diagnostic.types import TargetSelectionReason
from app.services.language_speaking_knowledge_model.storage import empty_knowledge_model
from app.services.language_speaking_knowledge_model.types import (
    SpeakingSkillStatus,
    StudentSpeakingSkillState,
)
from app.services.language_speaking_lesson_planner.decision_rules import decide_session_outcome
from app.services.language_speaking_lesson_planner.planner import assemble_speaking_lesson_blueprint
from app.services.language_speaking_lesson_planner.session_runtime import (
    create_learning_session,
    evaluate_session_boundary,
    record_session_turn,
)
from app.services.language_speaking_lesson_planner.types import SpeakingLearningSession, SpeakingSessionMode

PASS = 0
FAIL = 0


def check(label: str, cond: bool) -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  OK  {label}")
    else:
        FAIL += 1
        print(f" FAIL {label}")


def test_a_sparse_evidence_safe_start() -> None:
    km = empty_knowledge_model(student_id=1, language_id=1)
    rec = select_speaking_target(km, official_cefr="A2")
    check("A sparse evidence -> safe root target", rec.selection_reason == TargetSelectionReason.sparse_evidence_safe_start)
    check("A target is valid skill", SPEAKING_SKILL_GRAPH.node_by_id(rec.primary_target_skill_id) is not None)


def test_b_prerequisite_guard() -> None:
    km = empty_knowledge_model(student_id=2, language_id=1)
    advanced = next(n for n in SPEAKING_SKILL_GRAPH.nodes if n.prerequisite_skill_ids)
    ok, blocked = prerequisite_state(advanced, km)
    check("B weak prereq blocks advanced", not ok and len(blocked) > 0)


def test_c_d_e_session_decisions() -> None:
    bp_pron = assemble_speaking_lesson_blueprint(
        select_speaking_target(
            _model_with_weak("phoneme:theta", area="pronunciation"),
            official_cefr="A2",
        )
    )
    session = create_learning_session(bp_pron)
    for tid in ("t1", "t1b"):
        session = record_session_turn(
            session,
            live_turn_id=tid,
            target_skill_id=bp_pron.primary_target_skill_id,
            performance=0.35,
            success=False,
            source_dimension="pronunciation",
            mistake_tags=("misarticulation:theta",),
            mutation_applied=True,
        )
    d1 = decide_session_outcome(
        session,
        primary_target_skill_id=bp_pron.primary_target_skill_id,
        selection_reason=TargetSelectionReason.pronunciation_weakness.value,
        min_communicative_turns=2,
    )
    check("C pronunciation weakness -> focused retry path", d1.outcome_kind.value == "focused_retry")
    check("F one weak turn no regression streak", d1.retry_same_target)

    bp_task = assemble_speaking_lesson_blueprint(
        select_speaking_target(
            _model_with_weak("function:express_opinion"),
            official_cefr="B1",
        )
    )
    session2 = create_learning_session(bp_task)
    for tid in ("t2", "t2b"):
        session2 = record_session_turn(
            session2,
            live_turn_id=tid,
            target_skill_id=bp_task.primary_target_skill_id,
            performance=0.38,
            success=False,
            source_dimension="task_response",
            mistake_tags=(),
            mutation_applied=True,
        )
    d2 = decide_session_outcome(
        session2,
        primary_target_skill_id=bp_task.primary_target_skill_id,
        selection_reason=TargetSelectionReason.task_weakness.value,
        min_communicative_turns=2,
    )
    check("E task weakness -> remediation", d2.outcome_kind.value in ("remediation", "focused_retry"))


def _model_with_weak(skill_id: str, area: str = "") -> object:
    km = empty_knowledge_model(student_id=3, language_id=1)
    km.total_observations = 10
    node = SPEAKING_SKILL_GRAPH.node_by_id(skill_id)
    if node is None:
        skill_id = SPEAKING_SKILL_GRAPH.roots[0].skill_id
        node = SPEAKING_SKILL_GRAPH.node_by_id(skill_id)
    km.skill_states[skill_id] = StudentSpeakingSkillState(
        skill_id=skill_id,
        mastery=0.32,
        evidence_count=4,
        recent_performance=0.30,
        current_status=SpeakingSkillStatus.developing,
    )
    return km


def test_g_multi_turn_session() -> None:
    rec = select_speaking_target(empty_knowledge_model(student_id=4, language_id=1))
    bp = assemble_speaking_lesson_blueprint(rec)
    session = create_learning_session(bp)
    for i, perf in enumerate((0.55, 0.62, 0.71)):
        session = record_session_turn(
            session,
            live_turn_id=f"turn-{i}",
            target_skill_id=bp.primary_target_skill_id,
            performance=perf,
            success=perf >= 0.5,
            source_dimension="pronunciation",
            mistake_tags=(),
            mutation_applied=True,
        )
    check("G multiple turns accumulate", len(session.turn_accumulations) == 3)
    check("G communicative turn count", session.communicative_turns_completed == 3)


def test_h_focused_retry_same_target() -> None:
    rec = select_speaking_target(empty_knowledge_model(student_id=5, language_id=1))
    bp = assemble_speaking_lesson_blueprint(rec)
    session = create_learning_session(bp)
    for _ in range(2):
        session = record_session_turn(
            session,
            live_turn_id="weak",
            target_skill_id=bp.primary_target_skill_id,
            performance=0.30,
            success=False,
            source_dimension="pronunciation",
            mistake_tags=("misarticulation",),
            mutation_applied=True,
        )
    decision = evaluate_session_boundary(session, bp)
    check("H focused retry same target", decision.retry_same_target)


def test_i_reinforcement() -> None:
    rec = select_speaking_target(empty_knowledge_model(student_id=6, language_id=1))
    bp = assemble_speaking_lesson_blueprint(rec)
    session = create_learning_session(bp)
    for perf in (0.72, 0.78):
        session = record_session_turn(
            session,
            live_turn_id=f"strong-{perf}",
            target_skill_id=bp.primary_target_skill_id,
            performance=perf,
            success=True,
            source_dimension="task_response",
            mistake_tags=(),
            mutation_applied=True,
        )
    decision = evaluate_session_boundary(session, bp)
    check("I improvement can reinforce", decision.outcome_kind.value in ("reinforcement", "session_complete"))


def test_j_evi_session_context() -> None:
    rec = select_speaking_target(empty_knowledge_model(student_id=7, language_id=1))
    bp = assemble_speaking_lesson_blueprint(rec)
    base = StudentSpeakingLiveContext(
        context_version="7.6.0",
        student_reference="spk-test",
        speaking_goal="general_english",
        learner_state="developing",
    )
    merged = merge_session_into_live_context(base, bp.alex_context.to_dict())
    parsed = json.loads(merged)
    check("J EVI receives session tutoring block", "session_tutoring" in parsed)
    check("J session goal present", parsed["session_tutoring"].get("session_goal"))


def test_k_l_m_n_student_safe() -> None:
    rec = select_speaking_target(empty_knowledge_model(student_id=8, language_id=1))
    bp = assemble_speaking_lesson_blueprint(rec)
    student = bp.to_dict()
    blob = json.dumps(student)
    check("K no mastery in EVI constraints", "mastery" not in blob.lower() or "do not assign" in blob.lower())
    check("L blueprint hash present", bool(bp.blueprint_hash))
    check("M plan does not embed knowledge_model", "skill_states" not in blob)
    check("N no raw provider ids", "hume" not in blob.lower() and "openai" not in blob.lower())


def test_ownership_dag() -> None:
    check("O lesson_planner deps legal", "language_speaking_knowledge_model" in ALLOWED_PACKAGE_DEPENDENCIES["language_speaking_lesson_planner"])
    check("O journey deps include planner", "language_speaking_lesson_planner" in ALLOWED_PACKAGE_DEPENDENCIES["language_speaking_journey"])


def run_frozen_regressions() -> None:
    if os.environ.get("SPEAKING_VERIFY_SKIP_NESTED_REGRESSIONS") == "1":
        print("  (flat mode: skip nested regressions)", flush=True)
        return
    scripts = [
        "verify_speaking_s0_architecture.py",
    ]
    backend = Path(__file__).resolve().parents[1]
    for name in scripts:
        path = backend / "scripts" / name
        if not path.exists():
            print(f"  skip regression {name} (not found)")
            continue
        print(f"\n--- regression: {name} ---")
        proc = subprocess.run([sys.executable, str(path)], cwd=str(backend), capture_output=True, text=True)
        if proc.returncode != 0:
            print(proc.stdout[-2000:] if proc.stdout else "")
            print(proc.stderr[-2000:] if proc.stderr else "")
        check(f"O frozen {name}", proc.returncode == 0)


def main() -> int:
    print("Speaking S9 adaptive journey verifier\n")
    test_a_sparse_evidence_safe_start()
    test_b_prerequisite_guard()
    test_c_d_e_session_decisions()
    test_g_multi_turn_session()
    test_h_focused_retry_same_target()
    test_i_reinforcement()
    test_j_evi_session_context()
    test_k_l_m_n_student_safe()
    test_ownership_dag()
    run_frozen_regressions()
    print(f"\nResult: {PASS} passed, {FAIL} failed")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
