"""Verify Writing W4 Lesson Experience Architecture (design-only).

Usage (from backend/):
    python scripts/verify_writing_w4_lesson_experience.py
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
from app.services.language_writing_generation import ARCHITECTURE_VERSION as GEN_ARCH_VERSION  # noqa: E402
from app.services.language_writing_generation.generator_contract import WritingGeneratorInput  # noqa: E402
from app.services.language_writing_generation.mission_assembly import assemble_mission_from_blueprint  # noqa: E402
from app.services.language_writing_generation.mission_builder import build_mission_from_blueprint  # noqa: E402
from app.services.language_writing_generation.mission_builder_types import (  # noqa: E402
    MISSION_BUILDER_VERSION,
    mission_fields_complete,
)
from app.services.language_writing_generation.prompt_builder import build_prompt_from_blueprint  # noqa: E402
from app.services.language_writing_generation.prompt_builder_types import (  # noqa: E402
    LLM_FORBIDDEN_DIRECT_ACCESS,
    PROMPT_FORBIDDEN_CONTEXT_SOURCES,
    PROMPT_BUILDER_VERSION,
    PromptSectionKey,
)
from app.services.language_writing_knowledge_chain.types import WritingKnowledgeChainNode  # noqa: E402
from app.services.language_writing_lesson_experience import EXPERIENCE_SCHEMA_VERSION  # noqa: E402
from app.services.language_writing_lesson_experience.experience_assembler import (  # noqa: E402
    assemble_student_lesson_experience,
)
from app.services.language_writing_lesson_experience.student_lesson_types import (  # noqa: E402
    STUDENT_LESSON_SCHEMA_VERSION,
    student_lesson_fields_complete,
)
from app.services.language_writing_lesson_planner.planner_contract import assemble_blueprint  # noqa: E402
from app.services.language_writing_lesson_planner.types import LessonPlannerInput  # noqa: E402
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
            blueprint_id="w4:test:complaint_email",
        )
    ).blueprint


def check_mission_builder_ownership() -> list[bool]:
    results: list[bool] = []
    gen_dir = SERVICES / "language_writing_generation"
    results.append(_ok("mission_builder module exists", (gen_dir / "mission_builder.py").is_file()))
    results.append(_ok("mission_builder_types module exists", (gen_dir / "mission_builder_types.py").is_file()))
    results.append(_ok("generation in ownership registry", "language_writing_generation" in PACKAGE_OWNERSHIP))
    results.append(_ok("generation layer assignment", PACKAGE_LAYER.get("language_writing_generation") == "generation"))
    results.append(_ok("mission builder version 4.0.0", MISSION_BUILDER_VERSION == "4.0.0"))
    results.append(_ok("W4 generation architecture version", GEN_ARCH_VERSION in ("4.0.0", "5.0.0")))

    mb_text = (gen_dir / "mission_builder.py").read_text(encoding="utf-8")
    results.append(_ok("mission builder docstring: blueprint only", "blueprint" in mb_text.lower()))
    results.append(_ok("mission builder docstring: no decisions", "never makes educational decisions" in mb_text.lower()))

    deps: set[str] = set()
    for name in ("mission_builder.py", "mission_builder_types.py"):
        deps |= _parse_imports(gen_dir / name)
    allowed = ALLOWED_PACKAGE_DEPENDENCIES.get("language_writing_generation", frozenset())
    results.append(_ok("mission builder imports only allowed deps", deps <= allowed | {"language_writing_generation"}))
    return results


def check_prompt_builder_ownership() -> list[bool]:
    results: list[bool] = []
    gen_dir = SERVICES / "language_writing_generation"
    results.append(_ok("prompt_builder module exists", (gen_dir / "prompt_builder.py").is_file()))
    results.append(_ok("prompt_builder_types module exists", (gen_dir / "prompt_builder_types.py").is_file()))
    results.append(_ok("prompt builder version 4.0.0", PROMPT_BUILDER_VERSION == "4.0.0"))
    results.append(_ok("LLM_BOUNDARY doc exists", (gen_dir / "LLM_BOUNDARY.md").is_file()))

    pb_text = (gen_dir / "prompt_builder.py").read_text(encoding="utf-8")
    results.append(_ok("prompt builder: no LLM calls in W4", "no llm calls" in pb_text.lower()))

    deps: set[str] = set()
    for name in ("prompt_builder.py", "prompt_builder_types.py"):
        deps |= _parse_imports(gen_dir / name)
    allowed = ALLOWED_PACKAGE_DEPENDENCIES.get("language_writing_generation", frozenset())
    results.append(_ok("prompt builder imports only allowed deps", deps <= allowed | {"language_writing_generation"}))
    results.append(_ok("prompt builder does not import lesson_experience", "language_writing_lesson_experience" not in deps))
    results.append(_ok("forbidden context sources documented", len(PROMPT_FORBIDDEN_CONTEXT_SOURCES) >= 8))
    results.append(_ok("LLM forbidden direct access documented", "WritingLessonBlueprint" in LLM_FORBIDDEN_DIRECT_ACCESS))
    return results


def check_no_duplicated_assembly() -> list[bool]:
    results: list[bool] = []
    shim = (SERVICES / "language_writing_generation" / "mission_assembly.py").read_text(encoding="utf-8")
    results.append(_ok("mission_assembly delegates to mission_builder", "build_mission_from_blueprint" in shim))
    results.append(_ok("mission_assembly does not re-derive title inline", "goal_profile_label" not in shim))

    bp = _sample_blueprint()
    if not bp:
        results.append(_ok("no-duplication sample blueprint", False))
        return results

    mission = build_mission_from_blueprint(bp)
    legacy = assemble_mission_from_blueprint(WritingGeneratorInput(blueprint=bp))
    results.append(_ok("legacy title matches mission builder", legacy.assembly.mission_title == mission.mission_title))
    results.append(_ok("legacy instructions match mission builder", legacy.assembly.instructions == mission.instructions))
    results.append(_ok("legacy checklist matches mission builder", legacy.assembly.checklist == mission.checklist))
    results.append(_ok("legacy hash matches mission builder", legacy.blueprint_hash == mission.blueprint_hash))
    return results


def check_prompt_isolation() -> list[bool]:
    results: list[bool] = []
    bp = _sample_blueprint()
    if not bp:
        results.append(_ok("prompt isolation sample blueprint", False))
        return results

    bundle = build_prompt_from_blueprint(bp)
    prompt_dict = bundle.to_prompt_dict()
    for key in PromptSectionKey:
        results.append(_ok(f"prompt section present: {key.value}", key.value in prompt_dict and bool(prompt_dict[key.value].strip())))

    forbidden_tokens = ("student_id", "topic_universe", "knowledge_chain", "lessonplannerinput")
    combined = "\n".join(prompt_dict.values()).lower()
    for token in forbidden_tokens:
        results.append(_ok(f"prompt content avoids raw context token {token}", token not in combined))

    results.append(_ok("prompt bundle echoes blueprint hash", bundle.blueprint_hash == bp.blueprint_hash))
    results.append(_ok("prompt bundle echoes blueprint id", bundle.blueprint_id == bp.blueprint_id))
    return results


def check_student_lesson_experience() -> list[bool]:
    results: list[bool] = []
    exp_dir = SERVICES / "language_writing_lesson_experience"
    results.append(_ok("student_lesson_types module exists", (exp_dir / "student_lesson_types.py").is_file()))
    results.append(_ok("experience_assembler module exists", (exp_dir / "experience_assembler.py").is_file()))
    results.append(_ok("LESSON_EXPERIENCE_ARCHITECTURE doc", (exp_dir / "LESSON_EXPERIENCE_ARCHITECTURE.md").is_file()))
    results.append(_ok("lesson_experience in ownership registry", "language_writing_lesson_experience" in PACKAGE_OWNERSHIP))
    results.append(_ok("experience layer assignment", PACKAGE_LAYER.get("language_writing_lesson_experience") == "experience"))
    results.append(_ok("experience schema version 4.0.0", EXPERIENCE_SCHEMA_VERSION == STUDENT_LESSON_SCHEMA_VERSION == "4.0.0"))

    bp = _sample_blueprint()
    if not bp:
        results.append(_ok("student lesson sample blueprint", False))
        return results

    lesson = assemble_student_lesson_experience(bp)
    results.append(_ok("student lesson fields complete", student_lesson_fields_complete(lesson)))
    results.append(_ok("mission title present", bool(lesson.mission_title.strip())))
    results.append(_ok("writing context present", bool(lesson.writing_context.strip())))
    results.append(_ok("instructions present", len(lesson.instructions) > 0))
    results.append(_ok("checklist present", len(lesson.checklist) > 0))
    results.append(_ok("learning outcomes present", len(lesson.learning_outcomes) > 0))
    results.append(_ok("estimated time positive", lesson.estimated_time.total_minutes > 0))
    results.append(_ok("expected output present", bool(lesson.expected_output)))
    results.append(_ok("constraints present", len(lesson.constraints) > 0))
    results.append(_ok("success criteria present", len(lesson.success_criteria) > 0))
    results.append(_ok("tips present", len(lesson.tips) > 0))
    results.append(_ok("writing prompt present", bool(lesson.writing_prompt.strip())))
    results.append(_ok("blueprint hash preserved", lesson.blueprint_hash == bp.blueprint_hash))

    student_dict = lesson.to_student_dict()
    required_keys = {
        "mission_title",
        "writing_context",
        "instructions",
        "checklist",
        "learning_outcomes",
        "estimated_time",
        "expected_output",
        "constraints",
        "success_criteria",
        "tips",
        "writing_prompt",
        "blueprint_hash",
    }
    results.append(_ok("student dict has all visible fields", required_keys <= set(student_dict.keys())))
    return results


def check_pipeline_layers() -> list[bool]:
    results: list[bool] = []
    layer_index = {name: i for i, name in enumerate(ARCHITECTURE_LAYERS)}
    results.append(_ok("planning before generation", layer_index["planning"] < layer_index["generation"]))
    results.append(_ok("generation before experience", layer_index["generation"] < layer_index["experience"]))
    results.append(_ok("experience may import generation", "language_writing_generation" in ALLOWED_PACKAGE_DEPENDENCIES.get("language_writing_lesson_experience", frozenset())))
    return results


def check_mission_completeness() -> list[bool]:
    results: list[bool] = []
    bp = _sample_blueprint()
    if not bp:
        results.append(_ok("mission completeness sample", False))
        return results

    mission = build_mission_from_blueprint(bp)
    results.append(_ok("mission fields complete", mission_fields_complete(mission)))
    results.append(_ok("mission learning outcomes from blueprint", mission.learning_outcomes == bp.learning_outcomes))
    results.append(_ok("mission success criteria from blueprint", mission.success_criteria == bp.success_criteria_labels))
    return results


def check_imports() -> list[bool]:
    results: list[bool] = []
    for mod in (
        "app.services.language_writing_generation.mission_builder",
        "app.services.language_writing_generation.prompt_builder",
        "app.services.language_writing_lesson_experience.experience_assembler",
        "app.services.language_writing_lesson_experience.student_lesson_types",
    ):
        try:
            importlib.import_module(mod)
            results.append(_ok(f"import {mod.split('.')[-1]}", True))
        except Exception as exc:  # noqa: BLE001
            results.append(_ok(f"import {mod.split('.')[-1]}", False, str(exc)))
    return results


def main() -> int:
    print("Writing W4 Lesson Experience Architecture Verification\n")
    sections = [
        ("Mission Builder ownership", check_mission_builder_ownership),
        ("Prompt Builder ownership", check_prompt_builder_ownership),
        ("No duplicated assembly", check_no_duplicated_assembly),
        ("Prompt isolation", check_prompt_isolation),
        ("Student Lesson Experience", check_student_lesson_experience),
        ("Pipeline layers", check_pipeline_layers),
        ("Mission completeness", check_mission_completeness),
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
        print("W4 COMPLETE — Lesson Experience architecture ready. No runtime. No LLM. Stop after W4.")
        return 0
    print("W4 FAILED — fix architecture before proceeding.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
