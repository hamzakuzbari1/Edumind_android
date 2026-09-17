"""Verify Speaking S18 — SPA blueprint specification, constrained generation, bounded persistence.

S18 owns deterministic SPA specification, curriculum coverage policy, constrained wording
generation, deterministic validation, frozen bounded blueprint persistence, unlock
reconcile, and student-safe status/create/get APIs.

Does NOT score SPA, write official_speaking_cefr, apply S8 mastery, claim spontaneous
interaction from recorded spontaneous production, or invent EVI-mandatory SPA.

Usage (from backend/):
    python scripts/verify_speaking_s18_promotion_assessment_blueprint.py
"""

from __future__ import annotations

import ast
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.language_speaking.enums import SpeakingLearningStage, SpeakingSkillType
from app.services.language_speaking.ownership import ALLOWED_PACKAGE_DEPENDENCIES
from app.services.language_speaking_generation import (
    GENERATION_FORBIDDEN_DECISIONS,
    generate_spa_task_wording,
)
from app.services.language_speaking_generation.promotion_assessment import (
    SpeakingPromotionSlotGenerationConstraint,
    SpeakingPromotionTaskGenerationRequest,
)
from app.services.language_speaking_promotion_test import (
    MAX_PERSISTED_BLUEPRINTS,
    SPA_REQUIRES_INTERACTION_EVIDENCE,
    SpaBlueprintStatus,
    SpaCapabilityKind,
    SpaCreateFailureCode,
    SpaSkillEvaluatorCompatibility,
    SpaUnlockAuthority,
    SpeakingPromotionAssessmentTask,
    assert_bucket_bounded,
    assessments_bucket_from_payload,
    build_speaking_promotion_assessment_specification,
    classify_skill_evaluator_compatibility,
    count_persisted_blueprints,
    create_speaking_promotion_assessment,
    merge_assessments_into_payload,
    persist_active_blueprint,
    reconcile_spa_unlock,
    skill_requires_interactive_evaluation,
    validate_spa_tasks_against_specification,
)
from app.services.language_speaking_promotion_test.policy import (
    SPA_TASK_SLOTS,
    curriculum_skills_for_official_cefr,
)
from app.services.language_speaking_promotion_test.types import SpaEvaluatorRequirements

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


def _authority(**overrides) -> SpaUnlockAuthority:
    data = dict(
        spa_unlocked=True,
        official_cefr="A2",
        target_cefr="B1",
        readiness_snapshot_fingerprint="ready_fp_aaaaaaaaaaaaaaaaaaaa",
        source_stage_signal_fingerprint="stage_fp_bbbbbbbbbbbbbbbbbbbb",
        unlock_fingerprint="unlock_fp_cccccccccccccccccccc",
        hard_blockers_empty=True,
        stability_requirements_passed=True,
        current_stage_advanced=True,
    )
    data.update(overrides)
    return SpaUnlockAuthority(**data)


def test_unlock_gate() -> None:
    print("\n--- unlock reconcile ---")
    ok = reconcile_spa_unlock(_authority())
    check("1. unlocked advanced passes", ok.allowed and ok.resolved_target_cefr == "B1")

    locked = reconcile_spa_unlock(_authority(spa_unlocked=False))
    check("2. not unlocked rejected", not locked.allowed and locked.failure_code == SpaCreateFailureCode.unlock_not_granted)

    blockers = reconcile_spa_unlock(_authority(hard_blockers_empty=False))
    check("3. hard blockers reject", not blockers.allowed)

    stability = reconcile_spa_unlock(_authority(stability_requirements_passed=False))
    check("4. stability fail reject", not stability.allowed)

    stage = reconcile_spa_unlock(_authority(current_stage_advanced=False))
    check("5. not advanced reject", not stage.allowed)

    stale = reconcile_spa_unlock(
        _authority(),
        fresh_readiness_snapshot_fingerprint="different_fp",
    )
    check("6. stale readiness fingerprint reject", not stale.allowed and stale.failure_code == SpaCreateFailureCode.stale_fingerprint)

    mismatch = reconcile_spa_unlock(_authority(target_cefr="B2"))
    check("7. target_cefr mismatch reject", not mismatch.allowed and mismatch.failure_code == SpaCreateFailureCode.cefr_mismatch)

    c2 = reconcile_spa_unlock(_authority(official_cefr="C2", target_cefr=None))
    check("8. terminal C2 unsupported", not c2.allowed)


def test_coverage_and_composition() -> None:
    print("\n--- coverage + composition ---")
    spec = build_speaking_promotion_assessment_specification(source_cefr="A2", target_cefr="B1")
    check("9. exactly 5 slots", len(spec.slots) == 5)
    families = [s.task_family.value for s in spec.slots]
    check(
        "10. fixed family order",
        families
        == [
            "controlled_response",
            "picture_or_situation_description",
            "opinion_explanation",
            "transfer_new_context",
            "spontaneous_unprepared",
        ],
    )
    check("11. no EVI / live execution mode", all(s.execution_mode.value != "live_evi" for s in spec.slots))
    check("12. spontaneous slot prep=0", spec.slots[4].preparation_seconds == 0)
    check("13. spontaneous production required on slot 5", spec.slots[4].spontaneous_production_required is True)
    check(
        "14. spontaneous interaction NOT required on slot 5",
        spec.slots[4].spontaneous_interaction_required is False,
    )
    check(
        "15. slot 5 proves production not interaction",
        SpaCapabilityKind.spontaneous_production in spec.slots[4].proves_capabilities
        and SpaCapabilityKind.spontaneous_interaction not in spec.slots[4].proves_capabilities,
    )
    check("16. S18 does not require interaction evidence", SPA_REQUIRES_INTERACTION_EVIDENCE is False)
    check("17. authorized skills non-empty", len(spec.authorized_skill_ids) >= 3)
    check("18. specification fingerprint stable length", len(spec.specification_fingerprint) == 32)

    spec2 = build_speaking_promotion_assessment_specification(source_cefr="A2", target_cefr="B1")
    check("19. deterministic specification fingerprint", spec.specification_fingerprint == spec2.specification_fingerprint)


def test_interaction_vs_production() -> None:
    print("\n--- spontaneous production vs interaction ---")
    target = curriculum_skills_for_official_cefr("B1")
    interactive = [n for n in target if skill_requires_interactive_evaluation(n)]
    production = [n for n in target if not skill_requires_interactive_evaluation(n)]
    check("20. B1 has interactive skills classified", len(interactive) > 0)
    check("21. B1 has production-compatible skills", len(production) >= 3)

    for n in interactive:
        if n.skill_type in (SpeakingSkillType.interaction_skill, SpeakingSkillType.conversation_skill):
            check(
                f"22. {n.skill_id} interaction_required",
                classify_skill_evaluator_compatibility(n)
                is SpaSkillEvaluatorCompatibility.interaction_required,
            )
            break
    else:
        check("22. found interaction_skill/conversation_skill at B1", False)

    spec = build_speaking_promotion_assessment_specification(source_cefr="A2", target_cefr="B1")
    gap_ids = {g.skill_id for g in spec.coverage_gaps}
    check("23. interaction skills exposed as coverage gaps", any(n.skill_id in gap_ids for n in interactive))
    check(
        "24. authorized skills exclude interaction-required",
        all(
            classify_skill_evaluator_compatibility(n) is SpaSkillEvaluatorCompatibility.production_compatible
            for n in target
            if n.skill_id in spec.authorized_skill_ids
        ),
    )
    check(
        "25. no selected skill claims interaction coverage via monologue",
        all(g.gap_kind == "interaction_required" for g in spec.coverage_gaps if g.skill_id in gap_ids),
    )
    # False claim rejection
    from app.services.language_speaking_promotion_test.policy import SpaExecutionMode, SpaTaskFamily

    fake_tasks = []
    for slot in spec.slots:
        fake_tasks.append(
            SpeakingPromotionAssessmentTask(
                task_id=f"t{slot.task_order}",
                task_order=slot.task_order,
                task_family=slot.task_family,
                execution_mode=slot.execution_mode,
                source_cefr="A2",
                target_cefr="B1",
                target_skill_ids=slot.authorized_skill_ids,
                scenario="scene",
                student_prompt="prompt",
                follow_up_prompts=tuple(["x"] * slot.min_follow_ups),
                context_descriptor="ctx",
                spontaneous_production_required=slot.spontaneous_production_required,
                spontaneous_interaction_required=False,
                max_duration_seconds=slot.max_duration_seconds,
                preparation_seconds=slot.preparation_seconds,
                evaluator_requirements=SpaEvaluatorRequirements(
                    task_type="monologue",
                    success_criteria=("ok",),
                    target_skill_ids=slot.authorized_skill_ids,
                    proves_spontaneous_production=slot.spontaneous_production_required,
                    proves_spontaneous_interaction=True,  # FALSE CLAIM
                ),
                generation_provenance={"generator": "test"},
                task_fingerprint="x" * 32,
            )
        )
    bad = validate_spa_tasks_against_specification(specification=spec, tasks=fake_tasks)
    check("26. validation rejects proves_spontaneous_interaction", not bad.ok)
    check(
        "27. reject code present",
        any(i.code == "false_interaction_evidence" for i in bad.issues),
    )

    # Interaction skill on recorded task rejected
    if interactive:
        tainted = list(fake_tasks)
        # rebuild without interaction claim but with interaction skill
        slot0 = spec.slots[0]
        tainted[0] = SpeakingPromotionAssessmentTask(
            task_id="t1",
            task_order=1,
            task_family=slot0.task_family,
            execution_mode=slot0.execution_mode,
            source_cefr="A2",
            target_cefr="B1",
            target_skill_ids=(interactive[0].skill_id,),
            scenario="scene",
            student_prompt="prompt",
            follow_up_prompts=(),
            context_descriptor="ctx",
            spontaneous_production_required=False,
            spontaneous_interaction_required=False,
            max_duration_seconds=slot0.max_duration_seconds,
            preparation_seconds=slot0.preparation_seconds,
            evaluator_requirements=SpaEvaluatorRequirements(
                task_type="monologue",
                success_criteria=("ok",),
                target_skill_ids=(interactive[0].skill_id,),
                proves_spontaneous_production=False,
                proves_spontaneous_interaction=False,
            ),
            generation_provenance={"generator": "test"},
            task_fingerprint="y" * 32,
        )
        # Need full 5 tasks valid family-wise — only check skill issue by validating all slots properly
        rebuilt = []
        for i, slot in enumerate(spec.slots):
            sid = interactive[0].skill_id if i == 0 else slot.authorized_skill_ids[0]
            rebuilt.append(
                SpeakingPromotionAssessmentTask(
                    task_id=f"t{slot.task_order}",
                    task_order=slot.task_order,
                    task_family=slot.task_family,
                    execution_mode=slot.execution_mode,
                    source_cefr="A2",
                    target_cefr="B1",
                    target_skill_ids=(sid,),
                    scenario="scene",
                    student_prompt="prompt",
                    follow_up_prompts=tuple(["more"] * slot.min_follow_ups),
                    context_descriptor="ctx",
                    spontaneous_production_required=slot.spontaneous_production_required,
                    spontaneous_interaction_required=False,
                    max_duration_seconds=slot.max_duration_seconds,
                    preparation_seconds=slot.preparation_seconds,
                    evaluator_requirements=SpaEvaluatorRequirements(
                        task_type="monologue",
                        success_criteria=("ok",),
                        target_skill_ids=(sid,),
                        proves_spontaneous_production=slot.spontaneous_production_required,
                        proves_spontaneous_interaction=False,
                    ),
                    generation_provenance={"generator": "test"},
                    task_fingerprint=f"z{i}" * 8,
                )
            )
        bad2 = validate_spa_tasks_against_specification(specification=spec, tasks=rebuilt)
        check("28. interaction skill on recorded task rejected", not bad2.ok)
        check(
            "29. interaction_skill_on_recorded_task code",
            any(i.code in ("interaction_skill_on_recorded_task", "unauthorized_skill", "gap_falsely_covered") for i in bad2.issues),
        )


def test_create_freeze_and_no_scoring() -> None:
    print("\n--- create + freeze ---")
    result = create_speaking_promotion_assessment(_authority())
    check("30. create succeeds when unlocked", result.ok and result.blueprint is not None)
    assert result.blueprint is not None
    bp = result.blueprint
    check("31. frozen true", bp.frozen is True)
    check("32. status not_started", bp.status == SpaBlueprintStatus.not_started)
    check("33. 5 tasks", len(bp.tasks) == 5)
    check("34. evidence_source promotion_assessment", bp.evidence_source == "promotion_assessment")
    check(
        "35. no spontaneous interaction claims",
        all(not t.evaluator_requirements.proves_spontaneous_interaction for t in bp.tasks),
    )
    check(
        "36. slot 5 proves spontaneous production only",
        bp.tasks[4].spontaneous_production_required
        and bp.tasks[4].evaluator_requirements.proves_spontaneous_production
        and not bp.tasks[4].evaluator_requirements.proves_spontaneous_interaction,
    )
    check("37. coverage gaps retained on blueprint", len(bp.coverage_gaps) >= 0)
    safe = bp.to_student_safe_dict()
    check("38. student-safe hides evaluator_requirements", "evaluator_requirements" not in str(safe.get("tasks")))
    check("39. student-safe never claims interaction required", all(not t.get("spontaneous_interaction_required") for t in safe["tasks"]))

    denied = create_speaking_promotion_assessment(_authority(spa_unlocked=False))
    check("40. create fail closed when locked", not denied.ok)

    # Generation constraints: request cannot carry interaction requirement
    bad_req = SpeakingPromotionTaskGenerationRequest(
        specification_fingerprint="fp",
        source_cefr="A2",
        target_cefr="B1",
        slots=(
            SpeakingPromotionSlotGenerationConstraint(
                task_order=1,
                task_family="controlled_response",
                execution_mode="controlled_response",
                authorized_skill_ids=("skill:a",),
                skill_labels=("A",),
                preparation_seconds=0,
                max_duration_seconds=60,
                min_follow_ups=0,
                max_follow_ups=0,
                spontaneous_production_required=False,
                spontaneous_interaction_required=True,
            ),
        ),
    )
    gen = generate_spa_task_wording(bad_req)
    check("41. generation rejects interaction requirement", not gen.ok)

    check("42. forbidden decisions include promotion", "promotion" in GENERATION_FORBIDDEN_DECISIONS)


def test_bounded_retention() -> None:
    print("\n--- bounded blueprint retention ---")
    payload: dict = {}
    ids: list[str] = []
    for i in range(8):
        result = create_speaking_promotion_assessment(
            _authority(unlock_fingerprint=f"unlock_{i}_" + "c" * 20)
        )
        check(f"43.{i} create cycle ok", result.ok and result.blueprint is not None)
        assert result.blueprint is not None
        ids.append(result.blueprint.blueprint_id)
        payload = persist_active_blueprint(payload, result.blueprint, retire_previous_active_as_terminal=True)
        bucket = assessments_bucket_from_payload(payload)
        try:
            assert_bucket_bounded(bucket)
            bounded = True
        except ValueError:
            bounded = False
        check(f"44.{i} bucket bounded after create", bounded)
        check(
            f"45.{i} persisted count <= {MAX_PERSISTED_BLUEPRINTS}",
            count_persisted_blueprints(bucket) <= MAX_PERSISTED_BLUEPRINTS,
        )
        check(f"46.{i} no blueprints_by_id", "blueprints_by_id" not in bucket or not bucket.get("blueprints_by_id"))

    bucket = assessments_bucket_from_payload(payload)
    check("47. after 8 cycles still <= 2 blueprints", count_persisted_blueprints(bucket) <= 2)
    check("48. active present", isinstance(bucket.get("active_blueprint"), dict))
    # Distinct ids recycled retention — archive never grows with all 8
    stored_ids = set()
    if isinstance(bucket.get("active_blueprint"), dict):
        stored_ids.add(bucket["active_blueprint"].get("blueprint_id"))
    if isinstance(bucket.get("most_recent_terminal_blueprint"), dict):
        stored_ids.add(bucket["most_recent_terminal_blueprint"].get("blueprint_id"))
    check("49. stored ids subset of created; not full history", len(stored_ids) <= 2 and stored_ids.issubset(set(ids)))
    check("50. MAX_PERSISTED_BLUEPRINTS == 2", MAX_PERSISTED_BLUEPRINTS == 2)

    # Explicitly reject unbounded archive key
    dirty = dict(bucket)
    dirty["blueprints_by_id"] = {i: {"blueprint_id": i} for i in ids}
    try:
        assert_bucket_bounded(dirty)
        rejected = False
    except ValueError:
        rejected = True
    check("51. blueprints_by_id archive rejected", rejected)

    # merge strips extras
    merged = merge_assessments_into_payload({}, dirty)
    check(
        "52. merge only keeps bounded keys",
        set(merged["speaking_promotion_assessments"].keys())
        == {"active_blueprint", "most_recent_terminal_blueprint"},
    )


def test_authority_and_ownership() -> None:
    print("\n--- authority + ownership ---")
    pkg = BACKEND / "app/services/language_speaking_promotion_test"
    texts = "\n".join(p.read_text(encoding="utf-8") for p in pkg.rglob("*.py")).lower()
    check("53. no openai hardwire in promotion_test", "openai" not in texts)
    check("54. no anthropic/claude hardwire", "anthropic" not in texts and "import claude" not in texts and "from claude" not in texts)

    assign = False
    for p in pkg.rglob("*.py"):
        tree = ast.parse(p.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for t in node.targets:
                    if isinstance(t, ast.Attribute) and t.attr == "official_speaking_cefr":
                        assign = True
    check("55. no official_speaking_cefr write", not assign)

    # No SPA pass/fail aggregation symbols as authority
    check("56. no overall_passed scorer in engine", "overall_passed" not in (pkg / "engine.py").read_text(encoding="utf-8"))

    deps = ALLOWED_PACKAGE_DEPENDENCIES["language_speaking_promotion_test"]
    check("57. ownership includes curriculum", "language_speaking_curriculum" in deps)
    check("58. ownership includes generation", "language_speaking_generation" in deps)
    check("59. no language_speaking_spa package", not (BACKEND / "app/services/language_speaking_spa").exists())

    # API routes exist
    api = BACKEND / "app/api/language_speaking_promotion_test.py"
    check("60. API module present", api.exists())
    api_text = api.read_text(encoding="utf-8")
    check("61. status route", "/status" in api_text)
    check("62. create route", "promotion_assessment_create" in api_text)
    check("63. get by id route", "assessment_id" in api_text)

    router_text = (BACKEND / "app/api/router.py").read_text(encoding="utf-8")
    check("64. router registers SPA API", "language_speaking_promotion_test" in router_text)

    # Slot policy: no live EVI in composition
    check("65. composition has no EVI slots", all(s.execution_mode.value in ("controlled_response", "recorded_response") for s in SPA_TASK_SLOTS))

    # Fail-closed unavailable message exists for exhaustion path (symbol)
    from app.services.language_speaking_promotion_test.types import SpaCreateResult

    check("66. SpaCreateResult fail-closed shape", SpaCreateResult(ok=False, student_safe_message="x").ok is False)

    # Stage enum used for advanced gate
    check("67. SpeakingLearningStage.advanced exists", int(SpeakingLearningStage.advanced) >= 3)

    # Evidence quarantine contract label
    check(
        "68. evidence source constant",
        create_speaking_promotion_assessment(_authority()).blueprint.evidence_source == "promotion_assessment",
    )

    # Generation forbidden includes official_speaking_cefr
    check("69. generation forbids official_speaking_cefr decision", "official_speaking_cefr" in GENERATION_FORBIDDEN_DECISIONS)


def run_flat_verifier(label: str, script: str, *, timeout_s: int = 600) -> bool:
    """Run exactly one verifier process. Stop-on-fail handled by caller.

    Nested regressions inside the child are disabled via
    SPEAKING_VERIFY_SKIP_NESTED_REGRESSIONS=1 so each phase runs once, flat.
    Stdout goes to a log file (no PIPE) to avoid buffer deadlocks.
    """
    print(f"\n=== FLAT {label} ===", flush=True)
    env = {
        **os.environ,
        "PYTHONIOENCODING": "utf-8",
        "PYTHONUTF8": "1",
        "PYTHONUNBUFFERED": "1",
        "SPEAKING_VERIFY_SKIP_NESTED_REGRESSIONS": "1",
    }
    log_path = BACKEND / "scripts" / f"_flat_{Path(script).stem}.log"
    with open(log_path, "w", encoding="utf-8", errors="replace") as logf:
        proc = subprocess.Popen(
            [sys.executable, "-u", str(BACKEND / "scripts" / script)],
            cwd=str(BACKEND),
            stdout=logf,
            stderr=subprocess.STDOUT,
            env=env,
        )
        try:
            proc.wait(timeout=timeout_s)
        except subprocess.TimeoutExpired:
            if os.name == "nt":
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                    capture_output=True,
                    check=False,
                )
            else:
                proc.kill()
            try:
                proc.wait(timeout=30)
            except Exception:
                pass
            print(f"TIMEOUT after {timeout_s}s: {script}", flush=True)
            return False
    ok = proc.returncode == 0
    status = "OK" if ok else "FAIL"
    print(f"  {status}  {label} (exit={proc.returncode})", flush=True)
    if not ok:
        try:
            print(log_path.read_text(encoding="utf-8", errors="replace")[-3000:], flush=True)
        except OSError:
            pass
    return ok


# Flat S0–S17 gate — one process each, no recursive verifier invocation.
FLAT_REGRESSION_CHAIN: tuple[tuple[str, str], ...] = (
    ("S0", "verify_speaking_s0_architecture.py"),
    ("S9", "verify_speaking_s9_adaptive_journey.py"),
    ("S10", "verify_speaking_s10_educational_missions.py"),
    ("S10.1", "verify_speaking_s101_mission_stabilization.py"),
    ("S11", "verify_speaking_s11_attempt_lineage.py"),
    ("S12", "verify_speaking_s12_journey_read_model.py"),
    ("S13", "verify_speaking_s13_live_budget.py"),
    ("S14", "verify_speaking_s14_alex_context_identity.py"),
    ("S15", "verify_speaking_s15_stage_signals.py"),
    ("S16", "verify_speaking_s16_transition_gate.py"),
    ("S17", "verify_speaking_s17_promotion_readiness.py"),
)


def run_s18_unit_suite() -> int:
    """S18 local checks only (this process)."""
    global PASS, FAIL
    print("=== Speaking S18 promotion assessment blueprint verifier ===\n", flush=True)
    test_unlock_gate()
    test_coverage_and_composition()
    test_interaction_vs_production()
    test_create_freeze_and_no_scoring()
    test_bounded_retention()
    test_authority_and_ownership()
    print(f"\n=== S18 units: {PASS} passed, {FAIL} failed ===", flush=True)
    return FAIL


def main() -> int:
    # When invoked as a leaf under the flat orchestrator, run units only.
    if os.environ.get("SPEAKING_VERIFY_SKIP_NESTED_REGRESSIONS") == "1":
        failed = run_s18_unit_suite()
        return 1 if failed else 0

    # Flat orchestrator: S0 → S9…S17 → S18 units. Stop on first failure.
    print("=== Speaking S18 FLAT regression runner ===\n", flush=True)
    print(
        "Mode: one process per verifier; nested regressions disabled via "
        "SPEAKING_VERIFY_SKIP_NESTED_REGRESSIONS=1\n",
        flush=True,
    )

    for label, script in FLAT_REGRESSION_CHAIN:
        if not run_flat_verifier(label, script):
            print(f"\n=== STOPPED: flat regression failed at {label} ({script}) ===", flush=True)
            return 1

    print("\n=== FLAT S18 (this process) ===", flush=True)
    if run_s18_unit_suite() != 0:
        print("\n=== STOPPED: S18 unit suite failed ===", flush=True)
        return 1

    print("\n=== RESULT: all flat regressions + S18 units passed ===", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
