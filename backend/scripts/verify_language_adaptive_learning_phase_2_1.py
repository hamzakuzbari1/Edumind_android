"""Verify Phase 2.1 — Facts Layer + Learning Narrative Foundation.

Usage (from backend/):
    python scripts/verify_language_adaptive_learning_phase_2_1.py
"""

from __future__ import annotations

import ast
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ROOT = Path(__file__).resolve().parents[1]
NARRATIVE_DIR = ROOT / "app/services/language_learning_narrative"
FACTS_DIR = ROOT / "app/services/language_learning_facts"
EXPLAIN_DIR = ROOT / "app/services/language_listening_explainability"

# Modules allowed to contain student-facing educational sentence construction.
NARRATIVE_OWNER_FILES = {
    NARRATIVE_DIR / "builder.py",
    NARRATIVE_DIR / "legacy_adapter.py",
}

# Legacy teacher/journey paths — documented debt until Phase 2.2+.
LEGACY_PROSE_ALLOWLIST = {
    EXPLAIN_DIR / "teacher_summary.py",
    EXPLAIN_DIR / "learning_path.py",
}

FORBIDDEN_STUDENT_COPY_PATTERNS = (
    re.compile(r"Today's situation is"),
    re.compile(r"You are improving in:"),
    re.compile(r"Keep practising —"),
    re.compile(r"This lesson focuses on"),
)


def _py_files(directory: Path) -> list[Path]:
    return sorted(p for p in directory.rglob("*.py") if p.is_file())


def audit_narrative_ownership() -> dict[str, object]:
    violations: list[str] = []
    for directory in (EXPLAIN_DIR, FACTS_DIR):
        for path in _py_files(directory):
            if path in LEGACY_PROSE_ALLOWLIST:
                continue
            text = path.read_text(encoding="utf-8")
            for pattern in FORBIDDEN_STUDENT_COPY_PATTERNS:
                if pattern.search(text):
                    violations.append(f"{path.relative_to(ROOT)}: {pattern.pattern}")
    narrative_exists = all(
        (NARRATIVE_DIR / name).is_file() for name in ("builder.py", "types.py", "legacy_adapter.py")
    )
    facts_exists = all((FACTS_DIR / name).is_file() for name in ("types.py", "assembler.py"))
    explain_facts_exists = (EXPLAIN_DIR / "facts.py").is_file()
    return {
        "narrative_package": narrative_exists,
        "facts_package": facts_exists,
        "explainability_facts_module": explain_facts_exists,
        "student_copy_violations": violations,
        "narrative_owner_files": [str(p.relative_to(ROOT)) for p in NARRATIVE_OWNER_FILES],
    }


def audit_explainability_facts_only() -> dict[str, object]:
    from app.services.language_learning_goal.types import LearningGoal
    from app.services.language_listening_challenge import (
        build_initial_challenge_state,
        recommend_challenge_adaptive_listening_plan,
    )
    from app.services.language_listening_confidence import build_initial_confidence_state
    from app.services.language_listening_explainability import (
        build_explainability_facts_from_body,
        generate_listening_explainability,
    )
    from app.services.language_listening_explainability.facts import ExplainabilityFacts

    confidence_state = build_initial_confidence_state("B1")
    challenge_state = build_initial_challenge_state("B1")
    ch_rec = recommend_challenge_adaptive_listening_plan(
        "B1",
        [],
        [],
        confidence_state,
        challenge_state,
        learning_goal=LearningGoal.business,
        themes="mixed",
        topics="office",
        weaknesses=["main_idea"],
        generation_index=0,
    )
    objectives = ch_rec.objectives
    questions = [{"type": oid, "stem": "?", "choices": ["A", "B"], "correct_index": 0} for oid in objectives[:3]]
    body = {
        "level": "B1",
        "questions": questions,
        "listening_intelligence": ch_rec.plan.to_metadata(),
        "listening_curriculum": ch_rec.to_metadata() if hasattr(ch_rec, "to_metadata") else {},
    }
    # rebuild body like verify 3.4
    from app.services.language_listening_intelligence import HISTORY_KEY
    from app.services.language_listening_curriculum import CURRICULUM_KEY
    from app.services.language_learning_goal import GOAL_KEY
    from app.services.language_listening_confidence import LESSON_CONFIDENCE_KEY
    from app.services.language_listening_challenge import LESSON_CHALLENGE_KEY

    plan = ch_rec.plan
    conf_rec = ch_rec.confidence_aware
    goal_rec = conf_rec.goal_aware
    rec = conf_rec.recommendation
    body = {
        "level": plan.level,
        "questions": questions,
        HISTORY_KEY: plan.to_metadata(),
        CURRICULUM_KEY: rec.to_metadata(),
        GOAL_KEY: goal_rec.to_metadata() if goal_rec else {},
        LESSON_CONFIDENCE_KEY: conf_rec.to_metadata(),
        LESSON_CHALLENGE_KEY: ch_rec.to_metadata(),
    }

    facts = build_explainability_facts_from_body(
        body,
        confidence_state=confidence_state,
        challenge_state=challenge_state,
        cefr_level="B1",
    )
    assert isinstance(facts, ExplainabilityFacts)

    facts_dict = facts.to_dict()
    serialized = json.dumps(facts_dict)

    # Facts must not contain legacy student-summary phrases.
    forbidden_in_facts = [
        "You are improving in:",
        "Today's practice targets:",
        "Today's situation is",
    ]
    facts_clean = all(phrase not in serialized for phrase in forbidden_in_facts)

    result = generate_listening_explainability(
        body,
        confidence_state=confidence_state,
        challenge_state=challenge_state,
        cefr_level="B1",
    )
    has_facts = result.facts is not None
    lesson_fields_populated = all(
        str(result.lesson.to_dict().get(field, "")).strip()
        for field in ("why_this_lesson", "challenge_reason", "student_tip")
    )
    student_fields_populated = all(
        str(result.student_summary.to_dict().get(field, "")).strip()
        for field in ("why_today_matters", "what_needs_practice")
    )

    return {
        "facts_type_ok": True,
        "facts_no_student_phrases": facts_clean,
        "result_has_facts": has_facts,
        "legacy_lesson_fields_populated": lesson_fields_populated,
        "legacy_student_fields_populated": student_fields_populated,
        "sample_fact_keys": sorted(facts_dict.keys()),
    }


def audit_narrative_builder_outputs() -> dict[str, object]:
    from app.services.language_learning_facts.assembler import assemble_lesson_facts, assemble_progression_facts
    from app.services.language_learning_narrative.builder import build_lesson_narrative
    from app.services.language_listening_explainability.facts import build_explainability_facts_from_body

    body = {
        "level": "A2",
        "questions": [{"type": "main_idea", "stem": "?", "choices": ["A", "B"], "correct_index": 0}],
        "listening_intelligence": {
            "situation": "office",
            "category": "work",
            "narrative_format": "dialogue",
            "pace": "normal",
            "difficulty_band": "normal",
            "level": "A2",
        },
        "listening_curriculum": {
            "lesson_intent": "weak_skill_recovery",
            "curriculum_stage": "building",
            "skill_focus": ["main_idea", "detail"],
            "objectives": ["main_idea"],
            "review_objectives": [],
            "knowledge_node": "workplace_basics",
            "recommendation_score": 0.82,
        },
        "listening_learning_goal": {
            "learning_goal": "business",
            "goal_alignment_score": 0.76,
            "goal_profile": "Business",
        },
        "listening_challenge_lesson": {
            "challenge_level": "normal",
            "challenge_label": "A2 Normal",
            "challenge_score": 0.5,
            "effective_difficulty_band": "normal",
        },
    }
    lesson_facts = assemble_lesson_facts(body, lesson_title="Work Stress", lesson_level="A2")
    explain = build_explainability_facts_from_body(body, cefr_level="A2", official_level="A2")
    progression = assemble_progression_facts(official_level="A2", journey_target_level="B1")
    narrative = build_lesson_narrative(lesson_facts, explain, progression=progression)

    required = (
        "reason_selected",
        "why_this_lesson",
        "student_focus",
        "expected_improvement",
        "reward",
        "coach_summary",
        "challenge_reason",
    )
    populated = {key: bool(str(getattr(narrative, key, "")).strip()) for key in required}
    focus_nonempty = len(narrative.student_focus) > 0

    return {
        "narrative_fields": populated,
        "student_focus_nonempty": focus_nonempty,
        "all_required_populated": all(populated.values()) and focus_nonempty,
    }


def audit_lesson_context_adapter() -> dict[str, object]:
    from types import SimpleNamespace

    from app.services.language_listening_lesson_context import build_listening_lesson_coach_context

    item = SimpleNamespace(
        id=99,
        title="Work Stress — A2 Practice",
        level=SimpleNamespace(value="A2"),
        body_json={
            "questions": [{"type": "main_idea", "stem": "?", "choices": ["A", "B"], "correct_index": 0}],
            "listening_intelligence": {
                "situation": "office",
                "category": "work",
                "narrative_format": "dialogue",
                "pace": "normal",
                "difficulty_band": "normal",
                "level": "A2",
            },
            "listening_curriculum": {
                "lesson_intent": "weak_skill_recovery",
                "skill_focus": ["main_idea"],
                "objectives": ["main_idea"],
                "recommendation_score": 0.8,
            },
            "listening_learning_goal": {"learning_goal": "business", "goal_profile": "Business"},
            "listening_challenge_lesson": {"challenge_level": "normal", "effective_difficulty_band": "normal"},
        },
    )
    coach = build_listening_lesson_coach_context(item, official_cefr="A2", target_cefr="B1")
    return {
        "coach_has_why": bool(coach.get("coach_why")),
        "coach_has_focus": bool(coach.get("coach_focus")),
        "coach_has_reward": bool(coach.get("coach_reward")),
        "coach_goal_id": coach.get("learning_goal") == "business",
    }


def main() -> int:
    ownership = audit_narrative_ownership()
    facts_audit = audit_explainability_facts_only()
    narrative_audit = audit_narrative_builder_outputs()
    coach_audit = audit_lesson_context_adapter()

    checks = [
        ("narrative_package", ownership["narrative_package"]),
        ("facts_package", ownership["facts_package"]),
        ("explainability_facts_module", ownership["explainability_facts_module"]),
        ("no_student_copy_in_facts_explain", len(ownership["student_copy_violations"]) == 0),
        ("facts_no_student_phrases", facts_audit["facts_no_student_phrases"]),
        ("result_has_facts", facts_audit["result_has_facts"]),
        ("legacy_lesson_fields_populated", facts_audit["legacy_lesson_fields_populated"]),
        ("legacy_student_fields_populated", facts_audit["legacy_student_fields_populated"]),
        ("narrative_all_required", narrative_audit["all_required_populated"]),
        ("lesson_context_adapter", all(coach_audit.values())),
    ]

    print("LANGUAGE-ADAPTIVE-LEARNING-PHASE-2.1 VERIFICATION")
    print("=" * 58)
    for key, ok in checks:
        print(f"  [{'PASS' if ok else 'FAIL'}] {key}")

    if ownership["student_copy_violations"]:
        print("\nSTUDENT COPY VIOLATIONS:")
        for v in ownership["student_copy_violations"]:
            print(f"  - {v}")

    print("\nFACTS AUDIT")
    print(json.dumps({k: v for k, v in facts_audit.items() if k != "sample_fact_keys"}, indent=2))
    print("\nNARRATIVE AUDIT")
    print(json.dumps(narrative_audit, indent=2))
    print("\nCOACH ADAPTER")
    print(json.dumps(coach_audit, indent=2))

    overall = all(ok for _, ok in checks)
    print(f"\nOVERALL: {'PASS' if overall else 'FAIL'}")
    return 0 if overall else 1


if __name__ == "__main__":
    raise SystemExit(main())
