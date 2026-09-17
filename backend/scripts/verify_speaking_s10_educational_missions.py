"""Verify Speaking S10 — educational mission foundation.

Proves the S10 contracts and planner/experience/journey integration without any
official CEFR mutation, learning-stage advancement, durable lineage, EVI budget, or
Hume config dependency. Runs the frozen S0 and S9 verifiers as regressions.

Usage (from backend/):
    python scripts/verify_speaking_s10_educational_missions.py
"""

from __future__ import annotations

import os

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.language_speaking.enums import (
    SpeakingEvidenceIntent,
    SpeakingExecutionMode,
    SpeakingMissionKind,
    SpeakingTeachingBlockKind,
)
from app.services.language_speaking_diagnostic.selector import select_speaking_target
from app.services.language_speaking_generation import (
    GENERATION_FORBIDDEN_DECISIONS,
    SpeakingTeachingBlockRequest,
    draft_teaching_block,
)
from app.services.language_speaking_journey.builder import build_speaking_journey_bundle
from app.services.language_speaking_knowledge_model.storage import empty_knowledge_model
from app.services.language_speaking_lesson_experience.builder import build_lesson_experience_bundle
from app.services.language_speaking_lesson_planner.mission_types import (
    SpeakingEducationalMission,
    SpeakingLearningObjective,
    SpeakingTeachingBlock,
    is_teaching_only,
    mission_produces_evidence,
)
from app.services.language_speaking_lesson_planner.planner import assemble_speaking_lesson_blueprint
from app.services.language_speaking_lesson_planner.storage import blueprint_from_dict
from app.services.language_speaking_lesson_planner.task_taxonomy import (
    SPEAKING_MISSION_TAXONOMY,
    taxonomy_is_complete,
)

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


def _blueprint():
    km = empty_knowledge_model(student_id=101, language_id=1)
    rec = select_speaking_target(km, official_cefr="A2")
    return assemble_speaking_lesson_blueprint(rec)


def test_taxonomy_dimensions_distinct() -> None:
    # S10.1 correction: MissionKind holds educational phases ONLY (7), execution modes
    # and `retry` are no longer mission kinds.
    a = {m.value for m in SpeakingMissionKind}
    check("taxonomy A has 7 educational phases", len(a) == 7)
    check("taxonomy dimensions are separate enums", SpeakingMissionKind is not SpeakingExecutionMode)
    check("evidence intent is its own dimension", SpeakingEvidenceIntent is not SpeakingExecutionMode)
    for kind in ("teaching", "noticing", "guided_practice", "speak", "feedback", "transfer", "retention_review"):
        check(f"taxonomy phase present: {kind}", kind in a)
    for removed in ("controlled_speaking", "recorded_speaking", "live_conversation", "retry"):
        check(f"execution/flow value NOT a mission kind: {removed}", removed not in a)
    check("canonical taxonomy registry complete", taxonomy_is_complete())
    check("taxonomy registry has 7 rows", len(SPEAKING_MISSION_TAXONOMY) == 7)


def test_learning_objectives_typed() -> None:
    obj = SpeakingLearningObjective(
        objective_id="obj-1",
        target_skill_id="function:express_opinion",
        student_objective_text="Give an opinion with a reason.",
        expected_outcome="You can support an opinion.",
        evidence_expectation=SpeakingEvidenceIntent.summative,
    )
    check("objective is typed dataclass", isinstance(obj, SpeakingLearningObjective))
    check("objective names a target skill", bool(obj.target_skill_id))
    check("objective has evidence expectation", obj.evidence_expectation is SpeakingEvidenceIntent.summative)
    check("objective serializes", obj.to_dict()["target_skill_id"] == "function:express_opinion")


def test_teaching_blocks_typed_and_not_evidence() -> None:
    block = SpeakingTeachingBlock(
        block_id="tb-1",
        kind=SpeakingTeachingBlockKind.explanation,
        title="What is X",
        body="X helps you speak clearly.",
        target_skill_ids=("s1",),
    )
    check("teaching block is typed", isinstance(block, SpeakingTeachingBlock))
    check("teaching block kind enum", block.kind is SpeakingTeachingBlockKind.explanation)
    check("teaching content is NOT evidence by default", block.is_evidence is False)
    check("teaching block student dict has no evidence flag", "is_evidence" not in block.to_student_dict())


def test_generation_produces_typed_blocks() -> None:
    req = SpeakingTeachingBlockRequest(
        request_id="r1",
        kind=SpeakingTeachingBlockKind.scaffold,
        target_skill_id="function:express_opinion",
        target_skill_label="giving a reason",
    )
    block = draft_teaching_block(req)
    check("generation returns SpeakingTeachingBlock", isinstance(block, SpeakingTeachingBlock))
    check("generated block is not evidence", block.is_evidence is False)
    check("generated block preserves kind", block.kind is SpeakingTeachingBlockKind.scaffold)
    for forbidden in ("mastery", "official_speaking_cefr", "promotion", "learning_stage"):
        check(f"generation forbids deciding: {forbidden}", forbidden in GENERATION_FORBIDDEN_DECISIONS)


def test_missions_ordered_and_referenced() -> None:
    bp = _blueprint()
    missions = bp.educational_missions
    check("blueprint carries educational missions", len(missions) >= 3)
    orders = [m.order_index for m in missions]
    check("missions are strictly ordered", orders == sorted(orders) and len(set(orders)) == len(orders))
    check("missions reference target skills", all(m.target_skill_ids for m in missions))
    check("missions reference objectives (at least some)", any(m.objectives for m in missions))
    # S10.1 correction: executability is explicit via tasks, not an activity_ref string.
    check("some missions are executable (have tasks)", any(m.is_executable for m in missions))
    check("some missions are content-only (no tasks)", any(m.is_content_only for m in missions))
    # teaching content is not evidence by default
    teaching = [m for m in missions if m.mission_kind is SpeakingMissionKind.teaching]
    check("teaching mission is teaching-only", all(is_teaching_only(m) for m in teaching))
    check("teaching mission produces no evidence", all(not mission_produces_evidence(m) for m in teaching))


def test_retry_is_not_a_mission_and_no_pointers() -> None:
    # S10.1 correction: retry is a flow decision, not a mission kind; missions carry no
    # mission-to-mission lineage pointers.
    check("retry is not a mission kind", "retry" not in {m.value for m in SpeakingMissionKind})
    bp = _blueprint()
    for m in bp.educational_missions:
        check(f"mission {m.mission_kind.value} has no retry_of pointer", not hasattr(m, "retry_of_mission_id"))
        check(f"mission {m.mission_kind.value} has no transfer_of pointer", not hasattr(m, "transfer_of_mission_id"))


def test_educational_sequence_representable() -> None:
    # A support-heavy plan represents Learn -> Notice -> Guided -> Speak -> Feedback.
    from app.services.language_speaking_lesson_planner.planner import PLAN_SUPPORT_HEAVY

    expected = [
        SpeakingMissionKind.teaching,
        SpeakingMissionKind.noticing,
        SpeakingMissionKind.guided_practice,
        SpeakingMissionKind.speak,
        SpeakingMissionKind.feedback,
    ]
    check("support-heavy plan = Learn->Notice->Guided->Speak->Feedback", list(PLAN_SUPPORT_HEAVY) == expected)


def test_blueprint_roundtrip() -> None:
    bp = _blueprint()
    restored = blueprint_from_dict(bp.to_dict())
    check("blueprint roundtrips via storage", restored is not None)
    check("missions survive roundtrip", restored is not None and len(restored.educational_missions) == len(bp.educational_missions))
    check("mission kinds survive roundtrip", restored is not None and
          [m.mission_kind for m in restored.educational_missions] == [m.mission_kind for m in bp.educational_missions])


def test_lesson_experience_bundle_student_safe() -> None:
    bp = _blueprint()
    bundle = build_lesson_experience_bundle(bp)
    blob = json.dumps(bundle.to_student_dict())
    check("experience bundle assembles missions", len(bundle.missions) == len(bp.educational_missions))
    check("experience bundle exposes no evidence intent", "evidence_intent" not in blob)
    check("experience bundle exposes no mastery", "mastery" not in blob.lower())
    check("experience bundle exposes no skill_states", "skill_states" not in blob)
    check("experience bundle marks a live mission", any(m.is_live for m in bundle.missions))


def test_journey_projection_missions() -> None:
    bp = _blueprint()
    bundle = build_speaking_journey_bundle(official_level="A2", plan=None, blueprint=bp, session=None)
    student = bundle.to_student_dict()
    check("journey exposes today_missions", "today_missions" in student)
    check("journey missions ordered", [m["order_index"] for m in student["today_missions"]] ==
          sorted(m["order_index"] for m in student["today_missions"]))
    blob = json.dumps(student)
    check("journey missions have no evidence intent", "evidence_intent" not in blob)


def test_no_official_state_mutation() -> None:
    bp = _blueprint()
    blob = json.dumps(bp.to_dict()).lower()
    # S10 must not embed official CEFR writes, stage advancement, or Hume config.
    check("no official_speaking_cefr write in blueprint", "official_speaking_cefr" not in blob)
    check("no learning_stage advancement in blueprint", "learning_stage" not in blob)
    check("no hume config dependency in blueprint", "hume" not in blob)
    check("no provider ids leaked", "openai" not in blob and "elevenlabs" not in blob)


def run_frozen_regressions() -> None:
    if os.environ.get("SPEAKING_VERIFY_SKIP_NESTED_REGRESSIONS") == "1":
        print("  (flat mode: skip nested regressions)", flush=True)
        return
    scripts = [
        "verify_speaking_s0_architecture.py",
        "verify_speaking_s9_adaptive_journey.py",
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
            print(proc.stdout[-3000:] if proc.stdout else "")
            print(proc.stderr[-2000:] if proc.stderr else "")
        check(f"frozen regression {name}", proc.returncode == 0)


def main() -> int:
    print("Speaking S10 educational mission foundation verifier\n")
    test_taxonomy_dimensions_distinct()
    test_learning_objectives_typed()
    test_teaching_blocks_typed_and_not_evidence()
    test_generation_produces_typed_blocks()
    test_missions_ordered_and_referenced()
    test_retry_is_not_a_mission_and_no_pointers()
    test_educational_sequence_representable()
    test_blueprint_roundtrip()
    test_lesson_experience_bundle_student_safe()
    test_journey_projection_missions()
    test_no_official_state_mutation()
    run_frozen_regressions()
    print(f"\nResult: {PASS} passed, {FAIL} failed")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
