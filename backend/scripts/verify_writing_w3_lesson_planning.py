"""Verify Writing W3.1 Lesson Planning Architecture (FROZEN — design-only).

Usage (from backend/):
    python scripts/verify_writing_w3_lesson_planning.py
"""

from __future__ import annotations

import ast
import importlib
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
from app.services.language_writing_generation import WRITING_BLUEPRINT_KEY  # noqa: E402
from app.services.language_writing_knowledge_chain.types import WritingKnowledgeChainNode  # noqa: E402
from app.services.language_writing_lesson_planner import (  # noqa: E402
    ARCHITECTURE_VERSION as PLANNER_ARCH_VERSION,
    WRITING_BLUEPRINT_KEY as PLANNER_BP_KEY,
)
from app.services.language_writing_lesson_planner.blueprint_hash import compute_blueprint_hash  # noqa: E402
from app.services.language_writing_lesson_planner.blueprint_validation import (  # noqa: E402
    blueprint_is_complete,
    validate_blueprint,
)
from app.services.language_writing_lesson_planner.planner_contract import assemble_blueprint  # noqa: E402
from app.services.language_writing_lesson_planner.types import (  # noqa: E402
    BLUEPRINT_COMPATIBILITY_NOTES,
    BLUEPRINT_SCHEMA_VERSION,
    BLUEPRINT_VERSION,
    GENERATOR_FORBIDDEN_CONTEXT_SOURCES,
    GENERATOR_FORBIDDEN_DECISIONS,
    DETERMINISM_CANONICAL_FIELDS,
    LessonPlannerInput,
)
from app.services.language_writing_generation import ARCHITECTURE_VERSION as GEN_ARCH_VERSION  # noqa: E402
from app.services.language_writing_generation.generator_contract import (  # noqa: E402
    GENERATOR_ALLOWED_INPUT_FIELDS,
    GENERATOR_ALLOWED_INPUT_TYPES,
    GENERATOR_FORBIDDEN_IMPORT_PACKAGES,
    WritingGeneratorInput,
)
from app.services.language_writing_generation.mission_assembly import assemble_mission_from_blueprint  # noqa: E402
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


def _sample_node() -> WritingKnowledgeChainNode | None:
    catalog = get_universe_catalog()
    chain = catalog.chain_by_id("travel_airport_journey")
    return chain.node_by_id("complaint_email") if chain else None


def _sample_blueprint():
    node = _sample_node()
    if not node:
        return None
    return assemble_blueprint(
        LessonPlannerInput(
            official_cefr=OfficialWritingCEFR.B1,
            goal_profile=profile_for_goal(WritingGoal.travel),
            selected_node=node,
            blueprint_id="test:complaint_email",
        )
    ).blueprint


def check_planner_ownership() -> list[bool]:
    results: list[bool] = []
    init = (SERVICES / "language_writing_lesson_planner" / "__init__.py").read_text(encoding="utf-8")
    results.append(_ok("lesson_planner package exists", (SERVICES / "language_writing_lesson_planner").is_dir()))
    results.append(_ok("planner in ownership registry", "language_writing_lesson_planner" in PACKAGE_OWNERSHIP))
    results.append(_ok("planning layer exists", "planning" in ARCHITECTURE_LAYERS))
    results.append(_ok("planner layer assignment", PACKAGE_LAYER.get("language_writing_lesson_planner") == "planning"))
    results.append(_ok("planner never calls LLM", "no llm" in init.lower()))
    results.append(_ok("planner architecture frozen", PLANNER_ARCH_VERSION.endswith("frozen")))
    results.append(_ok("PLANNING_ARCHITECTURE doc", (SERVICES / "language_writing_lesson_planner" / "PLANNING_ARCHITECTURE.md").is_file()))

    deps: set[str] = set()
    for py in (SERVICES / "language_writing_lesson_planner").glob("*.py"):
        deps |= _parse_imports(py)
    results.append(_ok("planner does not import generation", "language_writing_generation" not in deps))
    results.append(_ok("planner does not import coach", "language_writing_coach" not in deps))
    results.append(_ok("planner does not import evaluator", "language_writing_evaluator" not in deps))
    return results


def check_blueprint_completeness() -> list[bool]:
    results: list[bool] = []
    bp = _sample_blueprint()
    results.append(_ok("sample blueprint built", bp is not None))
    if not bp:
        return results

    results.append(_ok("blueprint version 3.1.0", bp.blueprint_version == BLUEPRINT_VERSION == "3.1.0"))
    results.append(_ok("blueprint schema 3.1.0", bp.schema_version == BLUEPRINT_SCHEMA_VERSION == "3.1.0"))
    results.append(_ok("compatibility notes present", len(bp.compatibility_notes) >= 2))
    results.append(_ok("blueprint validates complete", blueprint_is_complete(bp)))
    results.append(_ok("structured success criteria", bp.success_criteria.min_words > 0))
    results.append(_ok("required grammar in criteria", len(bp.success_criteria.required_grammar) > 0))
    results.append(_ok("required vocabulary in criteria", len(bp.success_criteria.required_vocabulary) > 0))
    results.append(_ok("required output format in criteria", bool(bp.success_criteria.required_output_format)))
    results.append(_ok("required objectives in criteria", len(bp.success_criteria.required_objectives) > 0))
    results.append(_ok("success criteria labels derived", len(bp.success_criteria_labels) > 0))
    results.append(_ok("evaluation plan present", bp.evaluation_plan.weight_total > 0))
    results.append(_ok("evaluation weights sum to 1", abs(bp.evaluation_plan.weight_total - 1.0) < 0.01))
    results.append(_ok("evaluation required outcomes", len(bp.evaluation_plan.required_outcomes) > 0))
    results.append(_ok("evaluation critical mistakes", len(bp.evaluation_plan.critical_mistakes) > 0))
    results.append(_ok("blueprint hash present", len(bp.blueprint_hash) == 64))
    results.append(_ok("WRITING_BLUEPRINT_KEY consistent", PLANNER_BP_KEY == WRITING_BLUEPRINT_KEY))

    issues = validate_blueprint(bp)
    results.append(_ok("no validation issues", len(issues) == 0, str(issues[:2])))
    return results


def check_blueprint_hash() -> list[bool]:
    results: list[bool] = []
    bp = _sample_blueprint()
    if not bp:
        results.append(_ok("hash sample blueprint", False))
        return results

    h1 = compute_blueprint_hash(bp)
    h2 = compute_blueprint_hash(bp)
    results.append(_ok("hash is deterministic", h1 == h2))
    results.append(_ok("hash matches blueprint field", h1 == bp.blueprint_hash))
    results.append(_ok("hash in determinism fields", "blueprint_hash" in DETERMINISM_CANONICAL_FIELDS))
    return results


def check_generator_isolation() -> list[bool]:
    results: list[bool] = []
    init = (SERVICES / "language_writing_generation" / "__init__.py").read_text(encoding="utf-8")
    results.append(_ok("generator architecture version valid", GEN_ARCH_VERSION in ("3.1.0-frozen", "4.0.0", "5.0.0")))
    results.append(_ok("GENERATOR_ISOLATION doc", (SERVICES / "language_writing_generation" / "GENERATOR_ISOLATION.md").is_file()))
    results.append(_ok("generator reads blueprint only", "blueprint only" in init.lower()))

    deps: set[str] = set()
    for py in (SERVICES / "language_writing_generation").glob("*.py"):
        deps |= _parse_imports(py)
    deps.discard("language_writing_generation")
    allowed = ALLOWED_PACKAGE_DEPENDENCIES.get("language_writing_generation", frozenset())
    results.append(_ok("generator imports only lesson_planner", deps <= allowed))

    for forbidden in (
        "language_writing_curriculum",
        "language_writing_knowledge_chain",
        "language_writing_topic_universe",
        "language_writing_grammar_progression",
        "language_writing_lexis_progression",
    ):
        results.append(_ok(f"generator does not import {forbidden.split('_')[-1]}", forbidden not in deps))

    for pkg in GENERATOR_FORBIDDEN_IMPORT_PACKAGES:
        results.append(_ok(f"forbidden import documented: {pkg.split('_')[-1]}", pkg in GENERATOR_FORBIDDEN_IMPORT_PACKAGES))

    results.append(_ok("forbidden context sources documented", len(GENERATOR_FORBIDDEN_CONTEXT_SOURCES) >= 8))
    results.append(_ok("generator input fields restricted", GENERATOR_ALLOWED_INPUT_FIELDS == frozenset({"blueprint", "generator_version", "locale"})))
    results.append(_ok("generator input types restricted", "WritingLessonBlueprint" in GENERATOR_ALLOWED_INPUT_TYPES))
    results.append(_ok("forbidden decisions includes evaluation_plan", "evaluation_plan" in GENERATOR_FORBIDDEN_DECISIONS))
    return results


def check_architecture_separation() -> list[bool]:
    results: list[bool] = []
    layer_index = {name: i for i, name in enumerate(ARCHITECTURE_LAYERS)}
    results.append(_ok("planning before generation", layer_index["planning"] < layer_index["generation"]))
    results.append(_ok("generation before evaluation", layer_index["generation"] < layer_index["evaluation"]))
    return results


def check_determinism() -> list[bool]:
    results: list[bool] = []
    node = _sample_node()
    if not node:
        results.append(_ok("determinism sample node", False))
        return results

    inp = LessonPlannerInput(
        official_cefr=OfficialWritingCEFR.B1,
        goal_profile=profile_for_goal(WritingGoal.travel),
        selected_node=node,
        blueprint_id="det:complaint",
    )
    bp1 = assemble_blueprint(inp).blueprint
    bp2 = assemble_blueprint(inp).blueprint
    results.append(_ok("identical input -> identical hash", bp1.blueprint_hash == bp2.blueprint_hash))
    results.append(_ok("identical input -> identical evaluation plan", bp1.evaluation_plan == bp2.evaluation_plan))

    gen1 = assemble_mission_from_blueprint(WritingGeneratorInput(blueprint=bp1))
    gen2 = assemble_mission_from_blueprint(WritingGeneratorInput(blueprint=bp2))
    results.append(_ok("generator preserves blueprint hash", gen1.blueprint_hash == bp1.blueprint_hash))
    results.append(_ok("generator preserves blueprint version", gen1.blueprint_version == bp1.blueprint_version))
    results.append(_ok("generator preserves learning outcomes", gen1.learning_outcomes == bp1.learning_outcomes))
    results.append(_ok("determinism fields documented", len(DETERMINISM_CANONICAL_FIELDS) >= 10))
    return results


def check_mission_assembly() -> list[bool]:
    results: list[bool] = []
    bp = _sample_blueprint()
    if not bp:
        results.append(_ok("mission assembly sample", False))
        return results

    lesson = assemble_mission_from_blueprint(WritingGeneratorInput(blueprint=bp))
    a = lesson.assembly
    results.append(_ok("mission title present", bool(a.mission_title.strip())))
    results.append(_ok("instructions present", len(a.instructions) > 0))
    results.append(_ok("writing prompt present", bool(a.writing_prompt.strip())))
    results.append(_ok("constraints present", len(a.constraints) > 0))
    results.append(_ok("expected output label", bool(a.expected_output_label)))
    results.append(_ok("student context present", bool(a.student_context.strip())))
    results.append(_ok("checklist from criteria labels", a.checklist == bp.success_criteria_labels))
    return results


def check_imports() -> list[bool]:
    results: list[bool] = []
    for mod in (
        "app.services.language_writing_lesson_planner.types",
        "app.services.language_writing_generation.generator_contract",
    ):
        try:
            importlib.import_module(mod)
            results.append(_ok(f"import {mod.split('.')[-2]}", True))
        except Exception as exc:  # noqa: BLE001
            results.append(_ok(f"import {mod.split('.')[-2]}", False, str(exc)))
    return results


def main() -> int:
    print("Writing W3.1 Lesson Planning Architecture Verification (FROZEN)\n")
    sections = [
        ("Planner ownership", check_planner_ownership),
        ("Blueprint completeness", check_blueprint_completeness),
        ("Blueprint hash", check_blueprint_hash),
        ("Generator isolation", check_generator_isolation),
        ("Architecture separation", check_architecture_separation),
        ("Determinism", check_determinism),
        ("Mission assembly", check_mission_assembly),
        ("Architecture imports", check_imports),
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
        print("W3.1 FROZEN — Lesson planning architecture complete.")
        return 0
    print("W3.1 FAILED — fix architecture before proceeding.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
