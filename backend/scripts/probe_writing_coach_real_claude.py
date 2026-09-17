"""Real-Claude probe: prove the Coach preserves Claude's understanding end-to-end.

Runs the ACTUAL evaluation+coach pipeline with WRITING_EDUCATIONAL_ANALYZER=claude
on the observed email draft (task solid, deeper issue = question/modal control,
plus an isolated 'I are' slip). No mock, no silent fallback: fails loudly if
Claude was not used.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ["WRITING_EDUCATIONAL_ANALYZER"] = "claude"

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.language_writing.enums import WritingGoal  # noqa: E402
from app.services.language_writing_evaluation_runtime.pipeline import (  # noqa: E402
    process_writing_draft_turn_sync,
)
from scripts.verify_writing_w7_evaluation_revision import _sample_body  # noqa: E402

EMAIL_DRAFT = (
    "Dear manager, I are writing to ask about the monthly report. "
    "Could you tell me what should I do to finish it on time? "
    "Should I submited it online or send it by email? "
    "Thank you very much for your help and guidance."
)


def main() -> int:
    body = _sample_body(WritingGoal.business)
    result, _ = process_writing_draft_turn_sync(
        student_id=1,
        content_item_id=91001,
        draft_text=EMAIL_DRAFT,
        body_json=body,
    )
    facts = result.evaluation.claude_analysis
    plan = result.revision_plan

    print("=== PROVENANCE ===")
    print("analyzer source :", facts.source if facts else None)
    print("model           :", facts.model_name if facts else None)
    print("analyzer version:", facts.analyzer_version if facts else None)
    print("guidance source :", plan.guidance_source)
    print("priority key    :", plan.priority_key)

    print("\n=== CLAUDE EDUCATIONAL FACTS ===")
    if facts:
        print("task_response   :", round(facts.task_response.score, 2), facts.task_response.reason)
        print("cefr_estimate   :", facts.cefr_estimate, "-", facts.cefr_reason)
        print("learning_diag   :", facts.learning_diagnosis)
        print("major_issue     :", facts.major_learning_issue)

    print("\n=== COACH (Your next revision) ===")
    print("main_issue      :", plan.main_issue)
    print("why_it_matters  :", plan.why_it_matters)
    print("revision_mission:", plan.revision_mission)
    print("before_example  :", plan.before_example)
    print("after_example   :", plan.after_example)
    print("encouragement   :", plan.encouragement)

    print("\n=== RULE ENGINE (unchanged ownership) ===")
    print("ready_to_complete:", result.evaluation.revision_readiness.ready)

    ok = True

    def check(name: str, cond: bool) -> None:
        nonlocal ok
        ok = ok and cond
        print(f"[{'PASS' if cond else 'FAIL'}] {name}")

    print("\n=== ASSERTIONS ===")
    check("Claude was actually used (source=claude)", bool(facts and facts.source == "claude"))
    check("coach guidance came from Claude", plan.guidance_source == "claude")
    check("main issue is NOT the isolated 'I are' slip", "i are" not in plan.main_issue.lower())
    check(
        "main issue reflects a real learning skill",
        len(plan.main_issue.split()) >= 2,
    )
    check("revision mission is present & distinct", bool(plan.revision_mission.strip()) and plan.revision_mission.strip().lower() != plan.main_issue.strip().lower())
    check("before/after examples present", bool(plan.before_example) and bool(plan.after_example))
    check("before != after (a real correction)", plan.before_example.strip().lower() != plan.after_example.strip().lower())
    check("coach ready mirrors rule engine (Claude did not decide)", plan.ready_to_complete == result.evaluation.revision_readiness.ready)

    print("\nRESULT:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
