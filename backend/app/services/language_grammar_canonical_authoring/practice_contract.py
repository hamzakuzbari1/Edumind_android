"""Compatibility re-export for the server-owned rich practice contract."""

from app.services.language_grammar_practice_contract import (
    BE_PRESENT_RICH_PRACTICE_ITEMS,
    RICH_PRACTICE_DISTINCTIVE_TASK_TYPES,
    RICH_PRACTICE_REQUIRED_COUNTS,
    RICH_PRACTICE_REQUIRED_TOTAL,
    RICH_PRACTICE_TASK_TYPES,
    is_rich_practice_payload,
    rich_practice_ids_for_grammar,
    rich_practice_items_for_grammar,
)

__all__ = [
    "BE_PRESENT_RICH_PRACTICE_ITEMS",
    "RICH_PRACTICE_DISTINCTIVE_TASK_TYPES",
    "RICH_PRACTICE_REQUIRED_COUNTS",
    "RICH_PRACTICE_REQUIRED_TOTAL",
    "RICH_PRACTICE_TASK_TYPES",
    "is_rich_practice_payload",
    "rich_practice_ids_for_grammar",
    "rich_practice_items_for_grammar",
]
