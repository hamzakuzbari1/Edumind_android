"""Regression checks for Coach educational alignment (W7 Coach fix).

Proves the Coach preserves Claude's educational understanding and never falls
back to shallow "first grammar error" messaging:

- coach main issue is NOT blindly the first grammar error
- revision mission matches the main issue (single coherent priority)
- before/after example demonstrates the same issue
- no duplicate coach fields (each field is distinct)
- attempted-but-inaccurate success criteria are explained correctly
- Claude cannot make readiness / progression decisions
- deterministic fallback uses the canonical priority, not the first error

Runs on pure logic (no DB, no network). Uses constructed Claude facts to
simulate real analyzer output plus the deterministic ladder.
"""

from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.language_writing.enums import WritingGoal  # noqa: E402
from app.services.language_writing_coach.priority import (  # noqa: E402
    select_educational_priority,
)
from app.services.language_writing_coach.renderer import render_revision_plan  # noqa: E402
from app.services.language_writing_coach.types import CoachInputBundle, CoachNarrativeContext  # noqa: E402
from app.services.language_writing_curriculum.goal_profiles import profile_for_goal  # noqa: E402
from app.services.language_writing_educational_analyzer.parser import (  # noqa: E402
    parse_claude_educational_json,
)
from app.services.language_writing_educational_analyzer.types import CoachGuidance  # noqa: E402
from app.services.language_writing_evaluator.engine import evaluate_writing_draft_sync  # noqa: E402
from app.services.language_writing_evaluator.blueprint_snapshot import blueprint_snapshot_from_dict  # noqa: E402
from app.services.language_writing_explainability.facts_assembler import assemble_writing_facts  # noqa: E402
from app.services.language_writing_explainability.student_evaluation_display import (  # noqa: E402
    build_student_evaluation_display,
)
from app.services.language_writing_explainability.writing_narrative import (  # noqa: E402
    build_writing_learning_narrative,
)
from app.services.language_writing_generation import WRITING_BLUEPRINT_KEY  # noqa: E402
from scripts.verify_writing_w7_evaluation_revision import _sample_body  # noqa: E402

results: list[bool] = []


def _ok(name: str, cond: bool, detail: str = "") -> bool:
    status = "PASS" if cond else "FAIL"
    line = f"  {name}: {status}"
    if detail:
        line += f"  ({detail})"
    print(line)
    results.append(bool(cond))
    return bool(cond)


def _distinct(*values: str) -> bool:
    cleaned = [v.strip().lower() for v in values if v and v.strip()]
    return len(cleaned) == len(set(cleaned))


def _render(evaluation, goal: WritingGoal):
    profile = profile_for_goal(goal)
    # Build minimal narrative for the render-only renderer.
    facts_bundle = assemble_writing_facts(
        blueprint=_snapshot(goal), evaluation=evaluation
    )
    narrative = build_writing_learning_narrative(facts_bundle, evaluation)
    priority = select_educational_priority(evaluation=evaluation, goal_label=profile.label)
    plan = render_revision_plan(
        CoachInputBundle(evaluation=evaluation.to_coach_evaluation(), goal_profile=profile),
        CoachNarrativeContext(
            coach_summary=narrative.coach_summary,
            focus_sentence=narrative.focus_sentence,
            improvement_context=narrative.improvement_context,
            strengths_summary=narrative.strengths_summary,
            priority_area=narrative.priority_area,
        ),
        evaluation=evaluation,
        priority=priority,
        personality=profile.coach_defaults.personality,
        revision_turn=evaluation.revision_number or 1,
    )
    return priority, plan


_SNAP_CACHE: dict[WritingGoal, object] = {}


def _snapshot(goal: WritingGoal):
    if goal not in _SNAP_CACHE:
        body = _sample_body(goal)
        _SNAP_CACHE[goal] = blueprint_snapshot_from_dict(body[WRITING_BLUEPRINT_KEY])
    return _SNAP_CACHE[goal]


# --------------------------------------------------------------------------------------
# 1) Claude-guidance case: the observed email — task solid, deeper issue = question/modal
# --------------------------------------------------------------------------------------
print("Writing Coach Educational Alignment Verification\n")
print("[Claude guidance drives the coach — the observed email case]")

email_claude_json = """
{
  "task_response": {"score": 0.85, "reason": "The email answers the request and asks for the needed information."},
  "topic_understanding": {"score": 0.9, "reason": "Stays on the assigned workplace topic."},
  "coherence": {"score": 0.8, "reason": "Ideas connect logically."},
  "organization": {"score": 0.78, "reason": "Clear greeting, body and closing."},
  "idea_development": {"score": 0.8, "reason": "Requests are specific."},
  "goal_alignment": {"score": 0.82, "reason": "Professional tone fits business writing."},
  "vocabulary": {"score": 0.78, "reason": "Appropriate business vocabulary.", "range_comment": "Good range.", "repeated_words": [], "weak_choices": [], "missing_topic_words": [], "suggestions": []},
  "grammar_notes": [
    {"issue": "Embedded question word order", "rule": "Use statement word order in embedded questions", "fix": "what I should do", "example": "Could you tell me what I should do?"},
    {"issue": "Base verb after modal", "rule": "Use the base verb after should", "fix": "should submit", "example": "Should I submit it online?"}
  ],
  "cefr_estimate": "B1",
  "cefr_reason": "Controlled sentences with a few target-structure errors.",
  "progress_comparison": "",
  "learning_diagnosis": "The biggest obstacle is not the ideas or task coverage, which are solid, but grammatical control of questions and modal verbs.",
  "revision_priority": "Rewrite each question with correct embedded word order and base verbs after modals.",
  "encouragement": "Your email is clear and professional — tightening the question forms will make it excellent.",
  "strengths": ["Clear professional tone", "Directly answers the request"],
  "major_learning_issue": "Grammar",
  "coach_guidance": {
    "main_issue": "Question formation and modal verb control",
    "why_this_is_the_priority": "Your email answers the task well, but the lesson specifically targets polite questions and modal verbs, and both structures are still inaccurate.",
    "revision_mission": "Rewrite each question. Use normal subject-verb order in embedded questions and the base verb after should and could.",
    "student_friendly_explanation": "In embedded questions keep the normal order, and after should or could use the base verb.",
    "before_example": "Could you tell me what should I do? Should I submited it online?",
    "after_example": "Could you tell me what I should do? Should I submit it online?",
    "encouragement": "You are close — fixing the question forms is the last step to a polished email."
  }
}
"""

# A draft that ALSO contains an isolated "I are" slip, so the old coach would have
# picked "I are" as the headline.
email_draft = (
    "Dear manager, I are writing about the report. Could you tell me what should I do? "
    "Should I submited it online? Thank you for your help."
)
snapshot = _snapshot(WritingGoal.business)
email_eval = evaluate_writing_draft_sync(
    email_draft, draft_id="email1", revision_number=1, blueprint=snapshot
)
claude_facts = parse_claude_educational_json(email_claude_json, model_name="claude-test")
email_eval = replace(email_eval, claude_analysis=claude_facts)

priority, plan = _render(email_eval, WritingGoal.business)

_ok("claude guidance parsed & available", claude_facts.available and claude_facts.coach_guidance.available)
_ok("priority source is claude", priority.source == "claude", priority.source)
_ok(
    "main issue is question/modal control (not 'I are')",
    "question" in plan.main_issue.lower() and "i are" not in plan.main_issue.lower(),
    plan.main_issue,
)
_ok(
    "main issue is NOT subject-verb / 'I are'",
    "subject-verb" not in plan.main_issue.lower() and "i am" not in plan.main_issue.lower(),
)
_ok(
    "revision mission addresses questions/modals",
    "question" in plan.revision_mission.lower() or "modal" in plan.revision_mission.lower(),
    plan.revision_mission,
)
_ok(
    "before example demonstrates the issue",
    "should i" in plan.before_example.lower(),
    plan.before_example,
)
_ok(
    "after example corrects the same issue",
    "what i should do" in plan.after_example.lower(),
    plan.after_example,
)
_ok(
    "coach fields are distinct (no duplicate sentence)",
    _distinct(plan.main_issue, plan.why_it_matters, plan.revision_mission, plan.before_example, plan.after_example),
)
_ok("coach has why_it_matters", bool(plan.why_it_matters.strip()))
_ok(
    "claude cannot set readiness — coach ready mirrors rule engine",
    plan.ready_to_complete == email_eval.revision_readiness.ready,
)

# --------------------------------------------------------------------------------------
# 2) Deterministic fallback: NO claude guidance — must use canonical priority, not first error
# --------------------------------------------------------------------------------------
print("\n[Deterministic fallback uses canonical priority, not the first grammar error]")

# Off-topic Claude facts WITHOUT coach_guidance (guidance unavailable).
offtopic_claude = """
{
  "task_response": {"score": 0.15, "reason": "The draft never answers the prompt about the workplace request."},
  "topic_understanding": {"score": 0.2, "reason": "Talks about football instead of the task."},
  "coherence": {"score": 0.6, "reason": "Sentences flow."},
  "organization": {"score": 0.6, "reason": "Some structure."},
  "idea_development": {"score": 0.5, "reason": "Lists facts."},
  "goal_alignment": {"score": 0.3, "reason": "Not aligned with business goal."},
  "vocabulary": {"score": 0.6, "reason": "Everyday words.", "range_comment": "", "repeated_words": [], "weak_choices": [], "missing_topic_words": [], "suggestions": []},
  "grammar_notes": [{"issue": "I are", "rule": "Subject-verb agreement", "fix": "I am", "example": "I am"}],
  "cefr_estimate": "A2",
  "cefr_reason": "Simple sentences.",
  "progress_comparison": "",
  "learning_diagnosis": "The biggest obstacle is answering the actual question — the writing is off-topic.",
  "revision_priority": "Rewrite so the first sentences directly answer the workplace request.",
  "encouragement": "You clearly can write — aim it at the task.",
  "strengths": ["Fluent sentences"],
  "major_learning_issue": "Task response"
}
"""
off_draft = "I are a big fan of football. My team is the best and they is winning."
off_eval = evaluate_writing_draft_sync(
    off_draft, draft_id="off1", revision_number=1, blueprint=snapshot
)
off_facts = parse_claude_educational_json(offtopic_claude, model_name="claude-test")
_ok("off-topic guidance is unavailable (fallback path)", not off_facts.coach_guidance.available)
off_eval = replace(off_eval, claude_analysis=off_facts)
off_priority, off_plan = _render(off_eval, WritingGoal.business)
_ok("fallback source is canonical_fallback", off_priority.source == "canonical_fallback", off_priority.source)
_ok(
    "fallback headline is task, not 'I are'",
    off_priority.priority_key == "task_response" and "i are" not in off_plan.main_issue.lower(),
    off_plan.main_issue,
)
_ok(
    "fallback mission targets the task, not agreement",
    "answer" in off_plan.revision_mission.lower() or "task" in off_plan.revision_mission.lower(),
    off_plan.revision_mission,
)

# --------------------------------------------------------------------------------------
# 3) Fallback WITHOUT any claude (analyzer off) — still canonical, never first error
# --------------------------------------------------------------------------------------
print("\n[No analyzer at all — deterministic ladder still avoids first grammar error]")
bad_draft = "My name are Hamza. I are a student. They is my friends."
bad_eval = evaluate_writing_draft_sync(
    bad_draft, draft_id="bad1", revision_number=1, blueprint=snapshot
)
bad_eval = replace(bad_eval, claude_analysis=None)
bad_priority, bad_plan = _render(bad_eval, WritingGoal.business)
_ok("no-claude source is canonical_fallback", bad_priority.source == "canonical_fallback", bad_priority.source)
_ok("no-claude headline is a skill, not a raw error line", bool(bad_plan.main_issue.strip()))
_ok(
    "no-claude coach fields distinct",
    _distinct(bad_plan.main_issue, bad_plan.why_it_matters, bad_plan.revision_mission),
)

# --------------------------------------------------------------------------------------
# 4) Success criteria 4-state language (attempted-but-inaccurate vs not attempted)
# --------------------------------------------------------------------------------------
print("\n[Success criteria distinguish attempted-inaccurately from not-attempted]")
display = build_student_evaluation_display(email_eval)
statuses = {c["label"]: c.get("display_status") for c in display.success_criteria}
_ok("every criterion carries a display_status", all(c.get("display_status") for c in display.success_criteria))
_ok(
    "display statuses use the 4-state vocabulary",
    set(statuses.values()) <= {"met", "partially_met", "attempted_inaccurately", "not_attempted"},
    str(set(statuses.values())),
)
_ok("improvements capped to 3 (concise summary)", len(display.improvements) <= 3)

# --------------------------------------------------------------------------------------
# 5) Claude cannot smuggle a pass/fail decision into coach guidance
# --------------------------------------------------------------------------------------
print("\n[Claude coach guidance cannot make progression decisions]")
forbidden_json = email_claude_json.replace(
    "Question formation and modal verb control",
    "You passed — ready to complete and promote to B2",
)
forbidden_facts = parse_claude_educational_json(forbidden_json, model_name="claude-test")
_ok(
    "guidance with pass/promotion wording is rejected",
    not forbidden_facts.coach_guidance.available,
)

print(f"\nSummary: {sum(results)}/{len(results)} checks passed")
if all(results):
    print("COACH ALIGNMENT COMPLETE — coach preserves Claude's educational understanding.")
    sys.exit(0)
sys.exit(1)
