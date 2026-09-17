"""Server-owned contract for rich canonical grammar practice units."""

from __future__ import annotations

from typing import Any

RICH_PRACTICE_TASK_TYPES = (
    "multiple_choice",
    "fill_blank",
    "sentence_builder",
    "transformation",
    "correction",
    "short_answer",
    "open_response",
)

RICH_PRACTICE_DISTINCTIVE_TASK_TYPES = (
    "multiple_choice",
    "sentence_builder",
    "transformation",
    "short_answer",
    "open_response",
)

RICH_PRACTICE_REQUIRED_COUNTS = {
    "multiple_choice": 3,
    "fill_blank": 3,
    "sentence_builder": 2,
    "transformation": 2,
    "correction": 2,
    "short_answer": 1,
    "open_response": 1,
}

RICH_PRACTICE_REQUIRED_TOTAL = sum(RICH_PRACTICE_REQUIRED_COUNTS.values())

BE_PRESENT_RICH_PRACTICE_ITEMS: tuple[dict[str, str], ...] = (
    {"id": "practice_mc_1", "type": "multiple_choice", "round": "اختر الصحيح", "goal": "choose am/is/are for identity"},
    {"id": "practice_mc_2", "type": "multiple_choice", "round": "اختر الصحيح", "goal": "choose the correct negative"},
    {"id": "practice_mc_3", "type": "multiple_choice", "round": "اختر الصحيح", "goal": "choose the correct yes/no question"},
    {"id": "practice_blank_1", "type": "fill_blank", "round": "أكمل الفراغ", "goal": "affirmative is for description"},
    {"id": "practice_blank_2", "type": "fill_blank", "round": "أكمل الفراغ", "goal": "negative are not"},
    {"id": "practice_blank_3", "type": "fill_blank", "round": "أكمل الفراغ", "goal": "question is before subject"},
    {"id": "practice_build_1", "type": "sentence_builder", "round": "ركّب الجملة", "goal": "build an affirmative sentence"},
    {"id": "practice_build_2", "type": "sentence_builder", "round": "ركّب الجملة", "goal": "build a yes/no question"},
    {"id": "practice_transform_1", "type": "transformation", "round": "حوّل الجملة", "goal": "affirmative to negative"},
    {"id": "practice_transform_2", "type": "transformation", "round": "حوّل الجملة", "goal": "statement to yes/no question"},
    {"id": "practice_correct_1", "type": "correction", "round": "صحّح الخطأ", "goal": "missing be"},
    {"id": "practice_correct_2", "type": "correction", "round": "صحّح الخطأ", "goal": "do/does with be or wrong question order"},
    {"id": "practice_short_1", "type": "short_answer", "round": "جاوب واكتب", "goal": "answer a yes/no question with a short answer"},
    {"id": "practice_open_1", "type": "open_response", "round": "جاوب واكتب", "goal": "write 2-4 connected personal sentences"},
)


def rich_practice_items_for_grammar(grammar_id: str) -> tuple[dict[str, str], ...]:
    if grammar_id == "gram_be_present":
        return BE_PRESENT_RICH_PRACTICE_ITEMS
    return ()


def rich_practice_ids_for_grammar(grammar_id: str) -> tuple[str, ...]:
    return tuple(item["id"] for item in rich_practice_items_for_grammar(grammar_id))


def is_rich_practice_payload(payload: dict[str, Any]) -> bool:
    tasks = [
        *[item for item in payload.get("understanding_checks") or [] if isinstance(item, dict)],
        *[item for item in payload.get("guided_practice") or [] if isinstance(item, dict)],
    ]
    return any(str(task.get("type") or "") in RICH_PRACTICE_DISTINCTIVE_TASK_TYPES for task in tasks)
