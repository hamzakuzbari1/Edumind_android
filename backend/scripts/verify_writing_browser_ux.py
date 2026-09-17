"""Verify Writing W7 browser UX — revision loop, evaluation panel, criteria-gated completion."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

BACKEND = Path(__file__).resolve().parents[1]
ROOT = BACKEND.parent
SRC = ROOT / "src"
SERVICES = BACKEND / "app" / "services"

from app.services.language_writing.enums import WritingGoal  # noqa: E402
from app.services.language_writing_coach.renderer import COACH_RENDERER_VERSION  # noqa: E402
from app.services.language_writing_evaluator.blueprint_snapshot import blueprint_snapshot_from_dict  # noqa: E402
from app.services.language_writing_evaluator.engine import evaluate_writing_draft_sync  # noqa: E402
from app.services.language_writing_explainability.student_evaluation_display import build_student_evaluation_display  # noqa: E402
from app.services.language_writing_evaluation_runtime.pipeline import process_writing_draft_turn_sync  # noqa: E402
from app.services.language_writing_generation import WRITING_BLUEPRINT_KEY, WRITING_CURRICULUM_KEY, WRITING_GOAL_KEY  # noqa: E402
from scripts.verify_writing_w7_evaluation_revision import _sample_body  # noqa: E402


def _curriculum_context(body: dict) -> tuple[str, str, WritingGoal]:
    curriculum = body.get(WRITING_CURRICULUM_KEY) or {}
    if not isinstance(curriculum, dict):
        curriculum = {}
    blueprint = body.get(WRITING_BLUEPRINT_KEY) or {}
    if not isinstance(blueprint, dict):
        blueprint = {}
    official_cefr = str(curriculum.get("official_cefr") or blueprint.get("official_cefr") or "B1")
    arc_stage = str(curriculum.get("arc_stage") or blueprint.get("curriculum_arc") or "")
    raw_goal = (
        body.get(WRITING_GOAL_KEY)
        or curriculum.get("personal_goal")
        or blueprint.get("personal_goal")
        or "general_english"
    )
    try:
        goal = WritingGoal(str(raw_goal))
    except ValueError:
        goal = WritingGoal.general_english
    return official_cefr, arc_stage, goal


def _ok(name: str, passed: bool, detail: str = "") -> bool:
    status = "PASS" if passed else "FAIL"
    suffix = f" — {detail}" if detail else ""
    print(f"  {name}: {status}{suffix}")
    return passed


def main() -> int:
    print("Writing Browser UX Verification\n")
    results: list[bool] = []

    practice = (SRC / "components/language/WritingPracticePanel.vue").read_text(encoding="utf-8")
    eval_panel = (SRC / "components/language/WritingEvaluationPanel.vue").read_text(encoding="utf-8")
    progress_panel = (SRC / "components/language/WritingProgressPanel.vue").read_text(encoding="utf-8")
    bundles = (BACKEND / "app/schemas/language_writing_bundles.py").read_text(encoding="utf-8")
    runtime_api = (SERVICES / "language_writing_evaluation_runtime/runtime_api.py").read_text(encoding="utf-8")
    pipeline = (SERVICES / "language_writing_evaluation_runtime/pipeline.py").read_text(encoding="utf-8")
    renderer = (SERVICES / "language_writing_coach/renderer.py").read_text(encoding="utf-8")

    print("[Frontend flow]")
    results.append(_ok("evaluation panel component exists", eval_panel.strip()))
    results.append(_ok("progress panel on completion", "WritingProgressPanel" in practice))
    results.append(_ok("practice uses evaluation composable", "useWritingEvaluation" in practice))
    results.append(_ok("first submit does not use completeIfReady", "completeIfReady: false" in practice))
    results.append(_ok("complete button gated on readyToComplete", "readyToComplete && !completed" in practice))
    results.append(_ok("no auto-complete watch", "watch(completed" not in practice))
    results.append(_ok("evaluation shows dimensions", "dimensions" in eval_panel))
    results.append(_ok("evaluation shows criteria checklist", "successCriteria" in eval_panel))
    results.append(_ok("evaluation shows strengths/improvements", "strengths" in eval_panel and "improvements" in eval_panel))
    results.append(_ok("progress panel shows stage label", "writing_stage_label" in progress_panel))

    print("\n[API contract]")
    results.append(_ok("WritingEvaluationDisplayOut schema", "WritingEvaluationDisplayOut" in bundles))
    results.append(_ok("WritingLessonProgressOut schema", "WritingLessonProgressOut" in bundles))
    results.append(_ok("draft response includes evaluation_display", "evaluation_display" in bundles))
    results.append(_ok("runtime builds evaluation_display", "build_student_evaluation_display" in runtime_api))

    print("\n[Backend completion gate]")
    results.append(_ok("pipeline requires force_complete", "force_complete and evaluation.revision_readiness.ready" in pipeline))
    results.append(_ok("no auto-complete OR branch", "completion.completed or" not in pipeline))

    print("\n[Goal-specific recommendations]")
    results.append(_ok("travel recommendation text", "travel review" in renderer.lower()))
    results.append(_ok("ielts recommendation text", "ielts" in renderer.lower()))
    results.append(_ok("general english recommendation", "everyday paragraphs" in renderer.lower()))
    results.append(_ok("no QA node defaults map", "GOAL_QA_NODE_DEFAULTS" not in open(SERVICES / "language_writing_runtime/node_selection.py", encoding="utf-8").read()))
    results.append(_ok("curriculum selector exists", (SERVICES / "language_writing_curriculum/selector.py").is_file()))

    print("\n[Runtime behavior]")
    body = _sample_body(WritingGoal.travel)
    weak = "Hi."
    r_weak, body_after_weak = process_writing_draft_turn_sync(student_id=1, content_item_id=701, draft_text=weak, body_json=body)
    results.append(_ok("weak first draft opens evaluation not completion", r_weak.success and not r_weak.completed))
    display = build_student_evaluation_display(r_weak.evaluation)
    display_dict = display.to_student_dict()
    results.append(_ok("evaluation has five dimensions", len(display_dict.get("dimensions", [])) == 5))
    results.append(_ok("evaluation exposes no scores", "score" not in str(display_dict).lower()))

    draft2 = (
        "Dear Customer Service,\n\n"
        "I am writing to complain about my delayed flight because the boarding was late. "
        "I missed my connection and I would like a refund and an apology for this delay. "
        "The announcement was unclear and I felt the staff did not help enough. "
        "Please respond soon.\n\nRegards,\nSam"
    )
    r_rev, b_rev = process_writing_draft_turn_sync(student_id=1, content_item_id=701, draft_text=draft2, body_json=body_after_weak)
    results.append(_ok("revision loop second turn", r_rev.revision_number == 2))

    snapshot = blueprint_snapshot_from_dict(body[WRITING_BLUEPRINT_KEY])
    eng = evaluate_writing_draft_sync(draft2 * 2, draft_id="s", revision_number=2, blueprint=snapshot)
    strong_decision = eng.completion
    r_done, _ = process_writing_draft_turn_sync(
        student_id=1,
        content_item_id=701,
        draft_text=draft2 * 2,
        body_json=b_rev,
        force_complete=True,
    )
    if strong_decision.eligible:
        results.append(_ok("explicit complete when criteria met", r_done.completed))
    else:
        results.append(_ok("criteria gate blocks premature complete", not r_done.completed))

    official, arc, goal = _curriculum_context(body)
    results.append(_ok("curriculum context extracts CEFR", bool(official)))
    results.append(_ok("curriculum context extracts goal", goal == WritingGoal.travel))

    passed = sum(1 for item in results if item)
    total = len(results)
    print(f"\nSummary: {passed}/{total} checks passed")
    if passed == total:
        print("WRITING BROWSER UX VERIFIED — evaluation + revision loop ready.")
        return 0
    print("WRITING BROWSER UX NOT READY — fix failures.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
