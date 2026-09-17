"""Deterministic lesson-package payload fill for product display.

Fallback is a temporary safety path only. It must never create fake examples
from grammar display names; use catalog material or clear restart guidance.
"""

from __future__ import annotations

from dataclasses import replace

from app.services.language_grammar_activity_authoring.llm.lesson_schema import (
    ALL_REQUIRED_LESSON_SECTIONS,
    LESSON_PACKAGE_VERSION,
    LESSON_SCHEMA_VERSION,
    METHODOLOGY_VERSION,
    PAYLOAD_LESSON_PACKAGE_VERSION_KEY,
    PAYLOAD_LESSON_SCHEMA_VERSION_KEY,
    PAYLOAD_METHODOLOGY_VERSION_KEY,
)
from app.services.language_grammar_activity_spec import ActivitySpecification, with_fingerprint
from app.services.language_grammar_catalog.catalog import get_topic
from app.services.language_grammar_lesson_planner.types import GrammarLessonBlueprint

_ARABIC_CONCEPTS = {
    "gram_be_present": (
        "\u0628\u0641\u0639\u0644 be \u0623\u0646\u062a \u0644\u0627 \u062a\u062d\u0643\u064a \u0639\u0646 \u062d\u062f\u062b\u060c \u0628\u0644 \u062a\u0631\u0628\u0637 \u0627\u0644\u0634\u062e\u0635 \u0628\u0641\u0643\u0631\u0629: \u0645\u0646 \u0647\u0648\u061f \u0623\u064a\u0646 \u0647\u0648\u061f \u0643\u064a\u0641 \u062d\u0627\u0644\u0647\u061f "
        "\u0628\u0627\u0644\u0639\u0631\u0628\u064a \u0646\u0642\u0648\u0644: \u0647\u064a \u062a\u0639\u0628\u0627\u0646\u0629\u060c \u0628\u062f\u0648\u0646 \u0641\u0639\u0644 \u0638\u0627\u0647\u0631. \u0628\u0627\u0644\u0625\u0646\u062c\u0644\u064a\u0632\u064a\u0629 \u0646\u062d\u062a\u0627\u062c is: She is tired."
    ),
    "gram_present_simple": (
        "\u0646\u0633\u062a\u062e\u062f\u0645 \u0627\u0644\u0645\u0636\u0627\u0631\u0639 \u0627\u0644\u0628\u0633\u064a\u0637 \u0644\u0634\u064a\u0621 \u064a\u062d\u062f\u062b \u0639\u0627\u062f\u0629\u060c \u0623\u0648 \u0644\u062d\u0642\u064a\u0642\u0629\u060c \u0623\u0648 \u0644\u0634\u064a\u0621 \u062b\u0627\u0628\u062a. "
        "\u0627\u0644\u0641\u0643\u0631\u0629 \u0644\u064a\u0633\u062a '\u0627\u0644\u0622\u0646'\u060c \u0628\u0644 '\u0628\u0634\u0643\u0644 \u0639\u0627\u0645': I work, She works."
    ),
    "gram_present_perfect": (
        "\u0627\u0644\u0640 present perfect \u064a\u0631\u0628\u0637 \u0634\u064a\u0626\u0627 \u062d\u0635\u0644 \u0642\u0628\u0644 \u0627\u0644\u0622\u0646 \u0628\u0645\u0639\u0646\u0649 \u0645\u0647\u0645 \u0627\u0644\u0622\u0646: \u062a\u062c\u0631\u0628\u0629\u060c \u0646\u062a\u064a\u062c\u0629\u060c \u0623\u0648 \u0634\u064a\u0621 \u0644\u0645 \u064a\u0643\u062a\u0645\u0644 \u0628\u0639\u062f. "
        "\u0644\u0647\u0630\u0627 \u0644\u0627 \u0646\u0636\u0639 \u0648\u0642\u062a\u0627 \u0645\u0646\u062a\u0647\u064a\u0627 \u0645\u062b\u0644 yesterday \u0645\u0639\u0647."
    ),
    "gram_third_conditional": (
        "\u0627\u0644\u0634\u0631\u0637 \u0627\u0644\u062b\u0627\u0644\u062b \u064a\u062d\u0643\u064a \u0639\u0646 \u0645\u0627\u0636 \u0644\u0645 \u064a\u062d\u062f\u062b\u060c \u0648\u0646\u062a\u064a\u062c\u0629 \u0643\u0627\u0646\u062a \u0633\u062a\u062a\u063a\u064a\u0631. "
        "\u0647\u0648 \u0645\u0641\u064a\u062f \u0644\u0644\u0646\u062f\u0645 \u0623\u0648 \u062a\u062e\u064a\u0644 \u0646\u062a\u064a\u062c\u0629 \u0645\u062e\u062a\u0644\u0641\u0629: If I had known, I would have helped."
    ),
}

RETRY_AUTHORING_STATUS = "retry_required"
RETRY_GENERATION_MODE = "retry_required_no_valid_authoring"
RETRY_MESSAGE_AR = "\u062a\u0639\u0630\u0651\u0631 \u062a\u062c\u0647\u064a\u0632 \u0627\u0644\u062f\u0631\u0633 \u0628\u0627\u0644\u0634\u0643\u0644 \u0627\u0644\u0645\u0637\u0644\u0648\u0628. \u062d\u0627\u0648\u0644 \u0625\u0646\u0634\u0627\u0621 \u0627\u0644\u062f\u0631\u0633 \u0645\u0631\u0629 \u0623\u062e\u0631\u0649."


def specification_has_lesson_package(spec: ActivitySpecification) -> bool:
    payload = dict(spec.payload or {})
    mode = str(payload.get("generation_mode") or "").strip().lower()
    return bool(
        payload.get("student_content")
        and payload.get("server_teaching_metadata")
        and payload.get(PAYLOAD_METHODOLOGY_VERSION_KEY) == METHODOLOGY_VERSION
        and payload.get("authoring_status") != RETRY_AUTHORING_STATUS
        and not mode.startswith(("temporary_", "retry_required", "fallback"))
    )


def _topic_examples(topic: str, display_name: str, raw_examples: tuple[str, ...]) -> list[dict[str, str | None]]:
    examples = [str(item).strip() for item in raw_examples if str(item).strip()]
    if topic == "gram_be_present":
        examples = ["I am a student.", "She is at home.", "They are not ready."]
    elif topic == "gram_present_perfect":
        examples = ["I have already finished the task.", "Have you ever visited Aleppo?", "She hasn't replied yet."]
    elif topic == "gram_third_conditional":
        examples = [
            "If I had known, I would have helped.",
            "She would have arrived earlier if she had left at six.",
            "If they had studied, they would have passed.",
        ]
    elif len(examples) < 3:
        examples.extend(["I am ready.", "She works every day.", "They finished the task."])
    return [
        {
            "id": f"ex_{index}",
            "sentence": sentence,
            "teaching_purpose": purpose,
            "target_form": _target_form_hint(topic, sentence),
            "arabic_meaning": None,
            "arabic_explanation": _example_explanation(topic, display_name),
        }
        for index, (sentence, purpose) in enumerate(
            zip(examples[:3], ("meaning", "form", "contrast"), strict=False),
            start=1,
        )
    ]


def _target_form_hint(topic: str, sentence: str) -> str:
    if topic == "gram_be_present":
        lowered = f" {sentence.lower()} "
        for form in ("am", "is", "are"):
            if f" {form} " in lowered:
                return form
    if topic == "gram_present_perfect":
        return "have/has + past participle"
    if topic == "gram_third_conditional":
        return "if + past perfect, would have + past participle"
    return "target form"


def _example_explanation(topic: str, display_name: str) -> str:
    if topic == "gram_be_present":
        return "\u0647\u0630\u0627 \u0627\u0644\u0645\u062b\u0627\u0644 \u064a\u0633\u062a\u062e\u062f\u0645 am/is/are \u0644\u0631\u0628\u0637 \u0627\u0644\u0634\u062e\u0635 \u0628\u0648\u0635\u0641 \u0623\u0648 \u0645\u0643\u0627\u0646."
    if topic == "gram_present_perfect":
        return "\u0647\u0646\u0627 \u0627\u0644\u0645\u0627\u0636\u064a \u0645\u0647\u0645 \u0644\u0644\u0622\u0646\u060c \u0644\u0630\u0644\u0643 \u0646\u0633\u062a\u062e\u062f\u0645 have/has \u0645\u0639 \u0627\u0644\u062a\u0635\u0631\u064a\u0641 \u0627\u0644\u062b\u0627\u0644\u062b."
    if topic == "gram_third_conditional":
        return "\u0627\u0644\u062c\u0645\u0644\u0629 \u062a\u062a\u062e\u064a\u0644 \u0646\u062a\u064a\u062c\u0629 \u0645\u062e\u062a\u0644\u0641\u0629 \u0644\u0623\u0646 \u0634\u064a\u0626\u0627 \u0641\u064a \u0627\u0644\u0645\u0627\u0636\u064a \u0644\u0645 \u064a\u062d\u062f\u062b."
    return f"\u0647\u0630\u0627 \u0645\u062b\u0627\u0644 \u0645\u0624\u0642\u062a \u064a\u062d\u062a\u0627\u062c \u0625\u0644\u0649 \u062f\u0631\u0633 \u0645\u0648\u0644\u062f \u0645\u0646 Claude \u0644\u062a\u0641\u0635\u064a\u0644 {display_name}."


def _topic_patterns(topic: str, display_name: str, raw_patterns: tuple[str, ...]) -> list[dict[str, str]]:
    if topic == "gram_be_present":
        pairs = [
            ("I + am", "I am ready."),
            ("He/She/It + is", "She is tired."),
            ("You/We/They + are", "They are here."),
        ]
    elif topic == "gram_present_perfect":
        pairs = [
            ("Subject + have/has + past participle", "I have finished."),
            ("Have/Has + subject + ever + past participle?", "Have you ever travelled alone?"),
        ]
    elif topic == "gram_third_conditional":
        pairs = [
            ("If + past perfect, would have + past participle", "If I had studied, I would have passed."),
            ("Would have + past participle + if + past perfect", "She would have called if she had known."),
        ]
    else:
        pairs = [(pattern, "Regenerate this lesson for a full topic example.") for pattern in raw_patterns[:3]]
        if not pairs:
            pairs = [(display_name, "Regenerate this lesson for a full topic example.")]
    return [
        {
            "id": f"pat_{index}",
            "pattern": pattern,
            "meaning": "target form",
            "explanation": "\u0627\u0631\u0628\u0637 \u0627\u0644\u0634\u0643\u0644 \u0628\u0627\u0644\u0645\u0639\u0646\u0649 \u0642\u0628\u0644 \u0627\u0644\u062d\u0641\u0638.",
            "example": example,
        }
        for index, (pattern, example) in enumerate(pairs[:4], start=1)
    ]


def _topic_mistakes(topic: str, raw_errors: tuple[str, ...]) -> list[dict[str, str]]:
    if topic == "gram_be_present":
        pairs = [("He are tired.", "He is tired."), ("She my friend.", "She is my friend.")]
    elif topic == "gram_present_perfect":
        pairs = [("I have finished yesterday.", "I finished yesterday."), ("Did you ever visited Aleppo?", "Have you ever visited Aleppo?")]
    elif topic == "gram_third_conditional":
        pairs = [
            ("If I knew, I would have helped.", "If I had known, I would have helped."),
            ("If she had left, she will arrive.", "If she had left, she would have arrived."),
        ]
    else:
        pairs = [(err, "Regenerate this lesson for the corrected form.") for err in raw_errors[:2]]
    if len(pairs) < 2:
        pairs.append(("Regeneration needed.", "Start a fresh lesson."))
    return [
        {
            "id": f"mistake_{index}",
            "incorrect": incorrect,
            "correct": correct,
            "why": "\u0627\u0644\u062e\u0637\u0623 \u064a\u0623\u062a\u064a \u0645\u0646 \u0646\u0642\u0644 \u062a\u0641\u0643\u064a\u0631 \u0627\u0644\u0639\u0631\u0628\u064a \u0645\u0628\u0627\u0634\u0631\u0629 \u0623\u0648 \u0645\u0646 \u062a\u0637\u0628\u064a\u0642 \u0627\u0644\u0642\u0627\u0639\u062f\u0629 \u0639\u0644\u0649 \u0627\u0644\u0634\u062e\u0635 \u0627\u0644\u062e\u0637\u0623.",
            "misunderstanding": "\u062a\u0637\u0628\u064a\u0642 \u0627\u0644\u0645\u0639\u0646\u0649 \u0627\u0644\u0639\u0631\u0628\u064a \u0628\u0646\u0641\u0633 \u062a\u0631\u062a\u064a\u0628 \u0627\u0644\u0625\u0646\u062c\u0644\u064a\u0632\u064a.",
        }
        for index, (incorrect, correct) in enumerate(pairs[:2], start=1)
    ]


def ensure_lesson_package_on_specification(
    specification: ActivitySpecification,
    *,
    blueprint: GrammarLessonBlueprint | None,
    grammar_target: str,
) -> ActivitySpecification:
    if specification_has_lesson_package(specification):
        return specification

    topic = grammar_target or specification.grammar_topic or "grammar"
    catalog_topic = get_topic(topic)
    display_name = catalog_topic.display_name if catalog_topic is not None else topic.replace("gram_", "").replace("_", " ").title()
    payload = dict(specification.payload)
    payload.update(
        {
            "authoring_status": RETRY_AUTHORING_STATUS,
            "retry_message": RETRY_MESSAGE_AR,
            "teacher_opening": "",
            "lesson_goal": "",
            "warmup": "",
            "main_activity": "",
            "follow_up_questions": "[]",
            "grammar_focus": topic,
            "expected_patterns": "[]",
            "common_mistakes": "[]",
            "teacher_hints": "[]",
            "encouragement_messages": "[]",
            "completion_message": "",
            "alternative_examples": "[]",
            "extra_scaffolding": "[]",
            "adaptive_followups": "[]",
            "difficulty_adjustments": "",
            "review_focus": display_name,
            "encouragement": "",
            PAYLOAD_LESSON_SCHEMA_VERSION_KEY: str(LESSON_SCHEMA_VERSION),
            PAYLOAD_LESSON_PACKAGE_VERSION_KEY: LESSON_PACKAGE_VERSION,
            PAYLOAD_METHODOLOGY_VERSION_KEY: METHODOLOGY_VERSION,
            "lesson_id": specification.lesson_id,
            "grammar_id": topic,
            "display_name": display_name,
            "cefr_level": payload.get("student_cefr") or "",
            "generation_mode": RETRY_GENERATION_MODE,
        }
    )
    for key in ALL_REQUIRED_LESSON_SECTIONS:
        payload.setdefault(key, "")
    updated = replace(specification, payload=payload)
    return with_fingerprint(updated)
