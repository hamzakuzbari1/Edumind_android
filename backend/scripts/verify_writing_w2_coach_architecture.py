"""Verify Writing W2.1 Coach Architecture (FROZEN — design-only).

Usage (from backend/):
    python scripts/verify_writing_w2_coach_architecture.py
"""

from __future__ import annotations

import ast
import importlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

BACKEND = Path(__file__).resolve().parents[1]
SERVICES = BACKEND / "app" / "services"

from app.services.language_writing.enums import WritingCoachPersonality, WritingGoal  # noqa: E402
from app.services.language_writing.ownership import (  # noqa: E402
    ALLOWED_PACKAGE_DEPENDENCIES,
    ARCHITECTURE_LAYERS,
    PACKAGE_LAYER,
    PACKAGE_OWNERSHIP,
)
from app.services.language_writing_curriculum.goal_profiles import (  # noqa: E402
    GOAL_PROFILE_VERSION,
    WRITING_GOAL_KEY,
    all_writing_goal_profiles,
    profile_for_goal,
)
from app.services.language_writing_coach.personalities import (  # noqa: E402
    GOAL_DEFAULT_PERSONALITY,
    PERSONALITY_CATALOG,
    profile_for_personality,
)
from app.services.language_writing_coach.revision_plan import feedback_fields_complete  # noqa: E402
from app.services.language_writing_coach.types import WritingRevisionPlan  # noqa: E402


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
                imports.add(parts[2])
    return imports


def check_goal_profiles() -> list[bool]:
    results: list[bool] = []
    profiles = all_writing_goal_profiles()
    results.append(_ok("8 writing goal profiles defined", len(profiles) == 8))
    results.append(_ok("all WritingGoal enum covered", len(profiles) == len(WritingGoal)))

    for profile in profiles:
        complete = bool(
            profile.preferred_task_types
            and profile.preferred_genres
            and profile.preferred_mission_style
            and profile.preferred_writing_outputs
            and profile.preferred_vocabulary_categories
            and profile.preferred_grammar_priorities
            and profile.preferred_coach_tone
            and profile.preferred_revision_style
            and profile.preferred_promotion_style
            and profile.vocabulary_style
            and profile.coach_defaults
            and profile.feedback_style
            and profile.wpa_task_bundle_key
        )
        results.append(_ok(f"profile complete: {profile.goal.value}", complete))

    travel = profile_for_goal(WritingGoal.travel)
    results.append(_ok("travel profile prefers complaint task", "complaint" in travel.preferred_task_types))
    results.append(_ok("travel mission style travel_scenario", travel.preferred_mission_style.value == "travel_scenario"))
    results.append(_ok("ielts profile exam promotion style", profile_for_goal(WritingGoal.ielts).preferred_promotion_style.value == "exam_gate"))
    results.append(_ok("goal profile version 2.1.0", GOAL_PROFILE_VERSION == "2.1.0"))
    results.append(_ok("WRITING_GOAL_KEY documented", WRITING_GOAL_KEY == "writing_goal"))
    return results


def check_coach_personalities() -> list[bool]:
    results: list[bool] = []
    results.append(_ok("personality catalog covers enum", len(PERSONALITY_CATALOG) == len(WritingCoachPersonality)))
    for p in WritingCoachPersonality:
        prof = profile_for_personality(p)
        results.append(_ok(f"personality profile: {p.value}", bool(prof.label and prof.tone_directives)))

    results.append(_ok("goal default personality for all goals", len(GOAL_DEFAULT_PERSONALITY) == len(WritingGoal)))
    results.append(_ok("ielts maps to ielts_coach", GOAL_DEFAULT_PERSONALITY[WritingGoal.ielts] == WritingCoachPersonality.ielts_coach))
    results.append(_ok("academic maps to academic_tutor", GOAL_DEFAULT_PERSONALITY[WritingGoal.academic] == WritingCoachPersonality.academic_tutor))
    return results


def check_evaluator_coach_separation() -> list[bool]:
    results: list[bool] = []

    eval_init = (SERVICES / "language_writing_evaluator" / "__init__.py").read_text(encoding="utf-8")
    coach_init = (SERVICES / "language_writing_coach" / "__init__.py").read_text(encoding="utf-8")
    results.append(_ok("evaluator package exists", (SERVICES / "language_writing_evaluator").is_dir()))
    results.append(_ok("evaluator never teaches", "never teaches" in eval_init.lower() or "no coach" in eval_init.lower()))
    results.append(_ok("coach never evaluates", "never evaluates" in coach_init.lower()))

    eval_deps: set[str] = set()
    for py in (SERVICES / "language_writing_evaluator").glob("*.py"):
        eval_deps |= _parse_imports(py)
    results.append(_ok("evaluator does not import coach", "language_writing_coach" not in eval_deps))

    coach_deps: set[str] = set()
    for py in (SERVICES / "language_writing_coach").glob("*.py"):
        coach_deps |= _parse_imports(py)
    results.append(_ok("coach does not import explainability", "language_writing_explainability" not in coach_deps))
    results.append(_ok("coach imports evaluator types", "language_writing_evaluator" in coach_deps))

    from app.services.language_writing_evaluator.types import WritingEvaluationResult  # noqa: WPS433
    from app.services.language_writing_coach.types import CoachInputBundle  # noqa: WPS433

    results.append(_ok("WritingEvaluationResult contract", hasattr(WritingEvaluationResult, "to_facts_dict")))
    results.append(_ok("CoachInputBundle contract", hasattr(CoachInputBundle, "evaluation")))
    return results


def check_revision_plan() -> list[bool]:
    results: list[bool] = []
    sample = WritingRevisionPlan(
        encouragement="Nice progress on clarity.",
        main_issue="Past tense inconsistency",
        priority_fix="Use past simple for completed events",
        concrete_example="I arrived at the airport (not I arrive)",
        revision_mission="Rewrite the delay paragraph using past simple throughout",
        ready_to_complete=False,
        next_lesson_recommendation="Practice sequencers in your next travel note",
        what_improved=("Clear opening sentence",),
    )
    results.append(_ok("revision plan required fields", feedback_fields_complete(sample)))
    d = sample.to_student_dict()
    for key in (
        "encouragement",
        "main_issue",
        "priority_fix",
        "concrete_example",
        "revision_mission",
        "ready_to_complete",
        "next_lesson_recommendation",
    ):
        results.append(_ok(f"student dict has {key}", key in d))

    from app.services.language_writing_revision.types import RevisionWorkflowStage  # noqa: WPS433

    results.append(_ok("revision workflow stages defined", len(RevisionWorkflowStage) >= 6))
    return results


def check_memory_design() -> list[bool]:
    results: list[bool] = []
    from app.services.language_writing_coach.memory_design import (  # noqa: WPS433
        CoachMemorySnapshot,
        MemorySignalKind,
    )

    results.append(_ok("memory signal kinds >= 12", len(MemorySignalKind) >= 12))
    snap = CoachMemorySnapshot(student_id=1)
    ctx = snap.to_coach_context_dict()
    for key in (
        "repeated_mistakes",
        "repeated_strengths",
        "vocabulary_habits",
        "grammar_habits",
        "grammar_trends",
        "vocabulary_trends",
        "writing_speed_trend",
        "revision_behaviour",
        "favorite_topics",
        "avoided_topics",
        "confidence_trend",
        "learning_momentum",
        "preferences",
    ):
        results.append(_ok(f"memory snapshot field: {key}", key in ctx))
    results.append(_ok("memory snapshot version 2.1.0", snap.snapshot_version == "2.1.0"))
    return results


def check_adaptive_tone() -> list[bool]:
    results: list[bool] = []
    from app.services.language_writing_coach.adaptive_tone import (  # noqa: WPS433
        ADAPTIVE_TONE_INVARIANTS,
        AdaptiveToneContext,
        AdaptiveToneTrigger,
        TONE_ADJUSTMENT_MAP,
    )

    results.append(_ok("5 adaptive tone triggers", len(AdaptiveToneTrigger) == 5))
    results.append(_ok("tone adjustment map complete", len(TONE_ADJUSTMENT_MAP) == len(AdaptiveToneTrigger)))
    ctx = AdaptiveToneContext.resolve(
        personality=WritingCoachPersonality.friendly_teacher,
        triggers=(AdaptiveToneTrigger.student_frustration,),
    )
    results.append(_ok("adaptive tone resolves adjustments", len(ctx.adjustments) > 0))
    results.append(_ok("adaptive tone invariants documented", len(ADAPTIVE_TONE_INVARIANTS) >= 4))
    results.append(_ok("adaptive_tone.py exists", (SERVICES / "language_writing_coach" / "adaptive_tone.py").is_file()))
    return results


def check_mission_layer() -> list[bool]:
    results: list[bool] = []
    from app.services.language_writing_coach.mission_layer import (  # noqa: WPS433
        COACH_MISSION_LAYER_VERSION,
        WritingCoachMission,
        mission_fields_complete,
    )

    sample = WritingCoachMission(
        todays_mission="Write a polite email about your delayed flight.",
        todays_focus="Past simple and polite requests",
        todays_goal="Explain the problem and ask for a refund",
        success_criteria=("Clear problem statement", "Polite request", "Formal greeting and closing"),
        expected_learning_outcomes=("Write a formal email", "Request politely"),
        goal_label="Travel",
        mission_style="travel_scenario",
    )
    results.append(_ok("coach mission required fields", mission_fields_complete(sample)))
    d = sample.to_student_dict()
    for key in ("todays_mission", "todays_focus", "todays_goal", "success_criteria", "expected_learning_outcomes"):
        results.append(_ok(f"mission dict has {key}", key in d))
    results.append(_ok("mission layer version 2.1.0", COACH_MISSION_LAYER_VERSION == "2.1.0"))
    results.append(_ok("mission_layer.py exists", (SERVICES / "language_writing_coach" / "mission_layer.py").is_file()))
    return results


def check_architecture_frozen() -> list[bool]:
    results: list[bool] = []
    from app.services.language_writing_coach import ARCHITECTURE_VERSION  # noqa: WPS433

    arch_doc = (SERVICES / "language_writing_coach" / "COACH_ARCHITECTURE.md").read_text(encoding="utf-8")
    results.append(_ok("architecture marked FROZEN in doc", "FROZEN" in arch_doc))
    results.append(_ok("coach ARCHITECTURE_VERSION frozen", ARCHITECTURE_VERSION.endswith("frozen")))
    results.append(_ok("freeze policy in doc", "no redesign" in arch_doc.lower()))
    return results


def check_ownership_and_layers() -> list[bool]:
    results: list[bool] = []
    results.append(_ok("evaluator in ownership registry", "language_writing_evaluator" in PACKAGE_OWNERSHIP))
    results.append(_ok("evaluation layer exists", "evaluation" in ARCHITECTURE_LAYERS))
    results.append(_ok("evaluator layer assignment", PACKAGE_LAYER.get("language_writing_evaluator") == "evaluation"))

    allowed_coach = ALLOWED_PACKAGE_DEPENDENCIES.get("language_writing_coach", frozenset())
    results.append(_ok("coach allowed evaluator import", "language_writing_evaluator" in allowed_coach))
    results.append(_ok("explainability allowed evaluator import", "language_writing_evaluator" in ALLOWED_PACKAGE_DEPENDENCIES.get("language_writing_explainability", frozenset())))

    # Layer order: evaluator below coach
    layer_index = {name: i for i, name in enumerate(ARCHITECTURE_LAYERS)}
    results.append(
        _ok(
            "evaluator below coach in layers",
            layer_index["evaluation"] < layer_index["pedagogy"],
        )
    )
    return results


def check_narrative_ownership() -> list[bool]:
    results: list[bool] = []
    exp_init = (SERVICES / "language_writing_explainability" / "__init__.py").read_text(encoding="utf-8")
    results.append(_ok("explainability owns facts", "facts" in exp_init.lower()))
    results.append(_ok("FEEDBACK_LAYERS doc exists", (SERVICES / "language_writing_coach" / "FEEDBACK_LAYERS.md").is_file()))
    results.append(_ok("COACH_ARCHITECTURE doc exists", (SERVICES / "language_writing_coach" / "COACH_ARCHITECTURE.md").is_file()))

    from app.schemas import language_writing_bundles as bundles  # noqa: WPS433

    results.append(_ok("WritingRevisionPlanOut schema", hasattr(bundles, "WritingRevisionPlanOut")))
    results.append(_ok("WritingCoachMissionOut schema", hasattr(bundles, "WritingCoachMissionOut")))
    results.append(_ok("facts bundle includes evaluation slot", "evaluation" in WritingFactsBundle_fields()))
    return results


def WritingFactsBundle_fields() -> set[str]:
    from app.services.language_writing_explainability.types import WritingFactsBundle  # noqa: WPS433

    return {f.name for f in WritingFactsBundle.__dataclass_fields__.values()}


def check_architecture_imports() -> list[bool]:
    results: list[bool] = []
    for pkg in ("language_writing_evaluator", "language_writing_coach", "language_writing_curriculum"):
        try:
            importlib.import_module(f"app.services.{pkg}.types")
            results.append(_ok(f"import types: {pkg}", True))
        except Exception as exc:  # noqa: BLE001
            results.append(_ok(f"import types: {pkg}", False, str(exc)))
    return results


def main() -> int:
    print("Writing W2.1 Coach Architecture Verification (FROZEN)\n")
    sections = [
        ("Goal profiles", check_goal_profiles),
        ("Coach personalities", check_coach_personalities),
        ("Evaluator/coach separation", check_evaluator_coach_separation),
        ("Revision plan", check_revision_plan),
        ("Coach memory design", check_memory_design),
        ("Adaptive coach tone", check_adaptive_tone),
        ("Coach mission layer", check_mission_layer),
        ("Architecture frozen", check_architecture_frozen),
        ("Ownership & layers", check_ownership_and_layers),
        ("Narrative ownership", check_narrative_ownership),
        ("Architecture imports", check_architecture_imports),
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
        print("W2.1 FROZEN — Coach architecture complete. Do not start W3 until approved.")
        return 0
    print("W2.1 FAILED — fix architecture before proceeding.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
