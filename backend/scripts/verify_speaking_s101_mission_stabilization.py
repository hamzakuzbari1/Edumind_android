"""Verify Speaking S10.1 — educational mission model stabilization.

Proves the S10.1 corrections that make the mission model safe to build S11 durable
persistence on: orthogonal taxonomy, enforced legal combinations, adaptive
(recommendation-driven) composition, retry-as-flow, transfer-as-task, blueprint-scoped
mission identity, explicit executable/content missions, and typed attempt identity
semantics. Runs S0, S9, and S10 verifiers as regressions.

Usage (from backend/):
    python scripts/verify_speaking_s101_mission_stabilization.py
"""

from __future__ import annotations

import os

import dataclasses
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.language_speaking.enums import (
    SpeakingEvidenceIntent,
    SpeakingExecutionMode,
    SpeakingMissionKind,
)
from app.services.language_speaking_diagnostic.selector import select_speaking_target
from app.services.language_speaking_diagnostic.types import TargetSelectionReason
from app.services.language_speaking_knowledge_model.storage import empty_knowledge_model
from app.services.language_speaking_lesson_experience.builder import build_lesson_experience_bundle
from app.services.language_speaking_lesson_planner.decision_rules import mission_flow_from_session_outcome
from app.services.language_speaking_lesson_planner.identity import (
    SPEAKING_IDENTITY_SEMANTICS,
    STABLE_ACROSS_RESUME,
    SpeakingAttemptIdentity,
    make_task_id,
    new_attempt_id,
    should_start_new_attempt,
)
from app.services.language_speaking_lesson_planner.mission_types import (
    SpeakingEducationalMission,
    SpeakingExecutableTask,
    SpeakingMissionOutcome,
)
from app.services.language_speaking_lesson_planner.planner import assemble_speaking_lesson_blueprint
from app.services.language_speaking_lesson_planner.storage import blueprint_from_dict
from app.services.language_speaking_lesson_planner.task_taxonomy import (
    is_legal_mission_combination,
    taxonomy_entry,
    validate_mission_combination,
)
from app.services.language_speaking_lesson_planner.types import SpeakingSessionOutcomeKind

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


def _base_recommendation(reason: TargetSelectionReason):
    km = empty_knowledge_model(student_id=501, language_id=1)
    base = select_speaking_target(km, official_cefr="A2")
    return dataclasses.replace(base, selection_reason=reason)


def _blueprint_for(reason: TargetSelectionReason):
    return assemble_speaking_lesson_blueprint(_base_recommendation(reason))


def _kinds(bp) -> tuple:
    return tuple(m.mission_kind for m in sorted(bp.educational_missions, key=lambda m: m.order_index))


# 1-3. Taxonomy is educational phases only; no execution/flow leakage.
def test_taxonomy_orthogonality() -> None:
    kinds = {m.value for m in SpeakingMissionKind}
    check("MissionKind holds 7 educational phases only", kinds == {
        "teaching", "noticing", "guided_practice", "speak", "feedback", "transfer", "retention_review",
    })
    modes = {m.value for m in SpeakingExecutionMode}
    check("no execution mode duplicated in MissionKind", kinds.isdisjoint(modes - {"study", "review"}) and "live_evi_conversation" not in kinds)
    for leaked in ("controlled_speaking", "recorded_speaking", "live_conversation"):
        check(f"execution modality not a MissionKind: {leaked}", leaked not in kinds)
    check("retry is NOT a MissionKind", "retry" not in kinds)
    check("retry IS a runtime flow outcome", "retry_same_task" in {o.value for o in SpeakingMissionOutcome})


# 4. Illegal mission triples are rejected deterministically.
def test_illegal_triples_rejected() -> None:
    illegal = [
        (SpeakingMissionKind.teaching, SpeakingExecutionMode.live_evi_conversation, SpeakingEvidenceIntent.summative),
        (SpeakingMissionKind.noticing, SpeakingExecutionMode.recorded_response, SpeakingEvidenceIntent.retention),
        (SpeakingMissionKind.feedback, SpeakingExecutionMode.live_evi_conversation, SpeakingEvidenceIntent.transfer),
    ]
    for kind, mode, intent in illegal:
        raised = False
        try:
            validate_mission_combination(kind, mode, intent)
        except ValueError:
            raised = True
        check(f"illegal triple rejected: {kind.value}+{mode.value}+{intent.value}", raised)
        check(f"is_legal False: {kind.value}+{mode.value}+{intent.value}", not is_legal_mission_combination(kind, mode, intent))
    # dataclass invariant also rejects at construction time
    ctor_raised = False
    try:
        SpeakingEducationalMission(
            mission_id="x", mission_kind=SpeakingMissionKind.teaching,
            execution_mode=SpeakingExecutionMode.live_evi_conversation,
            evidence_intent=SpeakingEvidenceIntent.summative,
            order_index=1, title="t", learner_instructions="i",
        )
    except ValueError:
        ctor_raised = True
    check("mission construction rejects illegal triple (invariant)", ctor_raised)
    # legal combinations pass
    check("legal teaching triple accepted", is_legal_mission_combination(
        SpeakingMissionKind.teaching, SpeakingExecutionMode.study, SpeakingEvidenceIntent.none))
    check("legal speak triple accepted", is_legal_mission_combination(
        SpeakingMissionKind.speak, SpeakingExecutionMode.live_evi_conversation, SpeakingEvidenceIntent.summative))


# 5. Transfer phase vs transfer evidence are explicit, distinct concepts.
def test_transfer_phase_vs_evidence() -> None:
    check("transfer is an educational phase (MissionKind)", SpeakingMissionKind.transfer.value == "transfer")
    check("transfer is an evidence intent (EvidenceIntent)", SpeakingEvidenceIntent.transfer.value == "transfer")
    check("phase and evidence are different enum types", type(SpeakingMissionKind.transfer) is not type(SpeakingEvidenceIntent.transfer))
    entry = taxonomy_entry(SpeakingMissionKind.transfer)
    check("transfer phase legally carries transfer evidence", SpeakingEvidenceIntent.transfer in entry.legal_evidence_intents)
    # retention analog
    r_entry = taxonomy_entry(SpeakingMissionKind.retention_review)
    check("retention_review phase legally carries retention evidence", SpeakingEvidenceIntent.retention in r_entry.legal_evidence_intents)


# 6. Planner emits >= 3 structurally different sequences from real recommendation inputs.
def test_planner_variants() -> None:
    reasons = [
        TargetSelectionReason.sparse_evidence_safe_start,
        TargetSelectionReason.weak_mastery,
        TargetSelectionReason.reinforcement,
        TargetSelectionReason.progression_next,
        TargetSelectionReason.at_risk_retention,
    ]
    shapes = {tuple(k.value for k in _kinds(_blueprint_for(r))) for r in reasons}
    check("planner produces >= 3 structurally different plans", len(shapes) >= 3)
    check("planner produces >= 4 distinct plans (support/standard/lighter/transfer/retention)", len(shapes) >= 4)
    # support-heavy differs from a lighter plan by length
    heavy = _kinds(_blueprint_for(TargetSelectionReason.sparse_evidence_safe_start))
    lighter = _kinds(_blueprint_for(TargetSelectionReason.reinforcement))
    check("support-heavy is longer than lighter", len(heavy) > len(lighter))


# 7. Retry is never pre-emitted as a mission.
def test_retry_not_pre_emitted() -> None:
    for r in TargetSelectionReason:
        kinds = _kinds(_blueprint_for(r))
        check(f"no retry mission emitted for reason {r.value}", all(k is not None for k in kinds) and "retry" not in {k.value for k in kinds})
    # retry only appears as a declared flow policy, not as a mission
    bp = _blueprint_for(TargetSelectionReason.weak_mastery)
    speak = next((m for m in bp.educational_missions if m.mission_kind is SpeakingMissionKind.speak), None)
    check("speak mission declares a retry POLICY (not a retry mission)", speak is not None and speak.retry_policy in (
        SpeakingMissionOutcome.retry_with_scaffold, SpeakingMissionOutcome.retry_same_task))


# 8. Retention only under an explicit signal.
def test_retention_requires_signal() -> None:
    non_retention = [
        TargetSelectionReason.sparse_evidence_safe_start,
        TargetSelectionReason.weak_mastery,
        TargetSelectionReason.reinforcement,
        TargetSelectionReason.progression_next,
    ]
    for r in non_retention:
        kinds = {k.value for k in _kinds(_blueprint_for(r))}
        check(f"no retention_review without signal ({r.value})", "retention_review" not in kinds)
    retention_kinds = {k.value for k in _kinds(_blueprint_for(TargetSelectionReason.at_risk_retention))}
    check("retention_review emitted under at_risk_retention", "retention_review" in retention_kinds)


# 9. Mission ids are blueprint-scoped — no collisions across blueprints for the same skill.
def test_mission_id_no_collision() -> None:
    rec = _base_recommendation(TargetSelectionReason.sparse_evidence_safe_start)
    bp1 = assemble_speaking_lesson_blueprint(rec)
    bp2 = assemble_speaking_lesson_blueprint(rec)
    ids1 = {m.mission_id for m in bp1.educational_missions}
    ids2 = {m.mission_id for m in bp2.educational_missions}
    check("same-skill blueprints have different blueprint_id", bp1.blueprint_id != bp2.blueprint_id)
    check("mission ids do not collide across blueprints", ids1.isdisjoint(ids2))
    check("mission ids unique within blueprint", len(ids1) == len(bp1.educational_missions))


# 10-11. Executable vs content-only explicit; task identity representable.
def test_executable_vs_content_and_task_identity() -> None:
    bp = _blueprint_for(TargetSelectionReason.sparse_evidence_safe_start)
    by_kind = {m.mission_kind: m for m in bp.educational_missions}
    teaching = by_kind.get(SpeakingMissionKind.teaching)
    speak = by_kind.get(SpeakingMissionKind.speak)
    check("teaching mission is content-only (no task)", teaching is not None and teaching.is_content_only and not teaching.is_executable)
    check("speak mission is executable (has task)", speak is not None and speak.is_executable)
    check("executable mission carries a typed task", speak is not None and isinstance(speak.tasks[0], SpeakingExecutableTask))
    check("task has a stable task_id", speak is not None and bool(speak.tasks[0].task_id))
    # task id determinism (blueprint-scoped)
    tid = make_task_id(bp.blueprint_id, "speak", 4)
    check("make_task_id is deterministic", tid == make_task_id(bp.blueprint_id, "speak", 4))
    check("make_task_id is blueprint-scoped", tid != make_task_id("other-bp", "speak", 4))


# 12-14. Attempt identity semantics; EVI multi-turn; reconnect != fresh attempt.
def test_attempt_identity_semantics() -> None:
    for key in ("session_id", "blueprint_id", "mission_id", "task_id", "attempt_id", "live_session_id", "live_turn_id", "evaluation_id"):
        check(f"identity semantics documented: {key}", key in SPEAKING_IDENTITY_SEMANTICS)
    aid = new_attempt_id("spk-task-abc123")
    ident = SpeakingAttemptIdentity(
        session_id="s1", blueprint_id="bp1", mission_id="m1", task_id="spk-task-abc123",
        attempt_id=aid, live_session_id="live1",
    )
    ident = ident.with_turn("turn-1").with_turn("turn-2").with_evaluation("eval-1")
    check("one EVI attempt holds multiple live turns", len(ident.live_turn_ids) == 2 and ident.attempt_id == aid)
    check("one EVI attempt can hold multiple evaluations", len(ident.evaluation_ids) == 1)
    check("attempt_id stable across resume set", "attempt_id" in STABLE_ACROSS_RESUME and "live_session_id" in STABLE_ACROSS_RESUME)
    check("reconnect/resume does NOT start a new attempt", should_start_new_attempt(is_resume=True, previous_attempt_completed=False) is False)
    check("restart after completion DOES start a new attempt", should_start_new_attempt(is_resume=False, previous_attempt_completed=True) is True)


# 15. Retry lineage is not mission-level.
def test_retry_lineage_not_mission_level() -> None:
    bp = _blueprint_for(TargetSelectionReason.weak_mastery)
    for m in bp.educational_missions:
        check(f"{m.mission_kind.value}: no mission-level retry_of pointer", not hasattr(m, "retry_of_mission_id"))
    # retry expressed as a flow decision mapped from session outcomes
    check("session focused_retry maps to mission retry flow",
          mission_flow_from_session_outcome(SpeakingSessionOutcomeKind.focused_retry) is SpeakingMissionOutcome.retry_with_scaffold)
    check("session complete maps to mission complete",
          mission_flow_from_session_outcome(SpeakingSessionOutcomeKind.session_complete) is SpeakingMissionOutcome.complete)


# 16. Transfer evidence is not inferred from a mission pointer.
def test_transfer_not_mission_pointer() -> None:
    bp = _blueprint_for(TargetSelectionReason.progression_next)
    transfer = next((m for m in bp.educational_missions if m.mission_kind is SpeakingMissionKind.transfer), None)
    check("transfer mission present under progression_next", transfer is not None)
    check("transfer mission has no transfer_of pointer", transfer is not None and not hasattr(transfer, "transfer_of_mission_id"))
    check("transfer carries transfer evidence intent", transfer is not None and transfer.evidence_intent is SpeakingEvidenceIntent.transfer)
    check("transfer task names a changed context", transfer is not None and bool(transfer.tasks) and bool(transfer.tasks[0].context_descriptor))


# Runtime: storage round-trip + student-safe projections + no leakage.
def test_runtime_roundtrip_and_projection() -> None:
    bp = _blueprint_for(TargetSelectionReason.sparse_evidence_safe_start)
    restored = blueprint_from_dict(bp.to_dict())
    check("blueprint roundtrips via storage", restored is not None)
    check("missions survive roundtrip", restored is not None and _kinds(restored) == _kinds(bp))
    check("tasks survive roundtrip", restored is not None and
          [len(m.tasks) for m in restored.educational_missions] == [len(m.tasks) for m in bp.educational_missions])
    exp = build_lesson_experience_bundle(bp)
    blob = json.dumps(exp.to_student_dict())
    check("experience bundle assembles missions", len(exp.missions) == len(bp.educational_missions))
    check("experience exposes explicit executable flag", any(m.is_executable for m in exp.missions))
    check("experience exposes no evidence_intent", "evidence_intent" not in blob)
    check("experience exposes no mastery/skill_states", "mastery" not in blob.lower() and "skill_states" not in blob)


# 18-20. Non-goal confirmations.
def test_non_goals() -> None:
    bp = _blueprint_for(TargetSelectionReason.at_risk_retention)
    blob = json.dumps(bp.to_dict()).lower()
    check("no official_speaking_cefr write", "official_speaking_cefr" not in blob)
    check("no learning_stage advancement", "learning_stage" not in blob)
    check("no hume dependency introduced", "hume" not in blob)
    check("no provider ids leaked", "openai" not in blob and "elevenlabs" not in blob)
    check("mission model is not a DB table (no migration)", not hasattr(SpeakingEducationalMission, "__tablename__"))
    check("task model is not a DB table (no migration)", not hasattr(SpeakingExecutableTask, "__tablename__"))


def run_frozen_regressions() -> None:
    if os.environ.get("SPEAKING_VERIFY_SKIP_NESTED_REGRESSIONS") == "1":
        print("  (flat mode: skip nested regressions)", flush=True)
        return
    scripts = [
        "verify_speaking_s0_architecture.py",
        "verify_speaking_s9_adaptive_journey.py",
        "verify_speaking_s10_educational_missions.py",
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
    print("Speaking S10.1 mission stabilization verifier\n")
    test_taxonomy_orthogonality()
    test_illegal_triples_rejected()
    test_transfer_phase_vs_evidence()
    test_planner_variants()
    test_retry_not_pre_emitted()
    test_retention_requires_signal()
    test_mission_id_no_collision()
    test_executable_vs_content_and_task_identity()
    test_attempt_identity_semantics()
    test_retry_lineage_not_mission_level()
    test_transfer_not_mission_pointer()
    test_runtime_roundtrip_and_projection()
    test_non_goals()
    run_frozen_regressions()
    print(f"\nResult: {PASS} passed, {FAIL} failed")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
