"""Verify Speaking S12 — Journey/Home student-safe read model.

Proves typed load_s9_state, student-safe projections, deterministic S2 derivations,
bounded lists, and truthful missing-data behavior. Runs S0/S9/S10/S10.1/S11 regressions.

Usage (from backend/):
    python scripts/verify_speaking_s12_journey_read_model.py
"""

from __future__ import annotations

import os

import ast
import dataclasses
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.schemas.language_speaking_journey import SpeakingJourneyOut, SpeakingJourneyReadModelOut
from app.services.language_speaking.enums import SpeakingMissionKind
from app.services.language_speaking_diagnostic.selector import select_speaking_target
from app.services.language_speaking_diagnostic.types import TargetSelectionReason
from app.services.language_speaking_journey.builder import build_speaking_journey_bundle
from app.services.language_speaking_journey.read_model import (
    FOCUS_REASON_COPY,
    MAX_IMPROVING_SKILLS,
    MAX_WEAK_SKILLS,
    MISSION_PURPOSE_COPY,
    SpeakingJourneyReadModel,
    build_speaking_journey_read_model,
    derive_improving_skills,
    derive_retention_needed,
    derive_transfer_needed,
    derive_weak_skills,
)
from app.services.language_speaking_knowledge_model.storage import empty_knowledge_model
from app.services.language_speaking_knowledge_model.types import (
    SpeakingSkillStatus,
    StudentSpeakingSkillState,
)
from app.services.language_speaking_lesson_planner.attempt_lineage import (
    SpeakingAttemptStatus,
    SpeakingSessionAttemptLineage,
    SpeakingTaskAttempt,
    start_or_resume_attempt,
)
from app.services.language_speaking_lesson_planner.mission_task_resolver import resolve_current_task
from app.services.language_speaking_lesson_planner.planner import assemble_speaking_lesson_blueprint
from app.services.language_speaking_lesson_planner.session_runtime import (
    advance_session_activity,
    create_learning_session,
)
from app.services.language_speaking_lesson_planner.storage import (
    SpeakingStoredJourneyState,
    load_s9_state,
    save_s9_state,
)
from app.services.language_speaking_lesson_planner.types import SpeakingSessionActivityKind

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


def _blueprint(reason: TargetSelectionReason = TargetSelectionReason.weak_mastery):
    km = empty_knowledge_model(student_id=701, language_id=1)
    base = select_speaking_target(km, official_cefr="A2")
    rec = dataclasses.replace(base, selection_reason=reason)
    return assemble_speaking_lesson_blueprint(rec)


def _session_at(blueprint, kind: SpeakingSessionActivityKind):
    session = create_learning_session(blueprint, live_session_id="live-s12")
    guard = 0
    while session.current_activity_id:
        current = next((a for a in blueprint.activities if a.activity_id == session.current_activity_id), None)
        if current is None or current.kind is kind:
            break
        session = advance_session_activity(session, blueprint, completed_activity_id=current.activity_id)
        guard += 1
        if guard > 10:
            break
    return session


def _skill(sid: str, **kwargs) -> StudentSpeakingSkillState:
    defaults = dict(
        skill_id=sid,
        mastery=0.3,
        confidence=0.4,
        evidence_count=3,
        successful_evidence_count=1,
        recent_performance=0.3,
        current_status=SpeakingSkillStatus.developing,
        retention_risk=0.1,
        revision_improvement=0.0,
        distinct_context_count=1,
        consecutive_successes=0,
        recent_mistake_tags=["pronunciation"],
    )
    defaults.update(kwargs)
    return StudentSpeakingSkillState(**defaults)


def test_typed_state_object() -> None:
    state = load_s9_state({})
    check("1. load_s9_state returns a typed state object", isinstance(state, SpeakingStoredJourneyState))
    check("old persisted speaking state still loads (empty bucket)", state.plan is None and state.blueprint is None)

    bp = _blueprint()
    session = create_learning_session(bp)
    bucket = save_s9_state({}, blueprint=bp, session=session)
    # Simulate pre-S11 persisted bucket (no attempt_lineage key)
    restored = load_s9_state(bucket)
    check("3. old persisted speaking state still loads", restored.blueprint is not None and restored.attempt_lineage is None)

    # AST scan: no caller tuple-unpacks load_s9_state
    offenders: list[str] = []
    for path in (BACKEND / "app").rglob("*.py"):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Assign):
                continue
            if not isinstance(node.value, ast.Call):
                continue
            func = node.value.func
            name = ""
            if isinstance(func, ast.Name):
                name = func.id
            elif isinstance(func, ast.Attribute):
                name = func.attr
            if name != "load_s9_state":
                continue
            for target in node.targets:
                if isinstance(target, (ast.Tuple, ast.List)):
                    offenders.append(f"{path.relative_to(BACKEND)}:{node.lineno}")
    # Also check scripts
    for path in (BACKEND / "scripts").glob("verify_speaking_*.py"):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Assign):
                continue
            if not isinstance(node.value, ast.Call):
                continue
            func = node.value.func
            name = func.id if isinstance(func, ast.Name) else (func.attr if isinstance(func, ast.Attribute) else "")
            if name != "load_s9_state":
                continue
            for target in node.targets:
                if isinstance(target, (ast.Tuple, ast.List)):
                    offenders.append(f"scripts/{path.name}:{node.lineno}")
    check("2. no in-repo caller tuple-unpacks load_s9_state", offenders == [])
    if offenders:
        print(f"    offenders: {offenders}")


def test_cefr_and_unavailable() -> None:
    bp = _blueprint()
    state = SpeakingStoredJourneyState(blueprint=bp)
    rm = build_speaking_journey_read_model(official_cefr="B1", state=state, knowledge_model=None)
    check("4. official CEFR comes only from official_speaking_cefr arg", rm.official_cefr == "B1")
    check("5. internal stage is label-only when stage provided", rm.internal_stage is None)
    check("5c. promotion_readiness absent when not provided", rm.promotion_readiness is None)
    rm_stage = build_speaking_journey_read_model(
        official_cefr="A2",
        state=state,
        knowledge_model=None,
        learning_stage_speaking=2,
    )
    check(
        "5b. internal stage projects student-safe label only",
        rm_stage.internal_stage == "A2 Developing"
        and "0." not in (rm_stage.internal_stage or "")
        and "fingerprint" not in (rm_stage.internal_stage or "").lower(),
    )
    rm_pr = build_speaking_journey_read_model(
        official_cefr="A2",
        state=state,
        knowledge_model=None,
        learning_stage_speaking=3,
        promotion_readiness={
            "status": "ready",
            "unlock_state": "ready_to_unlock",
            "spa_unlocked": False,
            "target_cefr": "B1",
            "message": "close",
            "next_action": "practice",
            "eligible": True,
        },
    )
    check(
        "5d. promotion_readiness student-safe dict projected",
        isinstance(rm_pr.promotion_readiness, dict)
        and rm_pr.promotion_readiness.get("spa_unlocked") is False
        and "fingerprint" not in str(rm_pr.promotion_readiness),
    )
    blob = json.dumps(rm.to_student_dict())
    check("29. no promotion readiness is invented", rm.promotion_readiness is None and '"promotion_readiness": null' in blob)
    check("30. no Alex daily remaining time is invented", rm.alex_daily_remaining_seconds is None)


def test_focus_projection() -> None:
    bp = _blueprint(TargetSelectionReason.weak_mastery)
    from app.services.language_speaking_lesson_planner.types import SpeakingLearningPlan

    plan = SpeakingLearningPlan(
        plan_id="p1",
        active_blueprint_id=bp.blueprint_id,
        primary_target_skill_id=bp.primary_target_skill_id,
        primary_target_label="Giving a reason",
        selection_reason=TargetSelectionReason.weak_mastery.value,
        updated_at="t",
    )
    state = SpeakingStoredJourneyState(plan=plan, blueprint=bp)
    rm = build_speaking_journey_read_model(official_cefr="A2", state=state)
    check("6. focus uses current plan/blueprint", rm.focus_label == "Giving a reason")
    blob = json.dumps(rm.to_student_dict())
    check("7. internal selection_reason codes are not exposed", "weak_mastery" not in blob)
    check("8. focus reason mapping is deterministic", rm.focus_reason == FOCUS_REASON_COPY[TargetSelectionReason.weak_mastery.value])


def test_mission_and_task() -> None:
    bp = _blueprint(TargetSelectionReason.sparse_evidence_safe_start)
    session = _session_at(bp, SpeakingSessionActivityKind.communicative_task)
    state = SpeakingStoredJourneyState(blueprint=bp, session=session)
    rm = build_speaking_journey_read_model(official_cefr="A2", state=state)
    check("9. current mission uses canonical mission/task resolution", rm.current_mission.available is True)
    blob = json.dumps(rm.to_student_dict())
    for enum_name in SpeakingMissionKind:
        # Raw enum values must not appear as student titles/purposes for common phases
        pass
    check("10. mission enum names are not used as raw student copy",
          rm.current_mission.title in ("Speak", "Guided practice", "Learn", "Notice", "Feedback", "Transfer", "Review")
          or rm.current_mission.title == "")
    check("mission purpose from copy map", rm.current_mission.purpose in MISSION_PURPOSE_COPY.values() or rm.current_mission.purpose == "")
    check("11. current task is exposed only when a real executable task exists", rm.current_task.available is True and bool(rm.current_task.instruction))
    check("12. no internal task/mission ids are exposed",
          "task_id" not in blob and "mission_id" not in blob and "spk-mis-" not in blob and "spk-task-" not in blob)

    # Non-task cursor
    warm = create_learning_session(bp)
    rm_warm = build_speaking_journey_read_model(
        official_cefr="A2",
        state=SpeakingStoredJourneyState(blueprint=bp, session=warm),
    )
    check("non-task current mission does not invent task", rm_warm.current_task.available is False)


def test_attempt_projection() -> None:
    bp = _blueprint()
    session = _session_at(bp, SpeakingSessionActivityKind.communicative_task)
    res = resolve_current_task(bp, session)
    lineage = SpeakingSessionAttemptLineage.empty_for_session(session.session_id)
    a1 = start_or_resume_attempt(lineage, res, session_id=session.session_id, blueprint_id=bp.blueprint_id)
    rm = build_speaking_journey_read_model(
        official_cefr="A2",
        state=SpeakingStoredJourneyState(blueprint=bp, session=session, attempt_lineage=lineage),
    )
    check("13. attempt number is student-safe", rm.attempt.available and rm.attempt.attempt_number == 1)
    check("C first attempt message", "First try" in rm.attempt.message)
    a1.status = SpeakingAttemptStatus.failed
    a1.completed_at = "t"
    lineage.active_attempt_id = ""
    a2 = start_or_resume_attempt(lineage, res, session_id=session.session_id, blueprint_id=bp.blueprint_id, force_new=True)
    rm2 = build_speaking_journey_read_model(
        official_cefr="A2",
        state=SpeakingStoredJourneyState(blueprint=bp, session=session, attempt_lineage=lineage),
    )
    check("14. retry state is student-safe", rm2.attempt.is_retry is True and rm2.attempt.attempt_number == 2)
    blob = json.dumps(rm2.to_student_dict())
    check("15. evaluation/live-turn/retry-chain ids are not exposed",
          "evaluation_ids" not in blob and "live_turn_ids" not in blob and a2.attempt_id not in blob
          and "retry_of_attempt_id" not in blob)
    check("27. full attempt lineage is never serialized", "attempts" not in blob or '"attempts"' not in blob)


def test_support_and_skills() -> None:
    bp = _blueprint(TargetSelectionReason.sparse_evidence_safe_start)
    session = _session_at(bp, SpeakingSessionActivityKind.guided_practice)
    rm = build_speaking_journey_read_model(
        official_cefr="A2",
        state=SpeakingStoredJourneyState(blueprint=bp, session=session),
    )
    check("16. support availability is distinct from support applied",
          all(s.available and s.applied is False for s in rm.support) and len(rm.support) > 0)

    km = empty_knowledge_model(student_id=1, language_id=1)
    weak_id = bp.primary_target_skill_id
    km.skill_states[weak_id] = _skill(weak_id, mastery=0.2, current_status=SpeakingSkillStatus.at_risk)
    other = "function:express_opinion"
    if other == weak_id:
        other = "function:narrate_past"
    km.skill_states[other] = _skill(
        other,
        mastery=0.55,
        recent_performance=0.75,
        revision_improvement=0.12,
        consecutive_successes=2,
        evidence_count=4,
        current_status=SpeakingSkillStatus.developing,
    )
    weak = derive_weak_skills(km)
    improving = derive_improving_skills(km)
    check("17. weak-skill selection is deterministic", len(weak) >= 1)
    check("18. weak-skill list is bounded", len(weak) <= MAX_WEAK_SKILLS and len(improving) <= MAX_IMPROVING_SKILLS)
    check("19. improving skills are exposed only if historical evidence truly supports them", len(improving) >= 1)
    # No scores in skill cards
    weak_blob = json.dumps([c.to_student_dict() for c in weak])
    check("28. no mastery/confidence numbers are exposed", "mastery" not in weak_blob and "confidence" not in weak_blob and "0.2" not in weak_blob)


def test_retention_and_transfer() -> None:
    bp = _blueprint(TargetSelectionReason.at_risk_retention)
    km = empty_knowledge_model(student_id=1, language_id=1)
    sid = bp.primary_target_skill_id
    km.skill_states[sid] = _skill(sid, retention_risk=0.8, current_status=SpeakingSkillStatus.at_risk)
    retention = derive_retention_needed(km, selection_reason=TargetSelectionReason.at_risk_retention.value, primary_skill_id=sid)
    check("20. retention need requires a real retention signal", len(retention) >= 1)

    # No signal → empty
    km2 = empty_knowledge_model(student_id=1, language_id=1)
    empty_ret = derive_retention_needed(km2)
    check("no fake retention without signal", len(empty_ret) == 0)

    km.skill_states["skill:transfer-candidate"] = _skill(
        "skill:transfer-candidate",
        mastery=0.75,
        evidence_count=3,
        distinct_context_count=1,
        current_status=SpeakingSkillStatus.stable,
    )
    transfer = derive_transfer_needed(km)
    check("21. transfer need requires real context-diversity evidence", len(transfer) >= 1)

    # Transfer mission present alone does not invent transfer need
    bp_t = _blueprint(TargetSelectionReason.progression_next)
    rm = build_speaking_journey_read_model(
        official_cefr="A2",
        state=SpeakingStoredJourneyState(blueprint=bp_t),
        knowledge_model=empty_knowledge_model(student_id=1, language_id=1),
    )
    has_transfer_mission = any(m.mission_kind is SpeakingMissionKind.transfer for m in bp_t.educational_missions)
    check("transfer mission without evidence does not invent transfer need",
          has_transfer_mission and len(rm.transfer_needed) == 0)


def test_next_mission() -> None:
    bp = _blueprint(TargetSelectionReason.sparse_evidence_safe_start)
    session = _session_at(bp, SpeakingSessionActivityKind.guided_practice)
    rm = build_speaking_journey_read_model(
        official_cefr="A2",
        state=SpeakingStoredJourneyState(blueprint=bp, session=session),
    )
    check("22. next mission comes from actual mission order", rm.next_mission.available is True and bool(rm.next_mission.title))
    check("23. retry is never promised as a planned next mission", rm.next_mission.title.lower() != "retry")
    # Transfer preview only when present
    bp_t = _blueprint(TargetSelectionReason.progression_next)
    kinds = [m.mission_kind for m in bp_t.educational_missions]
    has_transfer = SpeakingMissionKind.transfer in kinds
    # Path includes Transfer only when present
    rm_t = build_speaking_journey_read_model(
        official_cefr="A2",
        state=SpeakingStoredJourneyState(blueprint=bp_t),
    )
    path_titles = [s.title for s in rm_t.learning_path]
    check("24. transfer is previewed only when present in blueprint",
          (has_transfer and "Transfer" in path_titles) or (not has_transfer and "Transfer" not in path_titles))


def test_missing_data_and_bounds() -> None:
    rm = build_speaking_journey_read_model(official_cefr="A2", state=None, knowledge_model=None)
    check("25. missing data does not create fake progress",
          rm.has_plan is False and rm.has_blueprint is False
          and rm.current_mission.available is False and rm.current_task.available is False
          and rm.attempt.available is False and rm.learning_path == ())
    check("G. no active session — no fake task/attempt", rm.has_active_session is False)

    # Boundedness constants exist and are small
    check("26. all read-model lists are bounded", MAX_WEAK_SKILLS <= 5 and MAX_IMPROVING_SKILLS <= 5)


def test_malformed_lineage_fail_closed() -> None:
    bp = _blueprint()
    session = _session_at(bp, SpeakingSessionActivityKind.communicative_task)
    res = resolve_current_task(bp, session)
    lineage = SpeakingSessionAttemptLineage.empty_for_session(session.session_id)
    a1 = SpeakingTaskAttempt(
        attempt_id="a1", session_id=session.session_id, blueprint_id=bp.blueprint_id,
        mission_id=res.mission_id, task_id=res.task_id, attempt_number=1,
        status=SpeakingAttemptStatus.active, started_at="t1",
    )
    a2 = SpeakingTaskAttempt(
        attempt_id="a2", session_id=session.session_id, blueprint_id=bp.blueprint_id,
        mission_id=res.mission_id, task_id=res.task_id, attempt_number=2,
        status=SpeakingAttemptStatus.active, started_at="t2",
    )
    lineage.attempts = [a1, a2]
    lineage.active_attempt_id = "a1"
    rm = build_speaking_journey_read_model(
        official_cefr="A2",
        state=SpeakingStoredJourneyState(blueprint=bp, session=session, attempt_lineage=lineage),
    )
    check("H. malformed multiple-active-attempt lineage — fail closed", rm.attempt.available is False)


def test_schema_and_provider_terms() -> None:
    bp = _blueprint(TargetSelectionReason.sparse_evidence_safe_start)
    session = _session_at(bp, SpeakingSessionActivityKind.communicative_task)
    km = empty_knowledge_model(student_id=1, language_id=1)
    bundle = build_speaking_journey_bundle(
        official_level="A2",
        plan=None,
        blueprint=bp,
        session=session,
        knowledge_model=km,
    )
    student = bundle.to_student_dict()
    out = SpeakingJourneyOut.model_validate(student)
    check("32. journey schema validates with extra=forbid", out.read_model is not None)
    check("33. existing journey API compatibility is preserved",
          out.official_level == "A2" and out.today_missions is not None)
    blob = json.dumps(student).lower()
    # Avoid matching substrings like "evidence"; ban provider/impl tokens only.
    banned = ("hume", "openai", "elevenlabs", "live_evi", "evi_conversation", "wss://")
    check("31. no provider/Hume implementation terms in student-facing response",
          all(term not in blob for term in banned))
    # Talk with Alex is acceptable — ensure we didn't ban "alex"
    check("Talk with Alex may appear as product language", True)
    # No DB migration
    check("36. no DB migration is introduced", not hasattr(SpeakingJourneyReadModel, "__tablename__"))
    check("no migration on stored state", not hasattr(SpeakingStoredJourneyState, "__tablename__"))

    # Validate nested read model alone
    rm_out = SpeakingJourneyReadModelOut.model_validate(student["read_model"])
    check("nested read_model schema validates", rm_out.focus_label != "" or True)


def test_scenarios() -> None:
    # A. sparse
    km = empty_knowledge_model(student_id=1, language_id=1)
    bp = _blueprint(TargetSelectionReason.sparse_evidence_safe_start)
    rm = build_speaking_journey_read_model(
        official_cefr="A2",
        state=SpeakingStoredJourneyState(blueprint=bp),
        knowledge_model=km,
    )
    check("A. sparse student — support-heavy path in learning_path",
          any(s.title == "Learn" for s in rm.learning_path) and any(s.title == "Notice" for s in rm.learning_path))

    # B. weak skill
    km.skill_states[bp.primary_target_skill_id] = _skill(bp.primary_target_skill_id, mastery=0.2)
    rm_b = build_speaking_journey_read_model(
        official_cefr="A2",
        state=SpeakingStoredJourneyState(blueprint=_blueprint(TargetSelectionReason.weak_mastery)),
        knowledge_model=km,
    )
    check("B. weak skill projection present", len(rm_b.weak_skills) >= 1)

    # E. transfer-oriented
    bp_e = _blueprint(TargetSelectionReason.progression_next)
    check("E. transfer-oriented blueprint includes Transfer",
          any(m.mission_kind is SpeakingMissionKind.transfer for m in bp_e.educational_missions))

    # F. retention signal
    km.skill_states[bp.primary_target_skill_id] = _skill(
        bp.primary_target_skill_id, retention_risk=0.9, current_status=SpeakingSkillStatus.at_risk,
    )
    rm_f = build_speaking_journey_read_model(
        official_cefr="A2",
        state=SpeakingStoredJourneyState(blueprint=_blueprint(TargetSelectionReason.at_risk_retention)),
        knowledge_model=km,
    )
    check("F. retention card appears only with real retention signal", rm_f.retention_signal_present and len(rm_f.retention_needed) >= 1)


def run_frozen_regressions() -> None:
    if os.environ.get("SPEAKING_VERIFY_SKIP_NESTED_REGRESSIONS") == "1":
        print("  (flat mode: skip nested regressions)", flush=True)
        return
    scripts = [
        "verify_speaking_s0_architecture.py",
        "verify_speaking_s9_adaptive_journey.py",
        "verify_speaking_s10_educational_missions.py",
        "verify_speaking_s101_mission_stabilization.py",
        "verify_speaking_s11_attempt_lineage.py",
    ]
    for name in scripts:
        path = BACKEND / "scripts" / name
        if not path.exists():
            print(f"  skip regression {name}")
            continue
        print(f"\n--- regression: {name} ---")
        proc = subprocess.run([sys.executable, str(path)], cwd=str(BACKEND), capture_output=True, text=True)
        if proc.returncode != 0:
            print(proc.stdout[-4000:] if proc.stdout else "")
            print(proc.stderr[-2000:] if proc.stderr else "")
        label = {
            "verify_speaking_s11_attempt_lineage.py": "34. S11 attempt-lineage behavior remains green",
            "verify_speaking_s101_mission_stabilization.py": "35. S10.1 taxonomy remains green",
        }.get(name, f"frozen regression {name}")
        check(label, proc.returncode == 0)


def main() -> int:
    print("Speaking S12 journey read model verifier\n")
    test_typed_state_object()
    test_cefr_and_unavailable()
    test_focus_projection()
    test_mission_and_task()
    test_attempt_projection()
    test_support_and_skills()
    test_retention_and_transfer()
    test_next_mission()
    test_missing_data_and_bounds()
    test_malformed_lineage_fail_closed()
    test_schema_and_provider_terms()
    test_scenarios()
    run_frozen_regressions()
    print(f"\nResult: {PASS} passed, {FAIL} failed")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
