"""Verify Writing W5 Generation Architecture (design-only).

Usage (from backend/):
    python scripts/verify_writing_w5_generation.py
"""

from __future__ import annotations

import ast
import importlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

BACKEND = Path(__file__).resolve().parents[1]
SERVICES = BACKEND / "app" / "services"
GEN_DIR = SERVICES / "language_writing_generation"

from app.services.language_writing.enums import OfficialWritingCEFR, WritingGoal  # noqa: E402
from app.services.language_writing.ownership import (  # noqa: E402
    ALLOWED_PACKAGE_DEPENDENCIES,
    PACKAGE_OWNERSHIP,
)
from app.services.language_writing_curriculum.goal_profiles import profile_for_goal  # noqa: E402
from app.services.language_writing_generation import (  # noqa: E402
    ARCHITECTURE_VERSION,
    GENERATOR_PIPELINE_VERSION,
    NORMALIZER_VERSION,
    PROMPT_BUILDER_VERSION,
    REPAIR_LAYER_VERSION,
    VALIDATOR_VERSION,
)
from app.services.language_writing_generation.audit_types import GENERATION_AUDIT_VERSION  # noqa: E402
from app.services.language_writing_generation.failure_strategy import (  # noqa: E402
    HARD_FAILURE_TRIGGERS,
    SOFT_FAILURE_TRIGGERS,
)
from app.services.language_writing_generation.generation_hash import compute_generation_hash  # noqa: E402
from app.services.language_writing_generation.generation_pipeline import process_llm_generation  # noqa: E402
from app.services.language_writing_generation.mission_builder import build_mission_from_blueprint  # noqa: E402
from app.services.language_writing_generation.normalizer_types import (  # noqa: E402
    LLM_FIELD_ALIASES,
    WritingLlmRawResponse,
)
from app.services.language_writing_generation.prompt_builder import build_prompt_from_blueprint  # noqa: E402
from app.services.language_writing_generation.repair_types import (  # noqa: E402
    BLUEPRINT_SOURCED_REPAIRS,
    FORBIDDEN_REPAIR_ACTIONS,
)
from app.services.language_writing_generation.response_normalizer import normalize_llm_response  # noqa: E402
from app.services.language_writing_knowledge_chain.types import WritingKnowledgeChainNode  # noqa: E402
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
            blueprint_id="w5:test:complaint_email",
        )
    ).blueprint


def _mock_llm_json(blueprint, *, complete: bool = True) -> str:
    mission = build_mission_from_blueprint(blueprint)
    payload = {
        "missionTitle": mission.mission_title,
        "writing_context": mission.mission_context,
        "instructions": list(mission.instructions),
        "writing_prompt": mission.writing_prompt,
        "expectedOutput": blueprint.expected_writing_output.value,
        "grammar_display": blueprint.grammar_targets.primary.replace("_", " "),
        "vocabulary_display": ", ".join(blueprint.vocabulary_targets.primary[:4]),
    }
    if complete:
        payload["checklist"] = list(mission.checklist)
        payload["tips"] = list(mission.tips)
        payload["learning_outcomes"] = list(mission.learning_outcomes)
        payload["success_criteria"] = list(mission.success_criteria)
        payload["constraints"] = list(mission.constraints)
    return json.dumps(payload)


def check_normalizer_ownership() -> list[bool]:
    results: list[bool] = []
    results.append(_ok("response_normalizer module exists", (GEN_DIR / "response_normalizer.py").is_file()))
    results.append(_ok("normalizer_types module exists", (GEN_DIR / "normalizer_types.py").is_file()))
    results.append(_ok("normalizer version 5.0.0", NORMALIZER_VERSION == "5.0.0"))

    text = (GEN_DIR / "response_normalizer.py").read_text(encoding="utf-8")
    results.append(_ok("normalizer: no blueprint import", "WritingLessonBlueprint" not in text))
    results.append(_ok("normalizer: no educational logic doc", "no educational" in text.lower() or "structural only" in text.lower()))
    results.append(_ok("field aliases documented", len(LLM_FIELD_ALIASES) >= 10))

    deps = _parse_imports(GEN_DIR / "response_normalizer.py")
    allowed = ALLOWED_PACKAGE_DEPENDENCIES.get("language_writing_generation", frozenset())
    results.append(_ok("normalizer imports only allowed deps", deps <= allowed | {"language_writing_generation"}))
    return results


def check_validator_ownership() -> list[bool]:
    results: list[bool] = []
    results.append(_ok("lesson_validator module exists", (GEN_DIR / "lesson_validator.py").is_file()))
    results.append(_ok("validator_types module exists", (GEN_DIR / "validator_types.py").is_file()))
    results.append(_ok("validator version 5.0.0", VALIDATOR_VERSION == "5.0.0"))

    text = (GEN_DIR / "lesson_validator.py").read_text(encoding="utf-8")
    results.append(_ok("validator does not call repair", "repair_lesson_draft" not in text))
    results.append(_ok("validator accesses blueprint", "WritingLessonBlueprint" in text))

    repair_text = (GEN_DIR / "repair_layer.py").read_text(encoding="utf-8")
    results.append(_ok("repair does not validate", "validate_lesson" not in repair_text))
    return results


def check_repair_ownership() -> list[bool]:
    results: list[bool] = []
    results.append(_ok("repair_layer module exists", (GEN_DIR / "repair_layer.py").is_file()))
    results.append(_ok("repair_types module exists", (GEN_DIR / "repair_types.py").is_file()))
    results.append(_ok("repair layer version 5.0.0", REPAIR_LAYER_VERSION == "5.0.0"))
    results.append(_ok("blueprint-sourced repairs documented", len(BLUEPRINT_SOURCED_REPAIRS) >= 5))
    results.append(_ok("forbidden repair actions documented", len(FORBIDDEN_REPAIR_ACTIONS) >= 5))

    text = (GEN_DIR / "repair_layer.py").read_text(encoding="utf-8")
    results.append(_ok("repair uses mission builder", "build_mission_from_blueprint" in text))
    results.append(_ok("repair doc: no invention", "no educational invention" in text.lower()))
    return results


def check_audit_ownership() -> list[bool]:
    results: list[bool] = []
    results.append(_ok("generation_audit module exists", (GEN_DIR / "generation_audit.py").is_file()))
    results.append(_ok("audit_types module exists", (GEN_DIR / "audit_types.py").is_file()))
    results.append(_ok("generation_hash module exists", (GEN_DIR / "generation_hash.py").is_file()))
    results.append(_ok("audit version 5.0.0", GENERATION_AUDIT_VERSION == "5.0.0"))
    results.append(_ok("GENERATION_ARCHITECTURE doc", (GEN_DIR / "GENERATION_ARCHITECTURE.md").is_file()))
    results.append(_ok("FAILURE_STRATEGY doc", (GEN_DIR / "FAILURE_STRATEGY.md").is_file()))
    results.append(_ok("failure_strategy module", (GEN_DIR / "failure_strategy.py").is_file()))
    results.append(_ok("hard failure triggers documented", len(HARD_FAILURE_TRIGGERS) >= 5))
    results.append(_ok("soft failure triggers documented", len(SOFT_FAILURE_TRIGGERS) >= 5))
    return results


def check_no_duplicated_logic() -> list[bool]:
    results: list[bool] = []
    norm = (GEN_DIR / "response_normalizer.py").read_text(encoding="utf-8")
    val = (GEN_DIR / "lesson_validator.py").read_text(encoding="utf-8")
    rep = (GEN_DIR / "repair_layer.py").read_text(encoding="utf-8")
    pipe = (GEN_DIR / "generation_pipeline.py").read_text(encoding="utf-8")

    results.append(_ok("normalizer sole owner of json parse", "json.loads" in norm and "json.loads" not in val))
    results.append(_ok("validator sole owner of validate_lesson_draft", "def validate_lesson_draft" in val))
    results.append(_ok("repair sole owner of repair_lesson_draft", "def repair_lesson_draft" in rep))
    results.append(_ok("pipeline orchestrates only", "normalize_llm_response" in pipe and "validate_lesson_draft" in pipe))
    results.append(_ok("mission builder not duplicated in normalizer", "build_mission_from_blueprint" not in norm))
    return results


def check_pipeline_integration() -> list[bool]:
    results: list[bool] = []
    bp = _sample_blueprint()
    if not bp:
        results.append(_ok("pipeline sample blueprint", False))
        return results

    prompt = build_prompt_from_blueprint(bp)
    results.append(_ok("prompt bundle built", bool(prompt.to_prompt_dict())))

    # Complete mock response
    raw_complete = WritingLlmRawResponse(raw_text=_mock_llm_json(bp, complete=True), llm_version="mock-5.0.0")
    result = process_llm_generation(bp, prompt, raw_complete, generation_duration_ms=42)
    results.append(_ok("pipeline success on complete mock", result.success))
    results.append(_ok("canonical lesson produced", result.canonical_lesson is not None))
    if result.canonical_lesson:
        results.append(_ok("generation hash present", len(result.canonical_lesson.generation_hash) == 64))
        results.append(_ok("generation hash deterministic", result.canonical_lesson.generation_hash == compute_generation_hash(result.canonical_lesson)))
    results.append(_ok("audit blueprint version", result.audit.blueprint_version == bp.blueprint_version))
    results.append(_ok("audit prompt version", result.audit.prompt_version == PROMPT_BUILDER_VERSION))
    results.append(_ok("audit generator version", result.audit.generator_version == GENERATOR_PIPELINE_VERSION))
    results.append(_ok("audit llm version", result.audit.llm_version == "mock-5.0.0"))
    results.append(_ok("audit duration recorded", result.audit.generation_duration_ms == 42))
    results.append(_ok("audit validation passed", result.audit.validation_passed))

    # Incomplete mock — repair should restore
    raw_incomplete = WritingLlmRawResponse(raw_text=_mock_llm_json(bp, complete=False), llm_version="mock-5.0.0")
    result2 = process_llm_generation(bp, prompt, raw_incomplete, generation_duration_ms=50)
    results.append(_ok("pipeline success after repair", result2.success))
    results.append(_ok("repair applied on incomplete", result2.repair is not None and result2.repair.repaired))
    results.append(_ok("audit repair flag", result2.audit.repair_applied))

    # Malformed JSON — hard failure
    raw_bad = WritingLlmRawResponse(raw_text="not json {{{", llm_version="mock-5.0.0")
    result3 = process_llm_generation(bp, prompt, raw_bad, generation_duration_ms=10)
    results.append(_ok("hard failure on bad json", not result3.success))
    results.append(_ok("no canonical on hard failure", result3.canonical_lesson is None))
    return results


def check_architecture_version() -> list[bool]:
    results: list[bool] = []
    results.append(_ok("W5 architecture version 5.0.0", ARCHITECTURE_VERSION == "5.0.0"))
    results.append(_ok("generation in ownership registry", "language_writing_generation" in PACKAGE_OWNERSHIP))
    results.append(_ok("ownership mentions audit", "audit" in PACKAGE_OWNERSHIP["language_writing_generation"].lower()))
    return results


def check_imports() -> list[bool]:
    results: list[bool] = []
    for mod in (
        "app.services.language_writing_generation.response_normalizer",
        "app.services.language_writing_generation.lesson_validator",
        "app.services.language_writing_generation.repair_layer",
        "app.services.language_writing_generation.generation_audit",
        "app.services.language_writing_generation.generation_pipeline",
    ):
        try:
            importlib.import_module(mod)
            results.append(_ok(f"import {mod.split('.')[-1]}", True))
        except Exception as exc:  # noqa: BLE001
            results.append(_ok(f"import {mod.split('.')[-1]}", False, str(exc)))
    return results


def main() -> int:
    print("Writing W5 Generation Architecture Verification\n")
    sections = [
        ("Normalizer ownership", check_normalizer_ownership),
        ("Validator ownership", check_validator_ownership),
        ("Repair ownership", check_repair_ownership),
        ("Audit ownership", check_audit_ownership),
        ("No duplicated logic", check_no_duplicated_logic),
        ("Pipeline integration", check_pipeline_integration),
        ("Architecture version", check_architecture_version),
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
        print("W5 COMPLETE — Generation architecture ready. No runtime. No LLM. Stop after W5.")
        return 0
    print("W5 FAILED — fix architecture before proceeding.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
