"""Verify Speaking S11 — durable attempt lineage & mission task runtime wiring.

Proves:
- canonical activity → mission → task resolution
- attempt start/resume/retry semantics
- EVI multi-turn / multi-eval under one attempt
- turn/eval idempotency
- retry chain A1→A2→A3
- JSONB storage round-trip
- no mastery/CEFR/stage authority in lineage
- no retry mission / no migration / no Hume dependency

Runs S0, S9, S10, S10.1 as regressions.

Usage (from backend/):
    python scripts/verify_speaking_s11_attempt_lineage.py
"""

from __future__ import annotations

import os

import dataclasses
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.language_speaking.enums import SpeakingMissionKind
from app.services.language_speaking_diagnostic.selector import select_speaking_target
from app.services.language_speaking_diagnostic.types import TargetSelectionReason
from app.services.language_speaking_journey.builder import build_speaking_journey_bundle
from app.services.language_speaking_knowledge_model.storage import empty_knowledge_model
from app.services.language_speaking_lesson_planner.attempt_lineage import (
    SpeakingAttemptStatus,
    SpeakingSessionAttemptLineage,
    SpeakingTaskAttempt,
    apply_outcome_to_attempt,
    attempts_for_task,
    get_active_attempt,
    latest_attempt_for_task,
    mark_active_attempt_for_outcome,
    retry_chain_for_attempt,
    start_or_resume_attempt,
    student_safe_attempt_projection,
)
from app.services.language_speaking_lesson_planner.mission_task_resolver import (
    resolve_activity_to_task,
    resolve_current_task,
)
from app.services.language_speaking_lesson_planner.mission_types import SpeakingMissionOutcome
from app.services.language_speaking_lesson_planner.planner import assemble_speaking_lesson_blueprint
from app.services.language_speaking_lesson_planner.session_runtime import (
    advance_session_activity,
    create_learning_session,
)
from app.services.language_speaking_lesson_planner.storage import (
    ATTEMPT_LINEAGE_KEY,
    load_s9_state,
    save_s9_state,
)
from app.services.language_speaking_lesson_planner.types import SpeakingSessionActivityKind

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


def _blueprint(reason: TargetSelectionReason = TargetSelectionReason.weak_mastery):
    km = empty_knowledge_model(student_id=601, language_id=1)
    base = select_speaking_target(km, official_cefr="A2")
    rec = dataclasses.replace(base, selection_reason=reason)
    return assemble_speaking_lesson_blueprint(rec)


def _session_at_activity(blueprint, kind: SpeakingSessionActivityKind):
    session = create_learning_session(blueprint, live_session_id="live-s11-test")
    # Advance until the target activity is current.
    guard = 0
    while session.current_activity_id:
        current = next((a for a in blueprint.activities if a.activity_id == session.current_activity_id), None)
        if current is None:
            break
        if current.kind is kind:
            break
        session = advance_session_activity(session, blueprint, completed_activity_id=current.activity_id)
        guard += 1
        if guard > 10:
            break
    return session


def test_resolver() -> None:
    bp = _blueprint()
    session = _session_at_activity(bp, SpeakingSessionActivityKind.communicative_task)
    res = resolve_current_task(bp, session)
    check("1. current activity resolves canonically to mission/task", res.is_task and bool(res.task_id) and bool(res.mission_id))
    check("2. executable task identity is consumed by runtime (task_id present)", bool(res.task_id) and res.mission_kind == SpeakingMissionKind.speak.value)
    check("resolver returns retry_policy", bool(res.retry_policy))
    check("resolver returns legacy_activity_ref", res.legacy_activity_ref == session.current_activity_id or bool(res.legacy_activity_ref))

    # Non-task: warmup
    warm = create_learning_session(bp)
    warm_res = resolve_current_task(bp, warm)
    check("non-executable activity returns typed non-task (no invented id)", not warm_res.is_task and not warm_res.task_id)


def test_scenario_a_first_attempt_multi_turn() -> None:
    bp = _blueprint()
    session = _session_at_activity(bp, SpeakingSessionActivityKind.communicative_task)
    res = resolve_current_task(bp, session)
    lineage = SpeakingSessionAttemptLineage.empty_for_session(session.session_id)
    a1 = start_or_resume_attempt(
        lineage, res,
        session_id=session.session_id,
        blueprint_id=bp.blueprint_id,
        live_session_id=session.live_session_id,
    )
    check("3. first task execution creates attempt 1", a1.attempt_number == 1 and a1.retry_of_attempt_id == "")
    for i in range(1, 4):
        a1.attach_turn(f"turn-{i}")
        a1.attach_evaluation(f"eval-{i}")
    check("5. a new student turn does not create a new attempt", len(lineage.attempts) == 1)
    check("6. multiple live_turn_ids can belong to one EVI attempt", len(a1.live_turn_ids) == 3)
    check("7. multiple evaluation_ids can belong to one attempt", len(a1.evaluation_ids) == 3)
    # Idempotency
    a1.attach_turn("turn-1")
    a1.attach_evaluation("eval-2")
    check("8. duplicate live_turn_id is idempotent", len(a1.live_turn_ids) == 3)
    check("9. duplicate evaluation_id is idempotent", len(a1.evaluation_ids) == 3)


def test_scenario_b_reconnect() -> None:
    bp = _blueprint()
    session = _session_at_activity(bp, SpeakingSessionActivityKind.communicative_task)
    res = resolve_current_task(bp, session)
    lineage = SpeakingSessionAttemptLineage.empty_for_session(session.session_id)
    a1 = start_or_resume_attempt(
        lineage, res,
        session_id=session.session_id,
        blueprint_id=bp.blueprint_id,
        live_session_id=session.live_session_id,
    )
    a1.attach_turn("turn-r1")
    a_resume = start_or_resume_attempt(
        lineage, res,
        session_id=session.session_id,
        blueprint_id=bp.blueprint_id,
        is_resume=True,
        live_session_id=session.live_session_id,
    )
    check("4. reconnect/resume reuses the same attempt", a_resume.attempt_id == a1.attempt_id)
    check("resume preserves attempt_number", a_resume.attempt_number == 1)
    check("resume does not create second attempt", len(lineage.attempts) == 1)


def test_scenario_c_d_retry_chain() -> None:
    bp = _blueprint()
    session = _session_at_activity(bp, SpeakingSessionActivityKind.communicative_task)
    res = resolve_current_task(bp, session)
    lineage = SpeakingSessionAttemptLineage.empty_for_session(session.session_id)
    a1 = start_or_resume_attempt(
        lineage, res,
        session_id=session.session_id,
        blueprint_id=bp.blueprint_id,
        live_session_id=session.live_session_id,
    )
    apply_outcome_to_attempt(a1, SpeakingMissionOutcome.retry_same_task)
    lineage.active_attempt_id = ""
    check("retry_same_task marks attempt terminal", a1.status is SpeakingAttemptStatus.failed)

    a2 = start_or_resume_attempt(
        lineage, res,
        session_id=session.session_id,
        blueprint_id=bp.blueprint_id,
        is_resume=False,
        live_session_id=session.live_session_id,
        force_new=True,
    )
    check("10. retry creates a fresh attempt_id", a2.attempt_id != a1.attempt_id)
    check("11. retry increments attempt_number", a2.attempt_number == 2)
    check("12. retry_of_attempt_id points to immediately previous", a2.retry_of_attempt_id == a1.attempt_id)

    apply_outcome_to_attempt(a2, SpeakingMissionOutcome.retry_with_scaffold)
    lineage.active_attempt_id = ""
    a3 = start_or_resume_attempt(
        lineage, res,
        session_id=session.session_id,
        blueprint_id=bp.blueprint_id,
        force_new=True,
        live_session_id=session.live_session_id,
    )
    check("retry again creates attempt 3 linked to a2", a3.attempt_number == 3 and a3.retry_of_attempt_id == a2.attempt_id)
    chain = retry_chain_for_attempt(lineage, a3.attempt_id)
    check(
        "13. three-attempt retry chain resolves A1->A2->A3",
        [a.attempt_id for a in chain] == [a1.attempt_id, a2.attempt_id, a3.attempt_id],
    )

    # Malformed cycle
    a3.retry_of_attempt_id = a3.attempt_id  # self-cycle
    cycle_raised = False
    try:
        retry_chain_for_attempt(lineage, a3.attempt_id)
    except ValueError as exc:
        cycle_raised = "malformed_retry_cycle" in str(exc)
    check("14. malformed retry cycles are rejected/detected", cycle_raised)
    a3.retry_of_attempt_id = a2.attempt_id  # restore


def test_separate_task_lineage() -> None:
    bp = _blueprint(TargetSelectionReason.sparse_evidence_safe_start)
    # Guided practice and speak are distinct task lineages.
    session_g = _session_at_activity(bp, SpeakingSessionActivityKind.guided_practice)
    res_g = resolve_current_task(bp, session_g)
    lineage = SpeakingSessionAttemptLineage.empty_for_session(session_g.session_id)
    ag = start_or_resume_attempt(
        lineage, res_g,
        session_id=session_g.session_id,
        blueprint_id=bp.blueprint_id,
    )
    apply_outcome_to_attempt(ag, SpeakingMissionOutcome.complete)
    lineage.active_attempt_id = ""

    session_s = _session_at_activity(bp, SpeakingSessionActivityKind.communicative_task)
    session_s.session_id = session_g.session_id
    res_s = resolve_current_task(bp, session_s)
    as_ = start_or_resume_attempt(
        lineage, res_s,
        session_id=session_s.session_id,
        blueprint_id=bp.blueprint_id,
        live_session_id=session_s.live_session_id,
    )
    check("15. starting another task creates a separate task lineage", as_.task_id != ag.task_id and as_.attempt_number == 1)
    check("guided and speak attempts do not share retry link", as_.retry_of_attempt_id == "")


def test_scenario_e_storage_roundtrip() -> None:
    bp = _blueprint()
    session = _session_at_activity(bp, SpeakingSessionActivityKind.communicative_task)
    res = resolve_current_task(bp, session)
    lineage = SpeakingSessionAttemptLineage.empty_for_session(session.session_id)
    a1 = start_or_resume_attempt(
        lineage, res,
        session_id=session.session_id,
        blueprint_id=bp.blueprint_id,
        live_session_id=session.live_session_id,
    )
    a1.attach_turn("turn-store-1")
    a1.attach_evaluation("eval-store-1")
    apply_outcome_to_attempt(a1, SpeakingMissionOutcome.retry_same_task)
    lineage.active_attempt_id = ""
    a2 = start_or_resume_attempt(
        lineage, res,
        session_id=session.session_id,
        blueprint_id=bp.blueprint_id,
        force_new=True,
        live_session_id=session.live_session_id,
    )

    bucket = save_s9_state({}, blueprint=bp, session=session, attempt_lineage=lineage)
    check("lineage key present in speaking bucket", ATTEMPT_LINEAGE_KEY in bucket)
    restored_state = load_s9_state(bucket)
    restored = restored_state.attempt_lineage
    check("16. attempt state round-trips through storage", restored is not None and len(restored.attempts) == 2)
    check("17. active attempt resumes after storage round-trip", restored is not None and restored.active_attempt_id == a2.attempt_id)
    r1 = next(a for a in restored.attempts if a.attempt_id == a1.attempt_id)
    check("18. completion status survives round-trip", r1.status is SpeakingAttemptStatus.failed and r1.completed_at != "")
    check("identity exact after round-trip", r1.live_turn_ids == ["turn-store-1"] and r1.evaluation_ids == ["eval-store-1"])


def test_authority_and_non_goals() -> None:
    bp = _blueprint()
    session = _session_at_activity(bp, SpeakingSessionActivityKind.communicative_task)
    res = resolve_current_task(bp, session)
    lineage = SpeakingSessionAttemptLineage.empty_for_session(session.session_id)
    a1 = start_or_resume_attempt(lineage, res, session_id=session.session_id, blueprint_id=bp.blueprint_id)
    blob = json.dumps(lineage.to_dict()).lower()
    check("19. attempt storage contains no mastery/CEFR/stage mutation authority",
          "mastery" not in blob and "official_speaking_cefr" not in blob and "learning_stage" not in blob)
    check("20. no retry mission is introduced", "retry" not in {m.value for m in SpeakingMissionKind})
    check("21. transfer evidence is not inferred from retry/mission pointers",
          not hasattr(a1, "transfer_of_mission_id") and a1.retry_of_attempt_id == "")
    # S9 legacy still advances
    before = session.current_activity_id
    next_session = advance_session_activity(session, bp, completed_activity_id=before)
    check("22. S9 legacy activity runtime remains compatible", next_session.current_activity_id != before)
    check("24. no migration introduced (dataclass, not ORM table)", not hasattr(SpeakingTaskAttempt, "__tablename__"))
    check("25. no Hume/provider dependency in lineage ownership", "hume" not in blob and "openai" not in blob)

    # MissionKind still educational phases only (S10.1 invariant)
    check("23. S10.1 taxonomy invariants remain green",
          set(m.value for m in SpeakingMissionKind) == {
              "teaching", "noticing", "guided_practice", "speak", "feedback", "transfer", "retention_review",
          })


def test_student_safe_projection() -> None:
    bp = _blueprint()
    session = _session_at_activity(bp, SpeakingSessionActivityKind.communicative_task)
    res = resolve_current_task(bp, session)
    lineage = SpeakingSessionAttemptLineage.empty_for_session(session.session_id)
    a1 = start_or_resume_attempt(lineage, res, session_id=session.session_id, blueprint_id=bp.blueprint_id)
    apply_outcome_to_attempt(a1, SpeakingMissionOutcome.retry_same_task)
    lineage.active_attempt_id = ""
    a2 = start_or_resume_attempt(lineage, res, session_id=session.session_id, blueprint_id=bp.blueprint_id, force_new=True)
    bundle = build_speaking_journey_bundle(
        official_level="A2", plan=None, blueprint=bp, session=session, attempt_lineage=lineage,
    )
    student = bundle.to_student_dict()
    check("student projection exposes current_attempt_number", student.get("current_attempt_number") == 2)
    check("student projection exposes is_retry", student.get("is_retry") is True)
    check("student projection exposes completed_task_attempt_count", student.get("completed_task_attempt_count") == 1)
    blob = json.dumps(student)
    check("student projection hides eval/turn/chain ids",
          "evaluation_ids" not in blob and "live_turn_ids" not in blob and a2.attempt_id not in blob)


def test_mark_outcome_helper() -> None:
    bp = _blueprint()
    session = _session_at_activity(bp, SpeakingSessionActivityKind.communicative_task)
    res = resolve_current_task(bp, session)
    lineage = SpeakingSessionAttemptLineage.empty_for_session(session.session_id)
    start_or_resume_attempt(lineage, res, session_id=session.session_id, blueprint_id=bp.blueprint_id)
    mark_active_attempt_for_outcome(lineage, SpeakingMissionOutcome.complete)
    check("complete clears active_attempt_id", lineage.active_attempt_id == "")
    check("complete leaves attempt completed", latest_attempt_for_task(lineage, res.task_id).status is SpeakingAttemptStatus.completed)


def run_frozen_regressions() -> None:
    if os.environ.get("SPEAKING_VERIFY_SKIP_NESTED_REGRESSIONS") == "1":
        print("  (flat mode: skip nested regressions)", flush=True)
        return
    scripts = [
        "verify_speaking_s0_architecture.py",
        "verify_speaking_s9_adaptive_journey.py",
        "verify_speaking_s10_educational_missions.py",
        "verify_speaking_s101_mission_stabilization.py",
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
            print(proc.stdout[-4000:] if proc.stdout else "")
            print(proc.stderr[-2000:] if proc.stderr else "")
        check(f"frozen regression {name}", proc.returncode == 0)


def main() -> int:
    print("Speaking S11 attempt lineage verifier\n")
    test_resolver()
    test_scenario_a_first_attempt_multi_turn()
    test_scenario_b_reconnect()
    test_scenario_c_d_retry_chain()
    test_separate_task_lineage()
    test_scenario_e_storage_roundtrip()
    test_authority_and_non_goals()
    test_student_safe_projection()
    test_mark_outcome_helper()
    run_frozen_regressions()
    print(f"\nResult: {PASS} passed, {FAIL} failed")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
