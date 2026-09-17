import json

from app.services.language_writing.enums import OfficialWritingCEFR, WritingGoal
from app.services.language_writing_curriculum.goal_profiles import profile_for_goal
from app.services.language_writing_generation.generation_pipeline import process_llm_generation
from app.services.language_writing_generation.normalizer_types import WritingLlmRawResponse
from app.services.language_writing_generation.prompt_builder import build_prompt_from_blueprint
from app.services.language_writing_lesson_planner.planner_contract import assemble_blueprint
from app.services.language_writing_lesson_planner.types import LessonPlannerInput
from app.services.language_writing_topic_universe.registry import get_universe_catalog


def _blueprint():
    chain = get_universe_catalog().chain_by_id("travel_airport_journey")
    node = chain.node_by_id("complaint_email")
    return assemble_blueprint(
        LessonPlannerInput(
            official_cefr=OfficialWritingCEFR.B1,
            goal_profile=profile_for_goal(WritingGoal.travel),
            selected_node=node,
            blueprint_id="test:repair:metadata",
        )
    ).blueprint


def test_repair_restores_mismatched_server_owned_metadata_from_blueprint():
    blueprint = _blueprint()
    raw = WritingLlmRawResponse(
        raw_text=json.dumps(
            {
                "mission_title": "Write a clear travel complaint",
                "writing_context": "B1 travel writing task",
                "instructions": ["Write a short complaint message."],
                "writing_prompt": "Write to the hotel about a room problem.",
                "constraints": [f"Write at least {blueprint.min_words} words.", "B1 level."],
                "learning_outcomes": list(blueprint.learning_outcomes),
                "success_criteria": list(blueprint.success_criteria_labels),
                "expected_output": blueprint.expected_writing_output.value,
                "grammar_display": "unrelated grammar wording",
                "vocabulary_display": "unrelated vocabulary",
            }
        ),
        llm_version="test",
    )

    result = process_llm_generation(
        blueprint,
        build_prompt_from_blueprint(blueprint),
        raw,
        attempt_repair=True,
    )

    assert result.success is True
    assert result.repair is not None
    assert {action.field for action in result.repair.actions} >= {"grammar_display", "vocabulary_display"}
    assert result.canonical_lesson is not None
    assert result.canonical_lesson.grammar_display == blueprint.grammar_targets.primary.replace("_", " ")
    assert result.canonical_lesson.vocabulary_display == ", ".join(blueprint.vocabulary_targets.primary[:6])
