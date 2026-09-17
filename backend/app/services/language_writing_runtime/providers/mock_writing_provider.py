"""Mock WritingModelProvider (W6) — deterministic JSON for verification without API calls."""

from __future__ import annotations

import json
import time

from app.services.language_writing_generation.mission_builder import build_mission_from_blueprint
from app.services.language_writing_generation.prompt_builder_types import PromptSectionKey
from app.services.language_writing_lesson_planner.types import WritingLessonBlueprint
from app.services.language_writing_runtime.model_provider import WritingModelProvider
from app.services.language_writing_runtime.provider_types import (
    ModelCapabilityFlags,
    WritingModelGenerateRequest,
    WritingModelGenerateResponse,
)

# Blueprint hash is embedded in prompt bundle — mock uses mission builder shape only.
# Runtime passes blueprint separately; mock reconstructs from prompt sections where possible.


class MockWritingModelProvider(WritingModelProvider):
    """Returns mission-shaped JSON — used by verification and offline dev."""

    def __init__(self, *, model_name: str = "mock-writing-v6") -> None:
        self._model_name = model_name

    @property
    def provider_name(self) -> str:
        return "mock"

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def temperature(self) -> float:
        return 0.0

    @property
    def max_tokens(self) -> int:
        return 2048

    @property
    def capabilities(self) -> ModelCapabilityFlags:
        return ModelCapabilityFlags(
            supports_json_mode=True,
            supports_streaming=False,
            supports_vision=False,
            supports_local_inference=True,
            provider_family="mock",
        )

    async def generate(self, request: WritingModelGenerateRequest) -> WritingModelGenerateResponse:
        started = time.perf_counter()
        bundle = request.prompt_bundle
        mission_block = bundle.section(PromptSectionKey.mission)
        grammar = bundle.section(PromptSectionKey.grammar)
        vocabulary = bundle.section(PromptSectionKey.vocabulary)
        output_format = bundle.section(PromptSectionKey.output_format)
        constraints_block = bundle.section(PromptSectionKey.constraints)
        criteria_block = bundle.section(PromptSectionKey.success_criteria)

        payload = {
            "mission_title": f"Writing Mission ({bundle.blueprint_id})",
            "writing_context": mission_block.split("\n")[0].replace("Situation: ", ""),
            "instructions": [
                f"Complete the writing task described in the mission.",
                grammar.split("\n")[0] if grammar else "",
                vocabulary.split("\n")[0] if vocabulary else "",
            ],
            "writing_prompt": mission_block,
            "constraints": [line.strip() for line in constraints_block.split("\n") if line.strip()],
            "checklist": [
                line.strip("- ").strip()
                for line in criteria_block.split("\n")
                if line.strip().startswith("-")
            ],
            "tips": ["Review the success criteria before submitting."],
            "learning_outcomes": [
                line.strip("- ").strip()
                for line in criteria_block.split("Required outcomes:")[-1].split("\n")
                if line.strip().startswith("-")
            ][:3],
            "success_criteria": [
                line.strip("- ").strip()
                for line in criteria_block.split("Checklist:")[-1].split("\n")
                if line.strip().startswith("-")
            ],
            "expected_output": output_format.replace("Expected output: ", ""),
            "grammar_display": grammar.replace("Primary focus: ", "").split("\n")[0],
            "vocabulary_display": vocabulary.replace("Primary lemmas: ", "").split("\n")[0],
        }
        raw_text = json.dumps(payload, ensure_ascii=False)
        duration_ms = int((time.perf_counter() - started) * 1000)
        return WritingModelGenerateResponse(
            raw_text=raw_text,
            provider_name=self.provider_name,
            model_name=self._model_name,
            llm_version=f"{self.provider_name}:{self._model_name}",
            duration_ms=duration_ms,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )


def mock_response_from_blueprint(blueprint: WritingLessonBlueprint) -> str:
    """Build deterministic mock JSON from blueprint via mission builder — for tests."""
    mission = build_mission_from_blueprint(blueprint)
    return json.dumps(
        {
            "mission_title": mission.mission_title,
            "writing_context": mission.mission_context,
            "instructions": list(mission.instructions),
            "writing_prompt": mission.writing_prompt,
            "constraints": list(mission.constraints),
            "checklist": list(mission.checklist),
            "tips": list(mission.tips),
            "learning_outcomes": list(mission.learning_outcomes),
            "success_criteria": list(mission.success_criteria),
            "expected_output": mission.expected_output,
            "grammar_display": blueprint.grammar_targets.primary.replace("_", " "),
            "vocabulary_display": ", ".join(blueprint.vocabulary_targets.primary[:4]),
        },
        ensure_ascii=False,
    )
