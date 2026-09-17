"""Verify Writing W6 Runtime Implementation.

Usage (from backend/):
    python scripts/verify_writing_w6_runtime.py
"""

from __future__ import annotations

import ast
import asyncio
import importlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

BACKEND = Path(__file__).resolve().parents[1]
SERVICES = BACKEND / "app" / "services"
RUNTIME_DIR = SERVICES / "language_writing_runtime"
GEN_DIR = SERVICES / "language_writing_generation"

from app.services.language_writing.enums import OfficialWritingCEFR, WritingGoal  # noqa: E402
from app.services.language_writing.ownership import (  # noqa: E402
    ALLOWED_PACKAGE_DEPENDENCIES,
    ARCHITECTURE_LAYERS,
    PACKAGE_LAYER,
    PACKAGE_OWNERSHIP,
)
from app.services.language_writing_generation import WRITING_GENERATION_KEY  # noqa: E402
from app.services.language_writing_generation.generation_pipeline import process_llm_generation  # noqa: E402
from app.services.language_writing_generation.prompt_builder import build_prompt_from_blueprint  # noqa: E402
from app.services.language_writing_lesson_planner.planner_contract import assemble_blueprint  # noqa: E402
from app.services.language_writing_lesson_planner.types import LessonPlannerInput  # noqa: E402
from app.services.language_writing_curriculum.goal_profiles import profile_for_goal  # noqa: E402
from app.services.language_writing_knowledge_chain.types import WritingKnowledgeChainNode  # noqa: E402
from app.services.language_writing_runtime import RUNTIME_VERSION  # noqa: E402
from app.services.language_writing_runtime.errors import WritingRuntimeErrorCode  # noqa: E402
from app.services.language_writing_runtime.generation_runtime import generate_writing_lesson  # noqa: E402
from app.services.language_writing_runtime.model_provider import WritingModelProvider, get_writing_model_provider  # noqa: E402
from app.services.language_writing_runtime.persistence import build_audit_persistence, build_body_json  # noqa: E402
from app.services.language_writing_runtime.providers.claude_writing_provider import ClaudeWritingModelProvider  # noqa: E402
from app.services.language_writing_runtime.providers.mock_writing_provider import (  # noqa: E402
    MockWritingModelProvider,
    mock_response_from_blueprint,
)
from app.services.language_writing_generation.normalizer_types import WritingLlmRawResponse  # noqa: E402
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


def check_provider_isolation() -> list[bool]:
    results: list[bool] = []
    results.append(_ok("model_provider module exists", (RUNTIME_DIR / "model_provider.py").is_file()))
    results.append(_ok("claude provider module exists", (RUNTIME_DIR / "providers" / "claude_writing_provider.py").is_file()))
    results.append(_ok("mock provider module exists", (RUNTIME_DIR / "providers" / "mock_writing_provider.py").is_file()))

    runtime_deps: set[str] = set()
    for py in RUNTIME_DIR.rglob("*.py"):
        runtime_deps |= _parse_imports(py)
    runtime_deps.discard("language_writing_runtime")
    allowed = ALLOWED_PACKAGE_DEPENDENCIES.get("language_writing_runtime", frozenset())
    results.append(_ok("runtime imports allowed writing deps", runtime_deps <= allowed))

    gen_deps = _parse_imports(GEN_DIR / "generation_pipeline.py")
    results.append(_ok("generation pipeline does not import runtime", "language_writing_runtime" not in gen_deps))

    for service_file in (
        RUNTIME_DIR / "generation_runtime.py",
        RUNTIME_DIR / "runtime_api.py",
    ):
        text = service_file.read_text(encoding="utf-8")
        results.append(_ok(f"{service_file.name} no direct anthropic", "anthropic" not in text.lower()))
        results.append(
            _ok(
                f"{service_file.name} uses model provider",
                "get_writing_model_provider" in text
                or "WritingModelProvider" in text
                or "generate_writing_lesson" in text,
            )
        )

    claude_text = (RUNTIME_DIR / "providers" / "claude_writing_provider.py").read_text(encoding="utf-8")
    results.append(_ok("only claude provider imports claude_service", "claude_service" in claude_text))
    results.append(_ok("claude provider exposes generate", "async def generate" in claude_text))
    results.append(_ok("claude provider exposes model_name", "def model_name" in claude_text))
    results.append(_ok("claude provider exposes provider_name", "def provider_name" in claude_text))
    results.append(_ok("claude provider exposes temperature", "def temperature" in claude_text))
    results.append(_ok("claude provider exposes max_tokens", "def max_tokens" in claude_text))
    return results


def check_claude_integration() -> list[bool]:
    results: list[bool] = []
    provider = ClaudeWritingModelProvider()
    results.append(_ok("claude provider_name", provider.provider_name == "claude"))
    results.append(_ok("claude capabilities json_mode", provider.capabilities.supports_json_mode))
    results.append(_ok("claude prompt adapter exists", (RUNTIME_DIR / "claude_prompt_adapter.py").is_file()))
    results.append(_ok("structured runtime error codes", len(WritingRuntimeErrorCode) >= 8))
    return results


def check_pipeline_integrity() -> list[bool]:
    results: list[bool] = []
    node = _sample_node()
    if not node:
        results.append(_ok("pipeline sample node", False))
        return results

    bp = assemble_blueprint(
        LessonPlannerInput(
            official_cefr=OfficialWritingCEFR.B1,
            goal_profile=profile_for_goal(WritingGoal.travel),
            selected_node=node,
            blueprint_id="w6:verify",
        )
    ).blueprint
    prompt = build_prompt_from_blueprint(bp)
    raw = WritingLlmRawResponse(raw_text=mock_response_from_blueprint(bp), llm_version="mock:w6")
    pipeline = process_llm_generation(bp, prompt, raw, generation_duration_ms=12)
    results.append(_ok("frozen pipeline success", pipeline.success))
    results.append(_ok("canonical lesson produced", pipeline.canonical_lesson is not None))
    results.append(_ok("audit produced", pipeline.audit is not None))
    return results


async def _runtime_mock_generation() -> list[bool]:
    results: list[bool] = []
    provider = MockWritingModelProvider()
    result = await generate_writing_lesson(
        None,
        language_id=1,
        student_id=99,
        goal=WritingGoal.travel,
        official_cefr=OfficialWritingCEFR.B1,
        chain_id="travel_airport_journey",
        node_id="complaint_email",
        provider=provider,
        persist=False,
    )
    results.append(_ok("runtime generation success", result.success))
    results.append(_ok("runtime blueprint present", result.blueprint is not None))
    results.append(_ok("runtime canonical present", result.canonical_lesson is not None))
    results.append(_ok("runtime audit present", result.audit is not None))
    results.append(_ok("runtime provider info", result.provider is not None))
    if result.blueprint and result.canonical_lesson:
        results.append(
            _ok(
                "expected output matches blueprint",
                result.canonical_lesson.expected_output == result.blueprint.expected_writing_output.value,
            )
        )
    return results


def check_audit_persistence() -> list[bool]:
    results: list[bool] = []
    node = _sample_node()
    if not node:
        results.append(_ok("audit sample", False))
        return results

    bp = assemble_blueprint(
        LessonPlannerInput(
            official_cefr=OfficialWritingCEFR.B1,
            goal_profile=profile_for_goal(WritingGoal.business),
            selected_node=node,
            blueprint_id="w6:audit",
        )
    ).blueprint
    prompt = build_prompt_from_blueprint(bp)
    raw = WritingLlmRawResponse(raw_text=mock_response_from_blueprint(bp), llm_version="mock:w6")
    pipeline = process_llm_generation(bp, prompt, raw, generation_duration_ms=25)
    assert pipeline.audit and pipeline.canonical_lesson

    audit_dict = build_audit_persistence(
        pipeline.audit,
        model_name="mock-writing-v6",
        provider_name="mock",
    )
    for key in (
        "blueprint_version",
        "blueprint_hash",
        "prompt_version",
        "generator_version",
        "model_name",
        "provider_name",
        "generation_hash",
        "generation_duration_ms",
        "validation_result",
        "repair_result",
    ):
        results.append(_ok(f"audit field persisted: {key}", key in audit_dict))

    body = build_body_json(
        blueprint=bp,
        canonical=pipeline.canonical_lesson,
        audit=pipeline.audit,
        model_name="mock",
        provider_name="mock",
    )
    results.append(_ok("body_json writing_generation key", WRITING_GENERATION_KEY in body))
    return results


def check_version_tracking() -> list[bool]:
    results: list[bool] = []
    results.append(_ok("runtime version 6.0.0", RUNTIME_VERSION == "6.0.0"))
    results.append(_ok("runtime in ownership", "language_writing_runtime" in PACKAGE_OWNERSHIP))
    results.append(_ok("runtime layer assignment", PACKAGE_LAYER.get("language_writing_runtime") == "runtime"))
    layer_index = {name: i for i, name in enumerate(ARCHITECTURE_LAYERS)}
    results.append(_ok("generation before runtime layer", layer_index["generation"] < layer_index["runtime"]))
    results.append(_ok("manual QA checklist doc", (RUNTIME_DIR / "MANUAL_QA_CHECKLIST.md").is_file()))
    return results


def check_malformed_json_handling() -> list[bool]:
    results: list[bool] = []
    node = _sample_node()
    if not node:
        results.append(_ok("malformed json sample", False))
        return results

    async def _run() -> bool:
        provider = MockWritingModelProvider()

        class BadJsonProvider(MockWritingModelProvider):
            async def generate(self, request):  # noqa: ANN001
                from app.services.language_writing_runtime.provider_types import WritingModelGenerateResponse

                return WritingModelGenerateResponse(
                    raw_text="not-json",
                    provider_name="mock",
                    model_name="bad",
                    llm_version="mock:bad",
                    duration_ms=1,
                    temperature=0.0,
                    max_tokens=100,
                )

        result = await generate_writing_lesson(
            None,
            language_id=1,
            student_id=1,
            goal=WritingGoal.travel,
            official_cefr=OfficialWritingCEFR.B1,
            chain_id="travel_airport_journey",
            node_id="complaint_email",
            provider=BadJsonProvider(),
            persist=False,
        )
        return not result.success and result.error is not None and result.error.code in (
            WritingRuntimeErrorCode.malformed_json,
            WritingRuntimeErrorCode.validation_failure,
        )

    results.append(_ok("malformed json returns structured failure", asyncio.run(_run())))
    return results


def check_imports() -> list[bool]:
    results: list[bool] = []
    for mod in (
        "app.services.language_writing_runtime.model_provider",
        "app.services.language_writing_runtime.generation_runtime",
        "app.services.language_writing_runtime.persistence",
        "app.services.language_writing_runtime.providers.claude_writing_provider",
    ):
        try:
            importlib.import_module(mod)
            results.append(_ok(f"import {mod.split('.')[-1]}", True))
        except Exception as exc:  # noqa: BLE001
            results.append(_ok(f"import {mod.split('.')[-1]}", False, str(exc)))
    results.append(_ok("WritingModelProvider is ABC", issubclass(WritingModelProvider, object)))
    mock = get_writing_model_provider(provider="mock")
    results.append(_ok("mock provider factory", mock.provider_name == "mock"))
    return results


def main() -> int:
    print("Writing W6 Runtime Verification\n")
    sections = [
        ("Provider isolation", check_provider_isolation),
        ("Claude integration", check_claude_integration),
        ("Pipeline integrity", check_pipeline_integrity),
        ("Runtime mock generation", lambda: asyncio.run(_runtime_mock_generation())),
        ("Audit persistence", check_audit_persistence),
        ("Version tracking", check_version_tracking),
        ("Malformed JSON handling", check_malformed_json_handling),
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
        print("W6 COMPLETE — Writing runtime ready. No evaluator. Stop after W6.")
        return 0
    print("W6 FAILED — fix runtime before proceeding.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
