"""Writing product QA — 50 real student scenarios (behavior only, no new features)."""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

os.environ.setdefault("WRITING_EDUCATIONAL_ANALYZER", "mock")
os.environ.setdefault("WRITING_MODEL_PROVIDER", "mock")

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.language_writing.enums import OfficialWritingCEFR, WritingGoal  # noqa: E402
from app.services.language_writing_coach.renderer import render_revision_plan  # noqa: E402
from app.services.language_writing_coach.types import CoachInputBundle, CoachNarrativeContext  # noqa: E402
from app.services.language_writing_curriculum.goal_profiles import profile_for_goal  # noqa: E402
from app.services.language_writing_evaluator.blueprint_snapshot import blueprint_snapshot_from_dict  # noqa: E402
from app.services.language_writing_evaluator.engine import evaluate_writing_draft_sync  # noqa: E402
from app.services.language_writing_evaluator.evaluation_facts_types import CriterionStatus  # noqa: E402
from app.services.language_writing_evaluator.evaluation_result import WritingEvaluationEngineResult  # noqa: E402
from app.services.language_writing_evaluator.facts_deserialize import evaluation_result_from_dict  # noqa: E402
from app.services.language_writing_explainability.student_evaluation_display import build_student_evaluation_display  # noqa: E402
from app.services.language_writing_evaluation_runtime.pipeline import process_writing_draft_turn_sync  # noqa: E402
from app.services.language_writing_generation import WRITING_BLUEPRINT_KEY  # noqa: E402
from app.services.language_writing_revision.persistence import WRITING_EVALUATION_FACTS_KEY  # noqa: E402
from scripts.verify_writing_w7_evaluation_revision import _sample_body  # noqa: E402

REPORT_PATH = Path(__file__).resolve().parent / "qa_writing_50_scenarios_report.json"

TRAVEL_COMPLAINT = (
    "Dear Customer Service, I am writing to complain about my delayed flight because the boarding was late. "
    "I missed my connection and I would like a refund and an apology for this delay. "
    "The announcement was unclear and I felt the staff did not help enough. "
    "Please respond soon. Regards, Sam."
)

BUSINESS_EMAIL = (
    "Dear team, I would like to schedule a meeting next Tuesday to discuss the quarterly agenda and budget "
    "priorities. Could you please confirm your available times by Friday? I will circulate a draft agenda "
    "in advance because everyone needs time to prepare. Thank you for your cooperation. Regards, Alex."
)

IELTS_PARAGRAPH = (
    "I am interested in studying computer science because it connects directly to my career goals in software "
    "engineering. During school I completed programming projects and internships that strengthened my analytical "
    "skills. Therefore, this major will help me contribute to technology solutions in my community and support "
    "my long-term professional development in the technology sector."
)


def _pad(text: str, min_words: int = 65) -> str:
    out = text.strip()
    filler = " Please review this paragraph carefully for clarity and detail."
    while len(out.split()) < min_words:
        out += filler
    return out


def _snap(goal: WritingGoal):
    body = _sample_body(goal)
    return blueprint_snapshot_from_dict(body[WRITING_BLUEPRINT_KEY]), body


@dataclass
class Scenario:
    id: str
    name: str
    goal: WritingGoal
    draft: str
    expected: str
    check: Callable[[WritingEvaluationEngineResult], tuple[bool, str]]
    pipeline: bool = False
    force_complete: bool = False
    revision_chain: tuple[str, ...] = ()
    persist_check: bool = False
    roundtrip_check: bool = False
    coach_check: bool = False
    compare_readiness: tuple[str, str] | None = None


@dataclass
class ScenarioResult:
    id: str
    name: str
    expected: str
    actual: str
    passed: bool
    root_cause: str = ""
    fix: str = ""
    retest: str = ""


def _scenarios() -> list[Scenario]:
    s: list[Scenario] = []

    def add(
        sid: str,
        name: str,
        goal: WritingGoal,
        draft: str,
        expected: str,
        check: Callable[[WritingEvaluationEngineResult], tuple[bool, str]],
        **kw: Any,
    ) -> None:
        s.append(Scenario(sid, name, goal, draft, expected, check, **kw))

    # --- Grammar agreement (S01–S10) ---
    add(
        "S01",
        "Singular subject + are (name)",
        WritingGoal.travel,
        "My name are Hamza",
        "Grammar fails; not ready; subject-verb explanation",
        lambda r: (
            (not r.grammar.passed and not r.revision_readiness.ready
             and any("subject-verb" in i.lower() or "name is" in i.lower() for i in r.explanation.improvements)),
            f"grammar={r.grammar.passed} ready={r.revision_readiness.ready} improvements={list(r.explanation.improvements)[:2]}",
        ),
    )
    add(
        "S02",
        "He are tired",
        WritingGoal.general_english,
        "He are tired today because he worked late.",
        "Grammar fails on agreement",
        lambda r: ((not r.grammar.passed), f"grammar={r.grammar.passed} errors={list(r.grammar.errors)}"),
    )
    add(
        "S03",
        "They is happy",
        WritingGoal.general_english,
        "They is happy about the result.",
        "Grammar fails on plural agreement",
        lambda r: ((not r.grammar.passed), f"grammar={r.grammar.passed}"),
    )
    add(
        "S04",
        "I are fine",
        WritingGoal.daily_communication,
        "I are fine thank you.",
        "Grammar fails on I am",
        lambda r: ((not r.grammar.passed), f"grammar={r.grammar.passed}"),
    )
    add(
        "S05",
        "Teacher is wrong plural",
        WritingGoal.academic,
        "The students is waiting outside.",
        "Grammar fails (students + is)",
        lambda r: ((not r.grammar.passed), f"grammar={r.grammar.passed}"),
    )
    add(
        "S06",
        "Correct agreement passes grammar dim",
        WritingGoal.travel,
        _pad("My name is Hamza and I am writing about my hotel reception experience at the front desk."),
        "No agreement error; grammar dimension not blocked by agreement",
        lambda r: (
            (not r.grammar.errors),
            f"errors={list(r.grammar.errors)} passed={r.grammar.passed}",
        ),
    )
    add(
        "S07",
        "Agreement error blocks readiness even with long draft",
        WritingGoal.travel,
        _pad("My name are Hamza and I want to complain about the delayed flight and refund issue."),
        "Long draft still not ready when agreement error present",
        lambda r: ((not r.revision_readiness.ready and not r.grammar.passed), f"ready={r.revision_readiness.ready}"),
    )
    add(
        "S08",
        "Priority issue mentions grammar first",
        WritingGoal.travel,
        "My name are Hamza",
        "Priority issue is grammar-related",
        lambda r: (
            ("agreement" in r.explanation.priority_issue.lower() or "name is" in r.explanation.priority_issue.lower()),
            f"priority={r.explanation.priority_issue}",
        ),
    )
    add(
        "S09",
        "Weak skill tags agreement",
        WritingGoal.travel,
        "My name are Hamza",
        "Weak skills include subject_verb_agreement",
        lambda r: (
            (any("subject_verb" in w for w in r.weak_skills)),
            f"weak={list(r.weak_skills)}",
        ),
    )
    add(
        "S10",
        "Coach ready matches evaluation ready (bad draft)",
        WritingGoal.travel,
        "My name are Hamza",
        "Coach plan ready_to_complete false",
        lambda r: ((not r.revision_readiness.ready), f"ready={r.revision_readiness.ready}"),
        pipeline=True,
    )

    # --- Word count (S11–S18) ---
    add(
        "S11",
        "Single word too short",
        WritingGoal.travel,
        "Hi.",
        "Not ready; below min words",
        lambda r: ((not r.revision_readiness.ready and r.word_count < 10), f"wc={r.word_count} ready={r.revision_readiness.ready}"),
    )
    add(
        "S12",
        "Empty draft",
        WritingGoal.travel,
        "   ",
        "Zero words; not ready",
        lambda r: ((r.word_count == 0 and not r.revision_readiness.ready), f"wc={r.word_count}"),
    )
    add(
        "S13",
        "Word count improvement hint",
        WritingGoal.travel,
        "Hello.",
        "Improvement mentions word count",
        lambda r: (
            (any("word" in i.lower() for i in r.explanation.improvements)),
            f"improvements={list(r.explanation.improvements)[:3]}",
        ),
    )
    add(
        "S14",
        "Meets min words flag",
        WritingGoal.travel,
        _pad(TRAVEL_COMPLAINT),
        "Meets word limit when padded to min",
        lambda r: ((r.meets_word_limit), f"meets={r.meets_word_limit} wc={r.word_count}"),
    )
    add(
        "S15",
        "Below min not meets_word_limit",
        WritingGoal.business,
        "Dear team, meeting please.",
        "Does not meet word limit",
        lambda r: ((not r.meets_word_limit), f"meets={r.meets_word_limit} wc={r.word_count}"),
    )
    add(
        "S16",
        "Blocker mentions word count",
        WritingGoal.travel,
        "Short draft.",
        "Blockers include word count",
        lambda r: (
            (any("word" in b.lower() or "below" in b.lower() for b in r.revision_readiness.blockers)),
            f"blockers={list(r.revision_readiness.blockers)[:3]}",
        ),
    )
    add(
        "S17",
        "Success criterion word min not met",
        WritingGoal.travel,
        "Hi there.",
        "Word-min criterion not_met",
        lambda r: (
            (any("word" in c.label.lower() and c.status == CriterionStatus.not_met for c in r.success_criteria)),
            f"criteria={[(c.label[:30], c.status.value) for c in r.success_criteria if 'word' in c.label.lower()]}",
        ),
    )
    add(
        "S18",
        "Strong travel draft word count strength possible",
        WritingGoal.travel,
        _pad(TRAVEL_COMPLAINT, 70),
        "Word count at least 60",
        lambda r: ((r.word_count >= 60), f"wc={r.word_count}"),
    )

    # --- Goal-specific writing (S19–S28) ---
    goal_drafts = [
        ("S19", WritingGoal.travel, _pad(TRAVEL_COMPLAINT), "Travel complaint has evaluation"),
        ("S20", WritingGoal.business, _pad(BUSINESS_EMAIL), "Business email evaluates"),
        ("S21", WritingGoal.ielts, _pad(IELTS_PARAGRAPH), "IELTS paragraph evaluates"),
        ("S22", WritingGoal.general_english, _pad("I enjoy learning English because it helps me communicate clearly."), "General English evaluates"),
        ("S23", WritingGoal.academic, _pad("This essay discusses research because evidence supports the thesis."), "Academic evaluates"),
        ("S24", WritingGoal.job_interview, _pad("Dear manager, I am applying for the position because I have experience."), "Job interview evaluates"),
        ("S25", WritingGoal.daily_communication, _pad("Hello, could you please help me with my appointment tomorrow?"), "Daily comm evaluates"),
        ("S26", WritingGoal.creative_writing, _pad("The old house stood quietly because the wind stopped suddenly."), "Creative evaluates"),
    ]
    for sid, goal, draft, expected in goal_drafts:
        add(
            sid,
            expected,
            goal,
            draft,
            "Produces valid evaluation with 5 dimensions and criteria",
            lambda r, _g=goal: (
                (r.engine_version.startswith("8.") and len(r.success_criteria) > 0),
                f"version={r.engine_version} criteria={len(r.success_criteria)}",
            ),
        )

    add(
        "S27",
        "Travel draft no agreement errors when correct",
        WritingGoal.travel,
        _pad("Dear Sir, I am writing because my flight was delayed and I would like a refund."),
        "No grammar errors when well-formed",
        lambda r: ((not r.grammar.errors), f"errors={list(r.grammar.errors)}"),
    )
    add(
        "S28",
        "Business polite language",
        WritingGoal.business,
        _pad(BUSINESS_EMAIL),
        "Goal alignment reasonable for email",
        lambda r: ((r.goal_alignment.score >= 0.35), f"goal={r.goal_alignment.score}"),
    )

    # --- Hybrid / Claude (S29–S32) ---
    add(
        "S29",
        "Claude analysis attached on bad draft",
        WritingGoal.travel,
        "My name are Hamza",
        "claude_analysis available (mock)",
        lambda r: (
            (r.claude_analysis is not None and r.claude_analysis.available),
            f"claude={r.claude_analysis is not None}",
        ),
    )
    add(
        "S30",
        "Claude cannot override grammar pass",
        WritingGoal.travel,
        "My name are Hamza",
        "grammar still fails with claude present",
        lambda r: ((not r.grammar.passed), f"grammar={r.grammar.passed}"),
    )
    add(
        "S31",
        "Engine version 8.1.0",
        WritingGoal.travel,
        "My name are Hamza",
        "Canonical engine version",
        lambda r: ((r.engine_version == "8.1.0"), f"version={r.engine_version}"),
    )
    add(
        "S32",
        "Claude enriches explanation",
        WritingGoal.travel,
        "My name are Hamza",
        "Explanation has claude or grammar content",
        lambda r: (
            (len(r.explanation.improvements) >= 3),
            f"n_improvements={len(r.explanation.improvements)}",
        ),
    )

    # --- Pipeline / runtime (S33–S40) ---
    add(
        "S33",
        "First draft does not auto-complete",
        WritingGoal.travel,
        _pad(TRAVEL_COMPLAINT),
        "Pipeline completed=false without force",
        lambda r: ((True,), "pipeline check"),
        pipeline=True,
    )
    add(
        "S34",
        "Weak draft opens revision not completion",
        WritingGoal.travel,
        "My name are Hamza",
        "Not ready after pipeline",
        lambda r: ((not r.revision_readiness.ready), f"ready={r.revision_readiness.ready}"),
        pipeline=True,
    )
    add(
        "S35",
        "Evaluation display has 5 dimensions",
        WritingGoal.travel,
        _pad(TRAVEL_COMPLAINT),
        "Student display 5 dimensions",
        lambda r: ((len(build_student_evaluation_display(r).dimensions) == 5), "display ok"),
    )
    add(
        "S36",
        "Display no numeric scores exposed",
        WritingGoal.travel,
        _pad(TRAVEL_COMPLAINT),
        "Display dict has no score key",
        lambda r: (
            ("score" not in json.dumps(build_student_evaluation_display(r).to_student_dict()).lower()),
            "checked",
        ),
    )
    add(
        "S37",
        "Persistence includes claude_analysis",
        WritingGoal.travel,
        "My name are Hamza",
        "Persisted facts have claude_analysis",
        lambda r: ((True,), "pipeline persist"),
        pipeline=True,
        persist_check=True,
    )
    add(
        "S38",
        "Persisted engine version",
        WritingGoal.travel,
        _pad(TRAVEL_COMPLAINT),
        "Persisted engine_version 8.1.0",
        lambda r: ((True,), "pipeline persist"),
        pipeline=True,
        persist_check=True,
    )
    add(
        "S39",
        "Coach encouragement present",
        WritingGoal.business,
        _pad(BUSINESS_EMAIL),
        "Coach plan has encouragement",
        lambda r: ((True,), "coach"),
        pipeline=True,
        coach_check=True,
    )
    add(
        "S40",
        "Coach main_issue present for bad draft",
        WritingGoal.travel,
        "My name are Hamza",
        "Coach main_issue non-empty",
        lambda r: ((True,), "coach"),
        pipeline=True,
        coach_check=True,
    )

    # --- Revision loop (S41–S45) ---
    add(
        "S41",
        "Revision 1 to 2 increments",
        WritingGoal.ielts,
        IELTS_PARAGRAPH,
        "Second revision number is 2",
        lambda r: ((True,), "revision chain"),
        pipeline=True,
        revision_chain=(IELTS_PARAGRAPH, IELTS_PARAGRAPH + " Therefore, I revised my paragraph to improve organization."),
    )
    add(
        "S42",
        "Comparison on second turn",
        WritingGoal.ielts,
        IELTS_PARAGRAPH,
        "Comparison object on rev 2",
        lambda r: ((r.comparison is not None), f"comparison={r.comparison is not None}"),
        pipeline=True,
        revision_chain=(IELTS_PARAGRAPH, _pad(IELTS_PARAGRAPH + " Moreover, linking words connect my ideas clearly.")),
    )
    add(
        "S43",
        "Improved draft higher readiness than bad",
        WritingGoal.travel,
        TRAVEL_COMPLAINT,
        "Strong draft readiness >= bad draft",
        lambda r: ((True,), "compare readiness"),
        compare_readiness=("My name are Hamza", _pad(TRAVEL_COMPLAINT)),
    )
    add(
        "S44",
        "Deserialize roundtrip preserves ready",
        WritingGoal.travel,
        "My name are Hamza",
        "Roundtrip ready flag matches",
        lambda r: ((True,), "roundtrip"),
        pipeline=True,
        roundtrip_check=True,
    )
    add(
        "S45",
        "Revision does not auto-complete",
        WritingGoal.travel,
        _pad(TRAVEL_COMPLAINT),
        "Second turn still not auto-completed",
        lambda r: ((True,), "rev2 complete"),
        pipeline=True,
        revision_chain=(_pad(TRAVEL_COMPLAINT), _pad(TRAVEL_COMPLAINT + " I revised this draft.")),
    )

    # --- Completion gates (S46–S50) ---
    add(
        "S46",
        "Force complete blocked when not ready",
        WritingGoal.travel,
        "My name are Hamza",
        "force_complete does not complete bad draft",
        lambda r: ((True,), "force gate"),
        pipeline=True,
        force_complete=True,
    )
    add(
        "S47",
        "Completion eligible false for bad grammar",
        WritingGoal.travel,
        "My name are Hamza",
        "completion.eligible false",
        lambda r: ((not r.completion.eligible), f"eligible={r.completion.eligible}"),
    )
    add(
        "S48",
        "Ready signal matches revision_readiness",
        WritingGoal.travel,
        "My name are Hamza",
        "ready_to_complete property matches readiness",
        lambda r: ((r.ready_to_complete == r.revision_readiness.ready), f"ready={r.ready_to_complete}"),
    )
    add(
        "S49",
        "Bad draft criteria not all met",
        WritingGoal.travel,
        "My name are Hamza",
        "criteria_met_count < criteria_total",
        lambda r: (
            (r.completion.criteria_met_count < r.completion.criteria_total),
            f"met={r.completion.criteria_met_count}/{r.completion.criteria_total}",
        ),
    )
    add(
        "S50",
        "Explanation summary mentions node or grammar for bad draft",
        WritingGoal.travel,
        "My name are Hamza",
        "Summary explains issue",
        lambda r: (
            (bool(r.explanation.summary) and ("grammar" in r.explanation.summary.lower() or "issue" in r.explanation.summary.lower())),
            f"summary={r.explanation.summary[:80]}",
        ),
    )

    return s


def _run_scenario(sc: Scenario) -> ScenarioResult:
    snap, body = _snap(sc.goal)
    actual = ""
    passed = False
    root_cause = ""
    fix = ""

    try:
        if getattr(sc, "compare_readiness", None):
            bad_d, good_d = sc.compare_readiness  # type: ignore[attr-defined]
            bad_r = evaluate_writing_draft_sync(bad_d, draft_id="bad", revision_number=1, blueprint=snap)
            good_r = evaluate_writing_draft_sync(good_d, draft_id="good", revision_number=1, blueprint=snap)
            passed = good_r.overall_readiness >= bad_r.overall_readiness
            actual = f"bad={bad_r.overall_readiness:.3f} good={good_r.overall_readiness:.3f}"
        elif sc.revision_chain:
            b = body
            ev = None
            turn_result = None
            for i, draft in enumerate(sc.revision_chain, start=1):
                turn_result, b = process_writing_draft_turn_sync(
                    student_id=1,
                    content_item_id=8000 + int(sc.id[1:]),
                    draft_text=draft,
                    body_json=b,
                )
                ev = turn_result.evaluation
            assert ev is not None
            if sc.id == "S41":
                passed = turn_result is not None and turn_result.revision_number == 2
                actual = f"revision={turn_result.revision_number if turn_result else None}"
            elif sc.id == "S45":
                passed = turn_result is not None and not turn_result.completed
                actual = f"completed={turn_result.completed if turn_result else None}"
            else:
                ok, actual = sc.check(ev)
                passed = ok
        elif sc.pipeline:
            turn_result, updated = process_writing_draft_turn_sync(
                student_id=1,
                content_item_id=7000 + int(sc.id[1:]),
                draft_text=sc.draft,
                body_json=body,
                force_complete=getattr(sc, "force_complete", False),
            )
            ev = turn_result.evaluation

            if getattr(sc, "persist_check", False):
                facts = updated.get(WRITING_EVALUATION_FACTS_KEY) or {}
                if sc.id == "S37":
                    passed = isinstance(facts, dict) and facts.get("claude_analysis") is not None
                    actual = f"has_claude={isinstance(facts, dict) and 'claude_analysis' in facts}"
                elif sc.id == "S38":
                    passed = isinstance(facts, dict) and facts.get("engine_version") == "8.1.0"
                    actual = f"version={facts.get('engine_version') if isinstance(facts, dict) else None}"
                else:
                    ok, actual = sc.check(ev)
                    passed = ok
            elif getattr(sc, "roundtrip_check", False):
                facts = updated.get(WRITING_EVALUATION_FACTS_KEY) or {}
                restored = evaluation_result_from_dict(facts) if isinstance(facts, dict) else None
                passed = restored is not None and restored.revision_readiness.ready == ev.revision_readiness.ready
                actual = f"orig={ev.revision_readiness.ready} restored={restored.revision_readiness.ready if restored else None}"
            elif getattr(sc, "coach_check", False):
                plan = turn_result.revision_plan
                if sc.id == "S39":
                    passed = bool(plan.encouragement.strip())
                    actual = f"encouragement_len={len(plan.encouragement)}"
                else:
                    passed = bool(plan.main_issue.strip())
                    actual = f"main_issue={plan.main_issue[:60]}"
            elif sc.id == "S33":
                passed = not turn_result.completed
                actual = f"completed={turn_result.completed}"
            elif sc.id == "S46":
                passed = not turn_result.completed
                actual = f"completed={turn_result.completed} ready={ev.revision_readiness.ready}"
            elif sc.id == "S10":
                plan = turn_result.revision_plan
                passed = plan.ready_to_complete == ev.revision_readiness.ready and not ev.revision_readiness.ready
                actual = f"coach_ready={plan.ready_to_complete} eval_ready={ev.revision_readiness.ready}"
            else:
                ok, actual = sc.check(ev)
                passed = ok
        else:
            ev = evaluate_writing_draft_sync(
                sc.draft,
                draft_id=sc.id,
                revision_number=1,
                blueprint=snap,
            )
            ok, actual = sc.check(ev)
            passed = ok
    except Exception as exc:  # noqa: BLE001
        passed = False
        actual = f"EXCEPTION: {exc}"
        root_cause = str(exc)

    if not passed and not root_cause:
        root_cause = f"Assertion failed: expected '{sc.expected}', got '{actual}'"

    return ScenarioResult(
        id=sc.id,
        name=sc.name,
        expected=sc.expected,
        actual=actual,
        passed=passed,
        root_cause="" if passed else root_cause,
        fix="" if passed else "TBD after triage",
        retest="PASS" if passed else "PENDING",
    )


def main() -> int:
    scenarios = _scenarios()
    if len(scenarios) != 50:
        print(f"WARNING: expected 50 scenarios, got {len(scenarios)}")
    results = [_run_scenario(sc) for sc in scenarios]
    passed = sum(1 for r in results if r.passed)
    report = {
        "total": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "scenarios": [r.__dict__ for r in results],
    }
    REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"Writing QA — 50 scenarios: {passed}/{len(results)} passed\n")
    for r in results:
        status = "PASS" if r.passed else "FAIL"
        print(f"  {r.id} {r.name}: {status}")
        if not r.passed:
            print(f"    expected: {r.expected}")
            print(f"    actual:   {r.actual}")
            print(f"    cause:    {r.root_cause}")

    print(f"\nReport: {REPORT_PATH}")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
