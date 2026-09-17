"""Verify Writing W7 Evaluation & Revision Runtime."""

from __future__ import annotations

import ast
import importlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

BACKEND = Path(__file__).resolve().parents[1]
SERVICES = BACKEND / "app" / "services"

from app.services.language_writing.enums import OfficialWritingCEFR, WritingGoal  # noqa: E402
from app.services.language_writing.ownership import (  # noqa: E402
    ALLOWED_PACKAGE_DEPENDENCIES,
    ARCHITECTURE_LAYERS,
    PACKAGE_LAYER,
    PACKAGE_OWNERSHIP,
)
from app.services.language_writing_curriculum.goal_profiles import profile_for_goal  # noqa: E402
from app.services.language_writing_evaluator.blueprint_snapshot import blueprint_snapshot_from_dict  # noqa: E402
from app.services.language_writing_evaluator.engine import evaluate_draft, evaluate_writing_draft_sync  # noqa: E402
from app.services.language_writing_evaluator.evaluation_facts_types import EVALUATION_FACTS_VERSION  # noqa: E402
from app.services.language_writing_evaluator.evaluation_result import EVALUATION_RESULT_VERSION  # noqa: E402
from app.services.language_writing_explainability.facts_assembler import assemble_writing_facts  # noqa: E402
from app.services.language_writing_explainability.writing_narrative import build_writing_learning_narrative  # noqa: E402
from app.services.language_writing_coach.renderer import render_revision_plan, COACH_RENDERER_VERSION  # noqa: E402
from app.services.language_writing_coach.types import CoachInputBundle, CoachNarrativeContext  # noqa: E402
from app.services.language_writing_revision.comparison import compare_evaluation_facts, ComparisonChange  # noqa: E402
from app.services.language_writing_revision.completion import decide_completion  # noqa: E402
from app.services.language_writing_revision.persistence import (  # noqa: E402
    WRITING_EVALUATION_FACTS_KEY,
    persist_revision_turn,
)
from app.services.language_writing_evaluation_runtime.pipeline import process_writing_draft_turn_sync  # noqa: E402
from app.services.language_writing_evaluation_runtime.types import EVALUATION_RUNTIME_VERSION  # noqa: E402
from app.services.language_writing_lesson_planner.planner_contract import assemble_blueprint  # noqa: E402
from app.services.language_writing_lesson_planner.types import LessonPlannerInput  # noqa: E402
from app.services.language_writing_generation import WRITING_BLUEPRINT_KEY  # noqa: E402
from app.services.language_writing_topic_universe.registry import get_universe_catalog  # noqa: E402


def _ok(name: str, passed: bool, detail: str = "") -> bool:
    status = "PASS" if passed else "FAIL"
    suffix = f" — {detail}" if detail else ""
    print(f"  {name}: {status}{suffix}")
    return passed


def _parse_imports(py_file: Path) -> set[str]:
    tree = ast.parse(py_file.read_text(encoding="utf-8"))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("app.services."):
            parts = node.module.split(".")
            if len(parts) >= 3 and parts[2].startswith("language_writing"):
                if parts[2] == "language_writing":
                    continue
                imports.add(parts[2])
    return imports


def _sample_body(goal: WritingGoal) -> dict:
    from app.services.language_writing_curriculum.selector import select_writing_curriculum_node

    sel = select_writing_curriculum_node(
        goal=goal,
        official_cefr=OfficialWritingCEFR.B1,
        completed_node_ids=frozenset(),
    )
    node = sel.node
    bp = assemble_blueprint(
        LessonPlannerInput(
            official_cefr=OfficialWritingCEFR.B1,
            goal_profile=profile_for_goal(goal),
            selected_node=node,
            blueprint_id=f"w7:{goal.value}",
        )
    ).blueprint
    return {WRITING_BLUEPRINT_KEY: bp.to_dict(), "writing_generation": {"generation_hash": "test"}}


def check_evaluator_correctness() -> list[bool]:
    results: list[bool] = []
    body = _sample_body(WritingGoal.travel)
    snapshot = blueprint_snapshot_from_dict(body[WRITING_BLUEPRINT_KEY])
    draft = (
        "Dear Sir or Madam,\n\n"
        "I am writing to complain about my delayed flight. Because the flight was late, I missed my connection. "
        "I would like a refund and an apology. The announcement was unclear and the staff were unhelpful.\n\n"
        "I used the words refund and apologize in this email about boarding and delay issues.\n\n"
        "Regards,\nAlex"
    )
    result, facts = evaluate_draft(draft, draft_id="d1", revision_number=1, blueprint=snapshot)
    results.append(_ok("evaluator returns result", bool(result.dimension_scores)))
    results.append(_ok("evaluation facts version", facts.evaluator_version == EVALUATION_FACTS_VERSION))
    results.append(_ok("grammar result present", facts.grammar_result.dimension == "grammar"))
    results.append(_ok("vocabulary result present", facts.vocabulary_result.dimension == "vocabulary"))
    results.append(_ok("success criteria status", len(facts.success_criteria_status) > 0))
    results.append(_ok("evaluator has to_facts_dict", hasattr(result, "to_facts_dict")))
    eval_text = json.dumps(result.to_facts_dict())
    results.append(_ok("evaluator output no encouragement", "encouragement" not in eval_text.lower()))
    return results


def check_coach_separation() -> list[bool]:
    results: list[bool] = []
    eval_deps = set()
    for py in (SERVICES / "language_writing_evaluator").glob("*.py"):
        eval_deps |= _parse_imports(py)
    results.append(_ok("evaluator does not import coach", "language_writing_coach" not in eval_deps))

    coach_renderer = (SERVICES / "language_writing_coach" / "renderer.py").read_text(encoding="utf-8")
    results.append(_ok("coach renderer exists", (SERVICES / "language_writing_coach" / "renderer.py").is_file()))
    results.append(_ok("coach renderer no evaluate_draft", "evaluate_draft" not in coach_renderer))
    results.append(_ok("coach renderer no score computation", "grammar_weight" not in coach_renderer))

    body = _sample_body(WritingGoal.business)
    snapshot = blueprint_snapshot_from_dict(body[WRITING_BLUEPRINT_KEY])
    draft = "Dear team, I would like to schedule a meeting to discuss the agenda. Could you please confirm your available times?"
    evaluation, facts = evaluate_draft(draft, draft_id="d2", revision_number=1, blueprint=snapshot)
    eng = evaluate_writing_draft_sync(draft, draft_id="d2", revision_number=1, blueprint=snapshot)
    bundle = assemble_writing_facts(blueprint=snapshot, evaluation=eng)
    narrative = build_writing_learning_narrative(bundle, eng)
    from app.services.language_writing_coach.priority import select_educational_priority  # noqa: E402

    plan = render_revision_plan(
        CoachInputBundle(evaluation=evaluation, goal_profile=profile_for_goal(WritingGoal.business), narrative_coach_summary=narrative.coach_summary),
        CoachNarrativeContext(
            coach_summary=narrative.coach_summary,
            focus_sentence=narrative.focus_sentence,
            improvement_context=narrative.improvement_context,
            strengths_summary=narrative.strengths_summary,
            priority_area=narrative.priority_area,
        ),
        evaluation=eng,
        priority=select_educational_priority(evaluation=eng, goal_label=profile_for_goal(WritingGoal.business).label),
        personality=profile_for_goal(WritingGoal.business).coach_defaults.personality,
        revision_turn=1,
    )
    results.append(_ok("coach plan has encouragement", bool(plan.encouragement.strip())))
    results.append(_ok("coach plan has main_issue", bool(plan.main_issue.strip())))
    results.append(_ok("coach ready_to_complete from evaluation", plan.ready_to_complete == eng.revision_readiness.ready))
    results.append(_ok("coach goal-specific recommendation", "workplace email" in plan.next_lesson_recommendation.lower()))
    results.append(_ok("coach renderer version", COACH_RENDERER_VERSION == "8.0.0"))
    bad = evaluate_writing_draft_sync("My name are Hamza", draft_id="bad", revision_number=1, blueprint=snapshot)
    results.append(_ok("bad draft fails grammar", not bad.grammar.passed))
    results.append(_ok("bad draft explains agreement", any("subject-verb" in i.lower() for i in bad.explanation.improvements)))
    results.append(_ok("bad draft not ready", not bad.revision_readiness.ready))
    return results


def check_revision_loop() -> list[bool]:
    results: list[bool] = []
    body = _sample_body(WritingGoal.ielts)
    draft1 = "I am interested in this major because it connects to my career goals."
    r1, b1 = process_writing_draft_turn_sync(student_id=1, content_item_id=99, draft_text=draft1, body_json=body)
    results.append(_ok("first draft turn success", r1.success))
    results.append(_ok("first draft does not auto-complete", not r1.completed))
    results.append(_ok("revision number increments", r1.revision_number == 1))

    draft2 = draft1 + " Therefore, I plan to study hard and use linking words because this subject interests me."
    r2, b2 = process_writing_draft_turn_sync(student_id=1, content_item_id=99, draft_text=draft2, body_json=b1)
    results.append(_ok("second draft turn success", r2.success))
    results.append(_ok("re-evaluation revision number", r2.revision_number == 2))
    results.append(_ok("comparison on second turn", r2.comparison is not None))
    return results


def check_completion_rules() -> list[bool]:
    results: list[bool] = []
    body = _sample_body(WritingGoal.travel)
    snapshot = blueprint_snapshot_from_dict(body[WRITING_BLUEPRINT_KEY])
    strong = (
        "Dear Customer Service,\n\n"
        "I am writing to complain about my delayed flight because the boarding was late. "
        "I missed my connection and I would like a refund and an apology for this delay. "
        "The announcement was unclear and I felt the staff did not help enough. "
        "Please respond soon.\n\nRegards,\nSam"
    ) * 2
    eng = evaluate_writing_draft_sync(strong, draft_id="d3", revision_number=1, blueprint=snapshot)
    decision = eng.completion
    results.append(_ok("completion decision object", hasattr(decision, "eligible")))
    results.append(_ok("completion uses criteria counts", decision.criteria_total > 0))
    return results


def check_version_comparison() -> list[bool]:
    results: list[bool] = []
    body = _sample_body(WritingGoal.business)
    snapshot = blueprint_snapshot_from_dict(body[WRITING_BLUEPRINT_KEY])
    _, f1 = evaluate_draft("Short.", draft_id="a", revision_number=1, blueprint=snapshot)
    _, f2 = evaluate_draft(
        "Dear colleague, I would like to schedule a meeting about the project agenda. Could you please confirm?",
        draft_id="b",
        revision_number=2,
        blueprint=snapshot,
    )
    cmp = compare_evaluation_facts(f1, f2)
    results.append(_ok("comparison has dimensions", len(cmp.dimensions) >= 5))
    results.append(_ok("comparison structured buckets", bool(cmp.improved or cmp.unchanged or cmp.regressed)))
    results.append(_ok("comparison has summary", bool(cmp.improvement_summary)))
    improved = any(d.change == ComparisonChange.improved for d in cmp.dimensions)
    results.append(_ok("detects improvement possible", improved or len(cmp.improved) > 0))
    return results


def check_persistence() -> list[bool]:
    results: list[bool] = []
    body = _sample_body(WritingGoal.travel)
    r, updated = process_writing_draft_turn_sync(
        student_id=1,
        content_item_id=50,
        draft_text="Dear team, I write about delay and refund because the flight was late.",
        body_json=body,
    )
    results.append(_ok("persist evaluation facts key", WRITING_EVALUATION_FACTS_KEY in updated))
    results.append(_ok("persist revision session", "writing_revision_session" in updated))
    results.append(_ok("persist coach plan", "writing_coach_plan" in updated))
    results.append(_ok("persist completion", "writing_completion" in updated))
    facts = updated.get(WRITING_EVALUATION_FACTS_KEY) or {}
    results.append(_ok("facts include blueprint hash", bool(facts.get("blueprint_hash")) if isinstance(facts, dict) else False))
    return results


def check_architecture() -> list[bool]:
    results: list[bool] = []
    results.append(_ok("evaluation runtime in ownership", "language_writing_evaluation_runtime" in PACKAGE_OWNERSHIP))
    results.append(_ok("runtime version 8.1.0", EVALUATION_RUNTIME_VERSION == "8.1.0"))
    results.append(_ok("canonical evaluation version", EVALUATION_RESULT_VERSION == "8.1.0"))
    results.append(_ok("educational analyzer in ownership", "language_writing_educational_analyzer" in PACKAGE_OWNERSHIP))
    layer_index = {n: i for i, n in enumerate(ARCHITECTURE_LAYERS)}
    results.append(_ok("evaluation before facts layer", layer_index["evaluation"] < layer_index["facts"]))
    results.append(_ok("facts before pedagogy", layer_index["facts"] < layer_index["pedagogy"]))
    results.append(_ok("pedagogy before evaluation_runtime", layer_index["pedagogy"] < layer_index["evaluation_runtime"]))
    deps = set()
    for py in (SERVICES / "language_writing_evaluation_runtime").glob("*.py"):
        deps |= _parse_imports(py)
    allowed = ALLOWED_PACKAGE_DEPENDENCIES.get("language_writing_evaluation_runtime", frozenset())
    results.append(_ok("evaluation runtime deps allowed", deps <= allowed | {"language_writing_evaluation_runtime"}))
    results.append(_ok("manual QA checklist", (SERVICES / "language_writing_evaluation_runtime" / "MANUAL_QA_CHECKLIST.md").is_file() or (SERVICES / "language_writing_evaluation_runtime" / "MANUAL_QA_CHECKLIST.md").exists()))
    return results


def check_imports() -> list[bool]:
    results: list[bool] = []
    for mod in (
        "app.services.language_writing_evaluator.engine",
        "app.services.language_writing_coach.renderer",
        "app.services.language_writing_revision.comparison",
        "app.services.language_writing_evaluation_runtime.pipeline",
    ):
        try:
            importlib.import_module(mod)
            results.append(_ok(f"import {mod.split('.')[-1]}", True))
        except Exception as exc:  # noqa: BLE001
            results.append(_ok(f"import {mod.split('.')[-1]}", False, str(exc)))
    return results


def main() -> int:
    print("Writing W7 Evaluation & Revision Runtime Verification\n")
    sections = [
        ("Evaluator correctness", check_evaluator_correctness),
        ("Coach separation", check_coach_separation),
        ("Revision loop", check_revision_loop),
        ("Completion rules", check_completion_rules),
        ("Version comparison", check_version_comparison),
        ("Persistence", check_persistence),
        ("Architecture", check_architecture),
        ("Imports", check_imports),
    ]
    all_results: list[bool] = []
    for title, fn in sections:
        print(f"[{title}]")
        all_results.extend(fn())
        print()
    passed = sum(all_results)
    total = len(all_results)
    print(f"Summary: {passed}/{total} checks passed")
    if passed == total:
        print("W7 COMPLETE — Evaluation & revision runtime ready. Stop after W7.")
        return 0
    print("W7 FAILED — fix before proceeding.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
