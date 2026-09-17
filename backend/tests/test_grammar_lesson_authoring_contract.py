"""Focused tests for the canonical Claude grammar lesson authoring contract."""

from __future__ import annotations

import json
import sys
import types
from dataclasses import replace

import pytest

from app.services.language_grammar_activity_authoring import (
    AuthoringContext,
    AuthoringRequest,
    AuthoringVersionBundle,
    LessonContext,
    StudentProfile,
    TeacherPersona,
)
from app.services.language_grammar_activity_authoring.llm.errors import LLMInvalidJSONError, LLMSchemaError
from app.services.language_grammar_activity_authoring.llm.parser import (
    extract_json_object,
    parse_activity_specification_json,
)
from app.services.language_grammar_activity_authoring.llm.prompt_builder import build_prompt_bundle
from app.services.language_grammar_activity_authoring.llm.retry import should_retry
from app.services.language_grammar_activity_authoring.llm.types import RetryPolicy
from app.services.language_grammar_activity_authoring.llm.lesson_validation import (
    detect_unsupported_grammar,
    validate_canonical_lesson_output,
)
from app.services.language_grammar_activity_spec import ActivitySpecification, ActivityType, LocalizedText
from app.schemas.language_grammar_student import GrammarLessonOut
from app.services.language_grammar_pipeline.generate import lesson_dict_from_generation
from app.services.language_grammar_pipeline.lesson_package_fallback import (
    ensure_lesson_package_on_specification,
)
from app.services.language_grammar_pipeline.stages import _grammar_authoring_profile
from app.services.language_grammar_pipeline.types import (
    PipelineObservability,
    PipelineOutcome,
    PipelineStatus,
    WriteGate,
)


def _request(
    *,
    cefr: str = "A2",
    grammar_target: str = "gram_present_simple",
    extras: dict[str, str] | None = None,
) -> AuthoringRequest:
    ctx = AuthoringContext(
        grammar_targets=(grammar_target,),
        student_cefr=cefr,
        learning_objective="Practice present simple for daily routines.",
        teacher_persona=TeacherPersona(),
        student_profile=StudentProfile(student_id=1, language_id=1, overall_cefr=cefr, locale="en"),
        lesson_context=LessonContext(lesson_id="lesson_1", step_id="practice"),
        activity_type="voice_recording",
        localization="en",
        extras=extras or {},
        versions=AuthoringVersionBundle(
            catalog_version="1.0.0",
            grammar_schema_version=1,
            blueprint_version="1.0.0",
            activity_schema_version=1,
            planner_version="1.0.0",
        ),
    )
    return AuthoringRequest(context=ctx, request_id="req_1")


def _metadata(item_id: str, answer: str = "ok") -> dict:
    return {
        "item_id": item_id,
        "expected_answer": answer,
        "feedback_reasoning": "Use the present simple form for the subject.",
        "hint": "Look at the subject.",
        "similar_retry_prompt": "Try a similar daily routine sentence.",
    }


_ARABIC_INTRO = (
    "\u0627\u0644\u0645\u0636\u0627\u0631\u0639 \u0627\u0644\u0628\u0633\u064a\u0637 \u0644\u064a\u0633 \u0644\u0644\u062d\u062f\u062b \u0627\u0644\u0630\u064a \u064a\u062d\u0635\u0644 \u0627\u0644\u0622\u0646\u060c \u0628\u0644 \u0644\u0644\u0639\u0627\u062f\u0629 \u0623\u0648 \u0627\u0644\u062d\u0642\u064a\u0642\u0629 \u0623\u0648 \u0627\u0644\u0634\u064a\u0621 \u0627\u0644\u0630\u064a \u064a\u062a\u0643\u0631\u0631. "
    "\u0628\u0627\u0644\u0639\u0631\u0628\u064a \u0642\u062f \u0644\u0627 \u064a\u062a\u063a\u064a\u0631 \u0627\u0644\u0641\u0639\u0644 \u0643\u062b\u064a\u0631\u0627\u060c \u0644\u0643\u0646 \u0628\u0627\u0644\u0625\u0646\u062c\u0644\u064a\u0632\u064a\u0629 \u0646\u0646\u062a\u0628\u0647 \u0644\u0644\u0634\u062e\u0635: She works \u0648\u0644\u064a\u0633 She work."
)


def _valid_lesson(*, arabic: object = _ARABIC_INTRO) -> dict:
    student = {
        "orientation": {"teacher_script": "Today we will use present simple for routines."},
        "meaning_hook": {
            "situation": "You tell a friend about your normal day.",
            "why_it_matters": "Present simple helps you describe routines clearly.",
        },
        "model_examples": [
            {
                "id": "ex_1",
                "sentence": "I wake up early.",
                "teaching_purpose": "meaning",
                "target_form": "wake up",
                "arabic_meaning": "\u0623\u0646\u0627 \u0623\u0633\u062a\u064a\u0642\u0638 \u0645\u0628\u0643\u0631\u0627.",
                "arabic_explanation": "\u0627\u0644\u062c\u0645\u0644\u0629 \u062a\u062d\u0643\u064a \u0639\u0646 \u0639\u0627\u062f\u0629\u060c \u0644\u0630\u0644\u0643 \u0646\u0633\u062a\u062e\u062f\u0645 \u0627\u0644\u0641\u0639\u0644 \u0627\u0644\u0623\u0633\u0627\u0633\u064a \u0645\u0639 I.",
            },
            {
                "id": "ex_2",
                "sentence": "She wakes up early.",
                "teaching_purpose": "form",
                "target_form": "wakes",
                "arabic_meaning": "\u0647\u064a \u062a\u0633\u062a\u064a\u0642\u0638 \u0645\u0628\u0643\u0631\u0627.",
                "arabic_explanation": "\u0645\u0639 She \u0646\u0636\u064a\u0641 s \u0644\u0644\u0641\u0639\u0644 \u0644\u0623\u0646\u0647 \u0645\u0636\u0627\u0631\u0639 \u0628\u0633\u064a\u0637.",
            },
            {
                "id": "ex_3",
                "sentence": "They do not work on Fridays.",
                "teaching_purpose": "contrast",
                "target_form": "do not work",
                "arabic_meaning": "\u0647\u0645 \u0644\u0627 \u064a\u0639\u0645\u0644\u0648\u0646 \u064a\u0648\u0645 \u0627\u0644\u062c\u0645\u0639\u0629.",
                "arabic_explanation": "\u0641\u064a \u0627\u0644\u0646\u0641\u064a \u0646\u0633\u062a\u062e\u062f\u0645 do not \u0645\u0639 They \u062b\u0645 \u0627\u0644\u0641\u0639\u0644 \u0627\u0644\u0623\u0633\u0627\u0633\u064a.",
            },
        ],
        "noticing": {
            "id": "notice_1",
            "prompt": "What changes when the subject is she?",
            "expected_observations": ["The verb often adds -s with she/he/it."],
        },
        "concept_explanation": {
            "arabic_concept_introduction": arabic,
            "english_bridge": "Present simple says what is normally true, not what is happening right now.",
            "summary": "Think habit or fact first, then choose the verb form.",
        },
        "form_and_rules": {
            "patterns": [
                {
                    "id": "pat_1",
                    "pattern": "I/You/We/They + base verb",
                    "meaning": "routine",
                    "explanation": "Use the base verb after I, you, we, and they.",
                    "example": "They work every day.",
                },
                {
                    "id": "pat_2",
                    "pattern": "He/She/It + verb-s",
                    "meaning": "routine with third person",
                    "explanation": "Add -s when the subject is he, she, or it.",
                    "example": "She works every day.",
                },
            ],
            "rule_notes": ["Use the base verb after I/you/we/they.", "Add -s with he/she/it."],
            "use_cases": [
                {
                    "id": "use_1",
                    "label": "Habits",
                    "explanation": "Use it for actions that happen regularly.",
                    "example": "I drink tea every morning.",
                    "arabic_explanation": "\u0647\u0646\u0627 \u0646\u062d\u0643\u064a \u0639\u0646 \u0639\u0627\u062f\u0629 \u0645\u062a\u0643\u0631\u0631\u0629\u060c \u0644\u064a\u0633 \u0639\u0646 \u0647\u0630\u0647 \u0627\u0644\u0644\u062d\u0638\u0629.",
                },
                {
                    "id": "use_2",
                    "label": "Facts",
                    "explanation": "Use it for facts that are generally true.",
                    "example": "Water boils at 100 degrees.",
                    "arabic_explanation": "\u0647\u0646\u0627 \u0627\u0644\u0645\u0639\u0646\u0649 \u062d\u0642\u064a\u0642\u0629 \u0639\u0627\u0645\u0629\u060c \u0644\u0630\u0644\u0643 \u0627\u0644\u0645\u0636\u0627\u0631\u0639 \u0627\u0644\u0628\u0633\u064a\u0637 \u0645\u0646\u0627\u0633\u0628.",
                },
            ],
            "visual_summary": [
                {"label": "Meaning", "value": "habit or fact", "warning": None},
                {"label": "I/You/We/They", "value": "base verb", "warning": None},
                {"label": "He/She/It", "value": "verb + s", "warning": "Do not add -s after I."},
            ],
        },
        "arabic_clarification": {
            "arabic": arabic,
            "arabic_speaker_warning": "\u0644\u0627 \u062a\u0636\u0641 s \u0645\u0639 I \u0623\u0648 they.",
            "arabic_english_contrast": "\u0628\u0627\u0644\u0639\u0631\u0628\u064a \u0642\u062f \u0646\u0642\u0648\u0644 \u0623\u0646\u0627 \u0623\u0639\u0645\u0644 \u0648\u0647\u064a \u062a\u0639\u0645\u0644 \u0628\u062a\u063a\u064a\u0631 \u0623\u0642\u0644\u060c \u0644\u0643\u0646 \u0627\u0644\u0625\u0646\u062c\u0644\u064a\u0632\u064a\u0629 \u062a\u0637\u0644\u0628 s \u0645\u0639 She/He/It.",
        },
        "contrasts_and_mistakes": [
            {
                "id": "mistake_1",
                "incorrect": "She wake up early.",
                "correct": "She wakes up early.",
                "why": "\u0627\u0644\u0637\u0627\u0644\u0628 \u0646\u0633\u064a s \u0644\u0623\u0646 \u0627\u0644\u0645\u0639\u0646\u0649 \u0628\u0627\u0644\u0639\u0631\u0628\u064a \u0648\u0627\u0636\u062d \u0628\u062f\u0648\u0646\u0647\u0627\u060c \u0644\u0643\u0646 She \u062a\u062d\u062a\u0627\u062c verb-s.",
                "misunderstanding": "\u0646\u0633\u064a\u0627\u0646 \u062a\u0637\u0627\u0628\u0642 \u0627\u0644\u0641\u0639\u0644 \u0645\u0639 he/she/it.",
            },
            {
                "id": "mistake_2",
                "incorrect": "I wakes up early.",
                "correct": "I wake up early.",
                "why": "\u0627\u0644\u0637\u0627\u0644\u0628 \u0639\u0645\u0645 s \u0639\u0644\u0649 \u0643\u0644 \u0627\u0644\u0623\u0634\u062e\u0627\u0635\u060c \u0644\u0643\u0646 I \u064a\u0623\u062e\u0630 \u0627\u0644\u0641\u0639\u0644 \u0627\u0644\u0623\u0633\u0627\u0633\u064a.",
                "misunderstanding": "\u062a\u0639\u0645\u064a\u0645 \u0642\u0627\u0639\u062f\u0629 s \u0628\u062f\u0648\u0646 \u0645\u0631\u0627\u062c\u0639\u0629 \u0627\u0644\u0634\u062e\u0635.",
            },
        ],
        "understanding_checks": [
            {"id": "check_1", "type": "choice", "prompt": "Choose the correct sentence.", "options": ["She works.", "She work."]},
            {"id": "check_2", "type": "fill_blank", "prompt": "Complete the sentence.", "sentence_with_blank": "He _____ coffee every morning."},
        ],
        "guided_practice": [
            {"id": "practice_1", "type": "choice", "prompt": "Choose the correct sentence.", "options": ["They play.", "They plays."]},
            {"id": "practice_2", "type": "fill_blank", "prompt": "Complete it.", "sentence_with_blank": "She _____ at home."},
            {"id": "practice_3", "type": "correction", "prompt": "Correct it.", "incorrect_sentence": "He go to school."},
            {"id": "practice_4", "type": "reorder", "prompt": "Put in order.", "reorder_tokens": ["She", "works", "today"]},
        ],
        "supported_production": [
            {"id": "produce_1", "type": "production", "prompt": "Write one routine sentence.", "scaffold": "Start with: I usually ..."}
        ],
        "transfer": {
            "id": "transfer_1",
            "type": "transfer",
            "context": "A chat about your weekly routine",
            "prompt": "Write one sentence about something you do every week.",
        },
        "exit_check": {
            "recognition": {"id": "exit_recognition", "type": "choice", "prompt": "Choose the correct sentence.", "options": ["He plays.", "He play."]},
            "correction": {"id": "exit_correction", "type": "correction", "prompt": "Correct it.", "incorrect_sentence": "She work here."},
            "production": {"id": "exit_production", "type": "production", "prompt": "Write one final present simple sentence.", "scaffold": None},
        },
        "reflection": {
            "summary": "You practiced routines with present simple.",
            "encouragement": "Keep checking the subject.",
            "next_step": "Use one routine sentence today.",
        },
    }
    return {
        "student_content": student,
        "server_teaching_metadata": {
            "noticing": [_metadata("notice_1")],
            "understanding_checks": [_metadata("check_1", "She works."), _metadata("check_2", "drinks")],
            "guided_practice": [
                _metadata("practice_1", "They play."),
                _metadata("practice_2", "works"),
                _metadata("practice_3", "He goes to school."),
                _metadata("practice_4", "She works today"),
            ],
            "supported_production": [{"item_id": "produce_1", "sample_answer": "I usually study at night.", "success_criteria": ["Uses present simple."]}],
            "transfer": [{"item_id": "transfer_1", "sample_answer": "I visit my family every week.", "success_criteria": ["Transfers present simple to a weekly routine."]}],
            "exit_check": [
                _metadata("exit_recognition", "He plays."),
                _metadata("exit_correction", "She works here."),
                {"item_id": "exit_production", "sample_answer": "I read every morning.", "success_criteria": ["Uses present simple."]},
            ],
        },
    }


def test_valid_canonical_lesson_parses_to_server_envelope_and_safe_projection():
    spec = parse_activity_specification_json(json.dumps(_valid_lesson()), _request(), provider_id="claude")

    assert spec.grammar_topic == "gram_present_simple"
    assert spec.lesson_id == "lesson_1"
    assert spec.payload["canonical_lesson_schema_version"] == "grammar_lesson_authoring_v2"
    assert "server_teaching_metadata" in spec.payload

    outcome = PipelineOutcome(
        status=PipelineStatus.completed,
        observability=PipelineObservability(pipeline_id="pipe_1"),
        write_gate=WriteGate(),
        grammar_targets=("gram_present_simple",),
        specification=spec,
    )
    lesson = lesson_dict_from_generation(outcome)
    assert lesson["student_content"]["orientation"]["teacher_script"]
    assert "server_teaching_metadata" not in lesson
    lesson_blob = json.dumps(lesson, ensure_ascii=True, sort_keys=True)
    for private in (
        "expected_answer",
        "sample_answer",
        "success_criteria",
        "misconception",
        "feedback_reasoning",
        "hint",
        "similar_retry_prompt",
        "validation_metadata",
    ):
        assert private not in lesson_blob


def test_student_lesson_api_schema_preserves_canonical_content_without_private_metadata():
    spec = parse_activity_specification_json(json.dumps(_valid_lesson()), _request(), provider_id="claude")
    outcome = PipelineOutcome(
        status=PipelineStatus.completed,
        observability=PipelineObservability(pipeline_id="pipe_1"),
        write_gate=WriteGate(),
        grammar_targets=("gram_present_simple",),
        specification=spec,
    )
    lesson = lesson_dict_from_generation(outcome)
    lesson["display_name"] = "Present Simple"
    response = GrammarLessonOut(**lesson).model_dump()

    assert response["display_name"] == "Present Simple"
    assert response["student_content"]["orientation"]["teacher_script"]
    assert "server_teaching_metadata" not in response
    response_blob = json.dumps(response, ensure_ascii=True, sort_keys=True)
    for private in (
        "expected_answer",
        "sample_answer",
        "success_criteria",
        "misconception",
        "feedback_reasoning",
        "hint",
        "similar_retry_prompt",
        "validation_metadata",
    ):
        assert private not in response_blob


def test_legacy_only_specification_returns_retry_state_instead_of_generic_lesson():
    legacy_spec = ActivitySpecification(
        activity_id="legacy_1",
        activity_type=ActivityType.voice_recording.value,
        grammar_topic="gram_be_present",
        grammar_targets=("gram_be_present",),
        lesson_id="lesson_legacy",
        step_id="practice",
        title=LocalizedText({"en": "Speaking: gram_be_present"}),
        goal=LocalizedText({"en": "Practice gram_be_present"}),
        instructions=LocalizedText({"en": "Practice the target."}),
        payload={
            "teacher_opening": "Legacy opening",
            "lesson_goal": "Legacy goal",
            "main_activity": "Legacy activity",
        },
    )
    spec = ensure_lesson_package_on_specification(
        legacy_spec,
        blueprint=None,
        grammar_target="gram_be_present",
    )
    outcome = PipelineOutcome(
        status=PipelineStatus.completed,
        observability=PipelineObservability(pipeline_id="pipe_legacy"),
        write_gate=WriteGate(),
        grammar_targets=("gram_be_present",),
        specification=spec,
    )
    lesson = lesson_dict_from_generation(outcome)

    assert lesson["authoring_status"] == "retry_required"
    assert lesson["generation_mode"] == "retry_required_no_valid_authoring"
    assert lesson["student_content"] == {}
    assert lesson["retry_message"]
    assert lesson["display_name"]
    assert not lesson["display_name"].startswith("gram_")
    assert not lesson["lesson_title"].startswith("Speaking: gram_")


def test_generic_fallback_like_package_is_not_projected_as_valid_lesson():
    spec = parse_activity_specification_json(json.dumps(_valid_lesson()), _request(), provider_id="claude")
    payload = dict(spec.payload)
    student = json.loads(payload["student_content"])
    student["orientation"]["teacher_script"] = "Welcome! Today we focus on Present Simple."
    student["model_examples"][0]["sentence"] = "I use Present Simple in a short sentence."
    payload["student_content"] = json.dumps(student, ensure_ascii=True, sort_keys=True)
    poisoned = replace(spec, payload=payload)
    outcome = PipelineOutcome(
        status=PipelineStatus.completed,
        observability=PipelineObservability(pipeline_id="pipe_poisoned"),
        write_gate=WriteGate(),
        grammar_targets=("gram_present_simple",),
        specification=poisoned,
    )

    lesson = lesson_dict_from_generation(outcome)

    assert lesson["authoring_status"] == "retry_required"
    assert lesson["generation_mode"] == "retry_required_invalid_student_content"
    assert lesson["student_content"] == {}


def test_duplicate_or_unknown_metadata_ids_are_rejected():
    data = _valid_lesson()
    data["server_teaching_metadata"]["guided_practice"][1]["item_id"] = "practice_1"
    with pytest.raises(LLMSchemaError, match="duplicate_metadata_item_ids"):
        parse_activity_specification_json(json.dumps(data), _request(), provider_id="claude")

    data = _valid_lesson()
    data["server_teaching_metadata"]["guided_practice"][1]["item_id"] = "practice_999"
    with pytest.raises(LLMSchemaError, match="unknown_metadata_item_id"):
        parse_activity_specification_json(json.dumps(data), _request(), provider_id="claude")


def test_missing_metadata_is_rejected():
    data = _valid_lesson()
    data["server_teaching_metadata"]["guided_practice"].pop()
    with pytest.raises(LLMSchemaError, match="missing_server_metadata"):
        parse_activity_specification_json(json.dumps(data), _request(), provider_id="claude")


def test_task_payload_validation_rejects_missing_required_fields():
    data = _valid_lesson()
    data["student_content"]["guided_practice"][1]["sentence_with_blank"] = "She works at home."
    with pytest.raises(LLMSchemaError, match="invalid_fill_blank_payload"):
        parse_activity_specification_json(json.dumps(data), _request(), provider_id="claude")

    data = _valid_lesson()
    data["student_content"]["guided_practice"][3]["reorder_tokens"] = ["She"]
    with pytest.raises(LLMSchemaError, match="invalid_reorder_payload"):
        parse_activity_specification_json(json.dumps(data), _request(), provider_id="claude")


def test_student_content_hidden_answers_are_rejected():
    data = _valid_lesson()
    data["student_content"]["guided_practice"][0]["hint"] = "Choose the first option."
    with pytest.raises(LLMSchemaError, match="server_metadata_exposed"):
        parse_activity_specification_json(json.dumps(data), _request(), provider_id="claude")


def test_detailed_arabic_intro_is_required_for_a1_a2():
    data = _valid_lesson(arabic="\u0642\u0635\u064a\u0631.")
    data["student_content"]["arabic_clarification"]["arabic_speaker_warning"] = None
    data["student_content"]["arabic_clarification"]["arabic_english_contrast"] = None
    with pytest.raises(LLMSchemaError, match="arabic_concept_too_short"):
        parse_activity_specification_json(json.dumps(data), _request(), provider_id="claude")


def test_model_examples_need_target_form_and_arabic_explanation():
    data = _valid_lesson()
    data["student_content"]["model_examples"][0]["arabic_explanation"] = ""
    with pytest.raises(LLMSchemaError, match="missing_example_explanation"):
        parse_activity_specification_json(json.dumps(data), _request(), provider_id="claude")

    data = _valid_lesson()
    data["student_content"]["model_examples"][1]["target_form"] = ""
    with pytest.raises(LLMSchemaError, match="missing_example_target_form"):
        parse_activity_specification_json(json.dumps(data), _request(), provider_id="claude")


def test_rule_breakdown_use_cases_and_visual_summary_are_required():
    data = _valid_lesson()
    data["student_content"]["form_and_rules"]["patterns"][0]["example"] = ""
    with pytest.raises(LLMSchemaError, match="rule_without_example"):
        parse_activity_specification_json(json.dumps(data), _request(), provider_id="claude")

    data = _valid_lesson()
    data["student_content"]["form_and_rules"]["use_cases"] = []
    with pytest.raises(LLMSchemaError, match="missing_use_cases"):
        parse_activity_specification_json(json.dumps(data), _request(), provider_id="claude")

    data = _valid_lesson()
    data["student_content"]["form_and_rules"]["visual_summary"] = []
    with pytest.raises(LLMSchemaError, match="missing_visual_summary"):
        parse_activity_specification_json(json.dumps(data), _request(), provider_id="claude")


def test_common_mistakes_require_reason_and_misunderstanding():
    data = _valid_lesson()
    data["student_content"]["contrasts_and_mistakes"][0]["why"] = ""
    with pytest.raises(LLMSchemaError, match="missing_mistake_reason"):
        parse_activity_specification_json(json.dumps(data), _request(), provider_id="claude")

    data = _valid_lesson()
    data["student_content"]["contrasts_and_mistakes"][0]["misunderstanding"] = ""
    with pytest.raises(LLMSchemaError, match="missing_misunderstanding"):
        parse_activity_specification_json(json.dumps(data), _request(), provider_id="claude")


def test_common_mistakes_default_limit_remains_four():
    data = _valid_lesson()
    data["student_content"]["contrasts_and_mistakes"].extend(
        [
            {
                "id": "mistake_3",
                "incorrect": "They works here.",
                "correct": "They work here.",
                "why": "\u0645\u0639 They \u0646\u0633\u062a\u062e\u062f\u0645 \u0627\u0644\u0641\u0639\u0644 \u0627\u0644\u0623\u0633\u0627\u0633\u064a \u0628\u062f\u0648\u0646 s.",
                "misunderstanding": "\u062a\u0639\u0645\u064a\u0645 s \u0639\u0644\u0649 \u0643\u0644 \u0627\u0644\u0636\u0645\u0627\u0626\u0631.",
            },
            {
                "id": "mistake_4",
                "incorrect": "He play football.",
                "correct": "He plays football.",
                "why": "\u0645\u0639 He \u0646\u0636\u064a\u0641 s \u0644\u0644\u0641\u0639\u0644 \u0641\u064a \u0627\u0644\u0645\u0636\u0627\u0631\u0639 \u0627\u0644\u0628\u0633\u064a\u0637.",
                "misunderstanding": "\u0646\u0633\u064a\u0627\u0646 \u062a\u0637\u0627\u0628\u0642 he/she/it.",
            },
            {
                "id": "mistake_5",
                "incorrect": "I does not work.",
                "correct": "I do not work.",
                "why": "\u0645\u0639 I \u0646\u0633\u062a\u062e\u062f\u0645 do not \u0648\u0644\u064a\u0633 does not.",
                "misunderstanding": "\u0627\u0644\u062e\u0644\u0637 \u0628\u064a\u0646 do \u0648 does.",
            },
        ]
    )

    with pytest.raises(LLMSchemaError, match=r"contrasts_and_mistakes requires 2-4 items"):
        validate_canonical_lesson_output(
            data,
            allowed_targets=("gram_present_simple",),
            cefr_level="A2",
        )


def test_server_owned_mistake_limit_allows_expanded_scope_when_provided():
    data = _valid_lesson()
    data["student_content"]["contrasts_and_mistakes"].extend(
        [
            {
                "id": "mistake_3",
                "incorrect": "They works here.",
                "correct": "They work here.",
                "why": "\u0645\u0639 They \u0646\u0633\u062a\u062e\u062f\u0645 \u0627\u0644\u0641\u0639\u0644 \u0627\u0644\u0623\u0633\u0627\u0633\u064a \u0628\u062f\u0648\u0646 s.",
                "misunderstanding": "\u062a\u0639\u0645\u064a\u0645 s \u0639\u0644\u0649 \u0643\u0644 \u0627\u0644\u0636\u0645\u0627\u0626\u0631.",
            },
            {
                "id": "mistake_4",
                "incorrect": "He play football.",
                "correct": "He plays football.",
                "why": "\u0645\u0639 He \u0646\u0636\u064a\u0641 s \u0644\u0644\u0641\u0639\u0644 \u0641\u064a \u0627\u0644\u0645\u0636\u0627\u0631\u0639 \u0627\u0644\u0628\u0633\u064a\u0637.",
                "misunderstanding": "\u0646\u0633\u064a\u0627\u0646 \u062a\u0637\u0627\u0628\u0642 he/she/it.",
            },
            {
                "id": "mistake_5",
                "incorrect": "I does not work.",
                "correct": "I do not work.",
                "why": "\u0645\u0639 I \u0646\u0633\u062a\u062e\u062f\u0645 do not \u0648\u0644\u064a\u0633 does not.",
                "misunderstanding": "\u0627\u0644\u062e\u0644\u0637 \u0628\u064a\u0646 do \u0648 does.",
            },
            {
                "id": "mistake_6",
                "incorrect": "She do not work.",
                "correct": "She does not work.",
                "why": "\u0645\u0639 She \u0646\u0633\u062a\u062e\u062f\u0645 does not \u0648\u0628\u0639\u062f\u0647\u0627 \u0627\u0644\u0641\u0639\u0644 \u0627\u0644\u0623\u0633\u0627\u0633\u064a.",
                "misunderstanding": "\u0646\u0633\u064a\u0627\u0646 does \u0645\u0639 he/she/it.",
            },
        ]
    )

    package = validate_canonical_lesson_output(
        data,
        allowed_targets=("gram_present_simple",),
        cefr_level="A2",
        max_contrasts_and_mistakes=6,
    )

    assert len(package.student_content["contrasts_and_mistakes"]) == 6


def test_generic_filler_and_grammar_name_fake_examples_are_rejected():
    data = _valid_lesson()
    data["student_content"]["concept_explanation"]["summary"] = "This grammar is useful in communication."
    with pytest.raises(LLMSchemaError, match="generic_filler_detected"):
        parse_activity_specification_json(json.dumps(data), _request(), provider_id="claude")

    data = _valid_lesson()
    data["student_content"]["model_examples"][0]["sentence"] = "I use Present simple."
    with pytest.raises(LLMSchemaError, match="generic_filler_detected|fake_model_example"):
        parse_activity_specification_json(json.dumps(data), _request(), provider_id="claude")


def test_practice_must_progress_before_production():
    data = _valid_lesson()
    data["student_content"]["guided_practice"][0]["type"] = "production"
    with pytest.raises(LLMSchemaError, match="invalid_practice_progression"):
        parse_activity_specification_json(json.dumps(data), _request(), provider_id="claude")


def test_b2_arabic_clarification_may_be_null():
    data = _valid_lesson(arabic=None)
    data["student_content"]["arabic_clarification"]["arabic_speaker_warning"] = None
    spec = parse_activity_specification_json(json.dumps(data), _request(cefr="B2"), provider_id="claude")
    student = json.loads(spec.payload["student_content"])
    assert student["arabic_clarification"]["arabic"] is None


def test_orientation_sentence_limit_ignores_trailing_quote_fragment():
    data = _valid_lesson()
    data["student_content"]["orientation"]["teacher_script"] = (
        "Today you learn the target pattern. This helps you say 'what usually happens.'"
    )
    parse_activity_specification_json(json.dumps(data), _request(), provider_id="claude")


def test_topic_mismatch_is_rejected():
    data = _valid_lesson()
    data["student_content"]["concept_explanation"]["summary"] = "This lesson teaches past perfect: had done."
    with pytest.raises(LLMSchemaError, match="unsupported_grammar_detected"):
        parse_activity_specification_json(json.dumps(data), _request(), provider_id="claude")


def test_repository_declared_support_targets_may_be_used_for_contrast():
    data = _valid_lesson()
    data["student_content"]["orientation"]["teacher_script"] = "Today we connect a past action to now."
    data["student_content"]["meaning_hook"]["why_it_matters"] = "Present perfect helps you explain a present result."
    data["student_content"]["concept_explanation"]["english_bridge"] = (
        "Present perfect connects a past action to now; use past simple when a finished time is stated."
    )
    profile = _grammar_authoring_profile(("gram_present_perfect",))
    req = _request(
        cefr="B1",
        grammar_target="gram_present_perfect",
        extras={"grammar_profile_json": json.dumps(profile, ensure_ascii=True, sort_keys=True)},
    )
    spec = parse_activity_specification_json(json.dumps(data), req, provider_id="claude")
    assert spec.grammar_topic == "gram_present_perfect"
    outcome = PipelineOutcome(
        status=PipelineStatus.completed,
        observability=PipelineObservability(pipeline_id="pipe_present_perfect"),
        write_gate=WriteGate(),
        grammar_targets=("gram_present_perfect",),
        specification=spec,
    )
    lesson = lesson_dict_from_generation(outcome)
    assert lesson["authoring_status"] == "ready"
    assert lesson["generation_mode"] == "llm_canonical_grammar_lesson_authoring"


def test_prompt_contract_prevents_b1_failure_shape_from_real_claude():
    req = _request(cefr="B1", grammar_target="gram_present_perfect")
    prompts = build_prompt_bundle(req, provider_id="claude", provider_version="1.0.0")
    prompt_text = f"{prompts.system_prompt}\n{prompts.developer_prompt}"

    assert "For A1-B1, every common mistake why and misunderstanding must include natural Arabic" in prompt_text
    assert "include choice, fill_blank, and at least one correction task before production" in prompt_text
    assert "Make one of the 4 guided_practice items a correction task" in prompt_text


def test_sanitized_present_perfect_failure_shape_is_rejected_with_precise_boundary():
    data = _valid_lesson()
    data["student_content"]["contrasts_and_mistakes"][0]["incorrect"] = "I have finished yesterday."
    data["student_content"]["contrasts_and_mistakes"][0]["correct"] = "I finished yesterday."
    data["student_content"]["contrasts_and_mistakes"][0]["why"] = (
        "Present Perfect cannot be used with a specific finished past time; yesterday requires Past Simple."
    )
    data["student_content"]["guided_practice"] = [
        {
            "id": "practice_1",
            "type": "fill_blank",
            "prompt": "Complete the sentence.",
            "sentence_with_blank": "I _____ finished already.",
        },
        {
            "id": "practice_2",
            "type": "fill_blank",
            "prompt": "Complete the sentence.",
            "sentence_with_blank": "She _____ gone home.",
        },
        {
            "id": "practice_3",
            "type": "reorder",
            "prompt": "Put the words in order.",
            "reorder_tokens": ["she", "has", "not", "replied", "yet"],
        },
        {
            "id": "practice_4",
            "type": "fill_blank",
            "prompt": "Complete the sentence.",
            "sentence_with_blank": "He has lived here _____ 2021.",
        },
    ]

    req = _request(cefr="B1", grammar_target="gram_present_perfect")
    with pytest.raises(LLMSchemaError, match=r"contrasts_and_mistakes\[0\]\.why must explain in Arabic"):
        parse_activity_specification_json(json.dumps(data), req, provider_id="claude")


def test_fidelity_detector_allows_specific_conditional_and_past_perfect_aliases():
    unsupported = detect_unsupported_grammar(
        "The third conditional uses if + past perfect and would have.",
        allowed_targets=("gram_third_conditional", "gram_past_perfect_light"),
    )
    assert unsupported == ()


def test_server_owned_identity_from_claude_is_rejected():
    data = _valid_lesson()
    data["lesson_id"] = "claude_invented"
    with pytest.raises(LLMSchemaError, match="server_owned_identity_returned"):
        parse_activity_specification_json(json.dumps(data), _request(), provider_id="claude")


def test_malformed_json_is_retryable():
    with pytest.raises(LLMInvalidJSONError) as exc:
        extract_json_object("{not json")
    assert should_retry(exc.value, RetryPolicy(max_attempts=2))


def test_default_claude_authoring_generator_uses_contract_token_limit(monkeypatch):
    captured = {}

    def fake_generate_claude_json_sync(*args, **kwargs):
        captured["max_output_tokens"] = kwargs.get("max_output_tokens")
        return "{}"

    fake_claude_service = types.SimpleNamespace(
        is_claude_configured=lambda: True,
        generate_claude_json_sync=fake_generate_claude_json_sync,
    )
    monkeypatch.setitem(sys.modules, "app.services.claude_service", fake_claude_service)

    from app.services.language_grammar_activity_authoring.llm.providers import (
        _default_claude_json_generator,
    )

    assert _default_claude_json_generator("user", "system", 10) == "{}"
    assert captured["max_output_tokens"] == 3500


def test_prompt_package_requires_compact_json_output():
    prompts = build_prompt_bundle(_request(), provider_id="claude")
    joined = "\n".join([prompts.system_prompt, prompts.developer_prompt])
    assert "compact minified JSON" in joined
    assert "Target output: 2,200-3,000 tokens. Hard maximum: 3,500 tokens." in joined
    assert "Output compact JSON" in joined
    assert "Never omit expected_observations" in joined
    assert "Never write placeholder" in joined
    assert "MUST include a valid type field" in joined
    assert "Arabic-first private-teacher behavior" in joined
    assert "visual_summary" in joined
    assert "Bad model sentence" in joined
