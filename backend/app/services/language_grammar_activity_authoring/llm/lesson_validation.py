"""Validation for canonical Claude grammar lesson authoring."""

from __future__ import annotations

import json
import re
from typing import Any

from app.services.language_grammar_activity_authoring.adaptive import StudentLearningSnapshot
from app.services.language_grammar_activity_authoring.llm.errors import LLMSchemaError
from app.services.language_grammar_activity_authoring.llm.lesson_schema import (
    LESSON_SCHEMA_VERSION,
    CanonicalLessonPackage,
    GrammarLessonPackage,
    METHODOLOGY_SECTIONS,
    normalize_canonical_lesson_output,
)
from app.services.language_grammar_practice_contract import (
    RICH_PRACTICE_DISTINCTIVE_TASK_TYPES,
    RICH_PRACTICE_REQUIRED_COUNTS,
    RICH_PRACTICE_REQUIRED_TOTAL,
    RICH_PRACTICE_TASK_TYPES,
)
from app.services.language_grammar_catalog.catalog import list_topics

_EXTRA_UNSUPPORTED_PHRASES: dict[str, tuple[str, ...]] = {
    "gram_past_perfect": ("past perfect", "had done", "had been"),
    "gram_conditionals": ("second conditional", "third conditional", "if i had"),
    "gram_passive_voice": ("passive voice", "was written by", "were made by"),
    "gram_future_perfect": ("future perfect", "will have"),
    "gram_reported_speech": ("reported speech", "he said that he had"),
}

_ANSWER_REVEAL_MARKERS = (
    "the answer is",
    "correct answer:",
    "write exactly:",
    "full answer:",
)

_ALLOWED_TARGET_ALIASES: dict[str, tuple[str, ...]] = {
    "gram_first_conditional": ("gram_conditionals",),
    "gram_second_conditional": ("gram_conditionals",),
    "gram_third_conditional": ("gram_conditionals",),
    "gram_mixed_conditionals_light": ("gram_conditionals",),
    "gram_zero_conditional": ("gram_conditionals",),
    "gram_past_perfect_light": ("gram_past_perfect",),
}

_SERVER_ONLY_KEYS = frozenset(
    {
        "expected_answer",
        "sample_answer",
        "success_criteria",
        "misconception",
        "misconception_classification",
        "feedback_reasoning",
        "hint",
        "similar_retry_prompt",
        "validation_metadata",
        "remediation_routes",
        "server_teaching_metadata",
    }
)

_ARABIC_RE = re.compile(r"[\u0600-\u06ff]")

_GENERIC_FILLER_PATTERNS = (
    re.compile(r"\bthis grammar is useful in communication\b", re.IGNORECASE),
    re.compile(r"\buse this grammar for communication\b", re.IGNORECASE),
    re.compile(r"\bthis pattern is used in sentences\b", re.IGNORECASE),
    re.compile(r"\byou will learn\b.+\bgram_", re.IGNORECASE),
)


def _display_name_for_targets(allowed_targets: tuple[str, ...] | frozenset[str]) -> str:
    primary = next(iter(allowed_targets), "")
    for topic in list_topics():
        if topic.grammar_id == primary:
            return topic.display_name
    return str(primary or "").replace("gram_", "").replace("_", " ").title()


def _arabic_char_count(text: str) -> int:
    return len(_ARABIC_RE.findall(text or ""))


def _text_blob(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _contains_generic_filler(text: str, *, display_name: str) -> bool:
    blob = (text or "").strip()
    if any(pattern.search(blob) for pattern in _GENERIC_FILLER_PATTERNS):
        return True
    escaped = re.escape(display_name.strip())
    if escaped:
        fake_example_patterns = (
            rf"\bi\s+use\s+{escaped}\b",
            rf"\bwe\s+use\s+{escaped}\b",
            rf"\bthey\s+practice\s+{escaped}\b",
            rf"\buse this pattern for\s+{escaped}\b",
            rf"\bthis sentence shows\s+{escaped}\b",
            rf"\bexample with\s+{escaped}\b",
        )
        if any(re.search(pattern, blob, flags=re.IGNORECASE) for pattern in fake_example_patterns):
            return True
    return False


def _topic_markers(grammar_id: str, display_name: str) -> tuple[str, ...]:
    markers = [grammar_id.lower()]
    name = (display_name or "").strip().lower()
    if name:
        markers.append(name)
    markers.extend(_EXTRA_UNSUPPORTED_PHRASES.get(grammar_id, ()))
    return tuple(dict.fromkeys(markers))


def detect_unsupported_grammar(
    text: str,
    *,
    allowed_targets: tuple[str, ...] | frozenset[str],
) -> tuple[str, ...]:
    """Return grammar_ids mentioned in text that are not in allowed targets."""
    expanded_allowed: set[str] = set(allowed_targets)
    for target in tuple(expanded_allowed):
        expanded_allowed.update(_ALLOWED_TARGET_ALIASES.get(target, ()))
    allowed = frozenset(expanded_allowed)
    blob = (text or "").lower()
    if not blob.strip():
        return ()

    found: list[str] = []
    for topic in list_topics():
        gid = topic.grammar_id
        if gid in allowed:
            continue
        for marker in _topic_markers(gid, topic.display_name):
            if " " in marker or marker.startswith("gram_"):
                if marker in blob:
                    found.append(gid)
                    break
            elif re.search(rf"\b{re.escape(marker)}\b", blob):
                found.append(gid)
                break

    for gid, phrases in _EXTRA_UNSUPPORTED_PHRASES.items():
        if gid in allowed or gid in found:
            continue
        if any(p in blob for p in phrases):
            found.append(gid)
    return tuple(sorted(set(found)))


def _raise(code: str, message: str) -> None:
    raise LLMSchemaError(code, message)


def _ensure_len(name: str, value: list[Any], min_count: int, max_count: int) -> None:
    if not isinstance(value, list):
        _raise("invalid_item_limit", f"{name} must be an array")
    count = len(value)
    if count < min_count or count > max_count:
        _raise("invalid_item_limit", f"{name} requires {min_count}-{max_count} items; got {count}")


def _sentence_count(text: str) -> int:
    fragments = re.split(r"[.!?]+", text or "")
    return len([p for p in fragments if p.strip(" \t\r\n'\"`.,;:!?")])


def _walk_student_keys(value: Any, *, path: str = "student_content") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if key in _SERVER_ONLY_KEYS:
                _raise("server_metadata_exposed", f"Student content contains server-only key: {path}.{key}")
            _walk_student_keys(child, path=f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _walk_student_keys(child, path=f"{path}[{index}]")


def _validate_task(task: dict[str, Any], *, path: str) -> None:
    task_id = str(task.get("id") or "").strip()
    task_type = str(task.get("type") or "").strip()
    prompt = str(task.get("prompt") or "").strip()
    if not task_id:
        _raise("missing_task_id", f"{path}.id required")
    if task_type not in {
        "choice",
        "fill_blank",
        "reorder",
        "correction",
        "production",
        "transfer",
        *RICH_PRACTICE_TASK_TYPES,
    }:
        _raise("invalid_task_type", f"{path}.type unsupported: {task_type}")
    if not prompt:
        _raise("missing_task_prompt", f"{path}.prompt required")
    if task_type in {"choice", "multiple_choice"}:
        options = task.get("options")
        if not isinstance(options, list) or not (2 <= len(options) <= 4):
            _raise("invalid_choice_payload", f"{path}.options requires 2-4 options")
        if any(not isinstance(option, str) or not option.strip() for option in options):
            _raise("invalid_choice_payload", f"{path}.options must contain strings")
    elif task_type == "fill_blank":
        sentence = str(task.get("sentence_with_blank") or "")
        if "_____" not in sentence:
            _raise("invalid_fill_blank_payload", f"{path}.sentence_with_blank must include _____")
    elif task_type == "reorder":
        tokens = task.get("reorder_tokens")
        if not isinstance(tokens, list) or len(tokens) < 2:
            _raise("invalid_reorder_payload", f"{path}.reorder_tokens requires at least 2 tokens")
    elif task_type == "sentence_builder":
        tokens = task.get("word_chips") or task.get("reorder_tokens")
        if not isinstance(tokens, list) or len(tokens) < 3:
            _raise("invalid_sentence_builder_payload", f"{path}.word_chips requires at least 3 tokens")
    elif task_type == "correction":
        if not str(task.get("incorrect_sentence") or "").strip():
            _raise("invalid_correction_payload", f"{path}.incorrect_sentence required")
    elif task_type == "transformation":
        if not str(task.get("original_sentence") or "").strip():
            _raise("invalid_transformation_payload", f"{path}.original_sentence required")
        if not str(task.get("transformation_goal") or "").strip():
            _raise("invalid_transformation_payload", f"{path}.transformation_goal required")
    elif task_type == "short_answer":
        if not str(task.get("context") or "").strip():
            _raise("invalid_short_answer_payload", f"{path}.context required")
    elif task_type == "open_response":
        minimum = int(task.get("sentence_count_min") or 0)
        maximum = int(task.get("sentence_count_max") or 0)
        if minimum < 1 or maximum < minimum:
            _raise("invalid_open_response_payload", f"{path}.sentence_count_min/max required")
    elif task_type == "production":
        # prompt is enough; scaffold is optional.
        return
    elif task_type == "transfer":
        if not str(task.get("context") or "").strip():
            _raise("invalid_transfer_payload", f"{path}.context required")


def _collect_student_item_ids(student: dict[str, Any]) -> tuple[str, ...]:
    ids: list[str] = []

    def add(raw_id: Any, path: str) -> None:
        item_id = str(raw_id or "").strip()
        if not item_id:
            _raise("missing_student_item_id", f"{path}.id required")
        ids.append(item_id)

    add((student.get("noticing") or {}).get("id"), "noticing")
    for section in ("understanding_checks", "guided_practice", "supported_production"):
        for index, item in enumerate(student.get(section) or []):
            add(item.get("id"), f"{section}[{index}]")
    add((student.get("transfer") or {}).get("id"), "transfer")
    exit_check = student.get("exit_check") or {}
    for key in ("recognition", "correction", "production"):
        add((exit_check.get(key) or {}).get("id"), f"exit_check.{key}")

    duplicates = sorted({item_id for item_id in ids if ids.count(item_id) > 1})
    if duplicates:
        _raise("duplicate_student_item_ids", "Duplicate student item ids: " + ", ".join(duplicates))
    return tuple(ids)


def _metadata_records(metadata: dict[str, Any]) -> tuple[dict[str, Any], ...]:
    records: list[dict[str, Any]] = []
    for section in (
        "noticing",
        "understanding_checks",
        "guided_practice",
        "supported_production",
        "transfer",
        "exit_check",
    ):
        raw = metadata.get(section)
        if raw in (None, ""):
            continue
        if isinstance(raw, dict):
            records.append(raw)
        elif isinstance(raw, list):
            records.extend(item for item in raw if isinstance(item, dict))
        else:
            _raise("invalid_metadata_shape", f"{section} metadata must be object or array")
    return tuple(records)


def _validate_metadata_links(student: dict[str, Any], metadata: dict[str, Any]) -> None:
    student_ids = _collect_student_item_ids(student)
    records = _metadata_records(metadata)
    metadata_ids = [str(record.get("item_id") or record.get("id") or "").strip() for record in records]
    if any(not item_id for item_id in metadata_ids):
        _raise("missing_metadata_item_id", "Every server metadata record requires item_id")
    duplicates = sorted({item_id for item_id in metadata_ids if metadata_ids.count(item_id) > 1})
    if duplicates:
        _raise("duplicate_metadata_item_ids", "Duplicate metadata item ids: " + ", ".join(duplicates))

    student_set = set(student_ids)
    metadata_set = set(metadata_ids)
    missing = sorted(student_set - metadata_set)
    unknown = sorted(metadata_set - student_set)
    if unknown:
        _raise("unknown_metadata_item_id", "Metadata references unknown item ids: " + ", ".join(unknown))
    if missing:
        _raise("missing_server_metadata", "Missing metadata for student item ids: " + ", ".join(missing))

    for record in records:
        if not (record.get("expected_answer") or record.get("sample_answer") or record.get("success_criteria")):
            _raise(
                "incomplete_server_metadata",
                f"Metadata for {record.get('item_id')} needs expected_answer, sample_answer, or success_criteria",
            )


def _validate_arabic_first_teaching_model(
    student: dict[str, Any],
    *,
    cefr_level: str,
    allowed_targets: tuple[str, ...],
) -> None:
    cefr = cefr_level.upper()
    display_name = _display_name_for_targets(allowed_targets)
    blob = _text_blob(student)
    if _contains_generic_filler(blob, display_name=display_name):
        _raise("generic_filler_detected", "Lesson contains generic filler or grammar-name fake examples")

    explanation = student.get("concept_explanation")
    if isinstance(explanation, dict):
        arabic_intro = str(explanation.get("arabic_concept_intro") or explanation.get("arabic_concept_introduction") or "").strip()
    elif isinstance(explanation, list):
        arabic_intro = "\n".join(str(item or "") for item in explanation if _ARABIC_RE.search(str(item or "")))
    else:
        arabic_intro = str(explanation or "").strip()
    arabic_clarification = student.get("arabic_clarification") if isinstance(student.get("arabic_clarification"), dict) else {}
    arabic_support = " ".join(
        str(arabic_clarification.get(key) or "")
        for key in ("arabic", "arabic_speaker_warning", "arabic_english_contrast")
    )
    arabic_teaching = f"{arabic_intro} {arabic_support}".strip()
    if cefr in {"A1", "A2"} and _arabic_char_count(arabic_teaching) < 120:
        _raise("arabic_concept_too_short", "A1-A2 lessons require a detailed Arabic concept explanation")
    if cefr in {"A1", "A2", "B1"} and arabic_teaching and not _ARABIC_RE.search(arabic_teaching):
        _raise("invalid_bilingual_content", "Arabic teaching content must use natural Arabic")

    for index, item in enumerate(student.get("model_examples") or []):
        sentence = str(item.get("sentence") or "").strip()
        target_form = str(item.get("target_form") or "").strip()
        arabic_explanation = str(item.get("arabic_explanation") or "").strip()
        if not sentence or _contains_generic_filler(sentence, display_name=display_name):
            _raise("fake_model_example", f"model_examples[{index}] must be a real English sentence")
        if display_name.lower() in sentence.lower() and len(sentence.split()) <= len(display_name.split()) + 4:
            _raise("fake_model_example", f"model_examples[{index}] explains the grammar name instead of using it")
        if not target_form:
            _raise("missing_example_target_form", f"model_examples[{index}].target_form required")
        if not arabic_explanation or not _ARABIC_RE.search(arabic_explanation):
            _raise("missing_example_explanation", f"model_examples[{index}].arabic_explanation required")

    form = student.get("form_and_rules") if isinstance(student.get("form_and_rules"), dict) else {}
    for index, pattern in enumerate(form.get("patterns") or []):
        explanation_text = str(pattern.get("explanation") or pattern.get("meaning") or "").strip()
        example = str(pattern.get("example") or "").strip()
        if not explanation_text:
            _raise("formula_without_explanation", f"form_and_rules.patterns[{index}] needs learner explanation")
        if not example:
            _raise("rule_without_example", f"form_and_rules.patterns[{index}] needs an immediate example")
    use_cases = form.get("use_cases") or []
    if not isinstance(use_cases, list) or not use_cases:
        _raise("missing_use_cases", "form_and_rules.use_cases required")
    for index, use_case in enumerate(use_cases):
        if not all(str(use_case.get(key) or "").strip() for key in ("label", "explanation", "example", "arabic_explanation")):
            _raise("invalid_use_case", f"form_and_rules.use_cases[{index}] needs label, explanation, example, and Arabic explanation")
        if not _ARABIC_RE.search(str(use_case.get("arabic_explanation") or "")):
            _raise("invalid_use_case", f"form_and_rules.use_cases[{index}] Arabic explanation required")
    visual_summary = form.get("visual_summary") or []
    if not isinstance(visual_summary, list) or not visual_summary:
        _raise("missing_visual_summary", "form_and_rules.visual_summary required")
    if any(not str(item.get("label") or "").strip() or not str(item.get("value") or "").strip() for item in visual_summary):
        _raise("invalid_visual_summary", "Every visual summary item needs label and value")

    contrast = str(arabic_clarification.get("arabic_english_contrast") or "").strip()
    misconceptions = " ".join(str(x or "") for x in (arabic_clarification.get("arabic_speaker_warning"), contrast))
    if cefr in {"A1", "A2", "B1"} and not _ARABIC_RE.search(misconceptions):
        _raise("missing_arabic_english_contrast", "A1-B1 lessons require an Arabic-English contrast or warning")

    for index, item in enumerate(student.get("contrasts_and_mistakes") or []):
        why = str(item.get("why") or "").strip()
        misunderstanding = str(item.get("misunderstanding") or "").strip()
        if not why:
            _raise("missing_mistake_reason", f"contrasts_and_mistakes[{index}].why required")
        if cefr in {"A1", "A2", "B1"} and not _ARABIC_RE.search(why):
            _raise("missing_mistake_reason", f"contrasts_and_mistakes[{index}].why must explain in Arabic")
        if not misunderstanding:
            _raise("missing_misunderstanding", f"contrasts_and_mistakes[{index}].misunderstanding required")


def _validate_practice_progression(student: dict[str, Any]) -> None:
    practice_items = [
        *[item for item in (student.get("understanding_checks") or []) if isinstance(item, dict)],
        *[item for item in (student.get("guided_practice") or []) if isinstance(item, dict)],
    ]
    practice_types = [str(item.get("type") or "") for item in practice_items]
    if any(task_type in RICH_PRACTICE_DISTINCTIVE_TASK_TYPES for task_type in practice_types):
        if len(practice_items) != RICH_PRACTICE_REQUIRED_TOTAL:
            _raise("invalid_practice_progression", f"Rich practice requires {RICH_PRACTICE_REQUIRED_TOTAL} tasks")
        for task_type, count in RICH_PRACTICE_REQUIRED_COUNTS.items():
            if practice_types.count(task_type) != count:
                _raise("invalid_practice_progression", f"Rich practice requires {count} {task_type} tasks")
        return
    guided_types = [str(item.get("type") or "") for item in (student.get("guided_practice") or [])]
    if any(task_type in {"production", "transfer"} for task_type in guided_types):
        _raise("invalid_practice_progression", "guided_practice must stay controlled before production")
    required_controlled = {"choice", "fill_blank", "correction"}
    if not required_controlled.issubset(set(guided_types + [str(item.get("type") or "") for item in (student.get("understanding_checks") or [])])):
        _raise("invalid_practice_progression", "Practice must include choice, fill_blank, and correction before production")
    if any(str(item.get("type") or "") != "production" for item in (student.get("supported_production") or [])):
        _raise("invalid_practice_progression", "supported_production must contain production tasks")
    if str((student.get("transfer") or {}).get("type") or "") != "transfer":
        _raise("invalid_practice_progression", "transfer must be a transfer task")


def _validate_section_limits(
    student: dict[str, Any],
    *,
    cefr_level: str,
    max_contrasts_and_mistakes: int | None = None,
) -> None:
    orientation = student.get("orientation") or {}
    orientation_text = " ".join(str(v) for v in orientation.values() if isinstance(v, str))
    if _sentence_count(orientation_text) > 2:
        _raise("invalid_item_limit", "orientation maximum is 2 short sentences")

    if not isinstance(student.get("meaning_hook"), dict):
        _raise("missing_section", "meaning_hook object required")
    _ensure_len("model_examples", student.get("model_examples") or [], 3, 5)

    noticing = student.get("noticing") or {}
    observations = noticing.get("expected_observations") or []
    if not isinstance(observations, list) or not (1 <= len(observations) <= 3):
        _raise("invalid_item_limit", "noticing.expected_observations requires 1-3 items")

    explanation = student.get("concept_explanation")
    if isinstance(explanation, list) and len(explanation) > 2:
        _raise("invalid_item_limit", "concept_explanation maximum is 2 short paragraphs")

    form = student.get("form_and_rules") or {}
    _ensure_len("form_and_rules.patterns", form.get("patterns") or [], 1, 4)
    if len(form.get("rule_notes") or []) > 5:
        _raise("invalid_item_limit", "form_and_rules.rule_notes maximum is 5")

    arabic = student.get("arabic_clarification")
    if not isinstance(arabic, dict) or "arabic" not in arabic or "arabic_speaker_warning" not in arabic:
        _raise("missing_section", "arabic_clarification requires arabic and arabic_speaker_warning keys")
    arabic_text = " ".join(str(v) for v in arabic.values() if isinstance(v, str) and v.strip())
    if cefr_level.upper() in {"A1", "A2"} and not arabic_text:
        _raise("missing_arabic_clarification", "A1-A2 lessons require Arabic clarification")
    if arabic_text and not _ARABIC_RE.search(arabic_text):
        _raise("invalid_bilingual_content", "Arabic clarification must use Arabic when present")

    mistake_max = max(4, int(max_contrasts_and_mistakes or 4))
    _ensure_len("contrasts_and_mistakes", student.get("contrasts_and_mistakes") or [], 2, mistake_max)
    _ensure_len("understanding_checks", student.get("understanding_checks") or [], 2, 3)
    guided_max = 12 if len(student.get("guided_practice") or []) > 6 else 6
    _ensure_len("guided_practice", student.get("guided_practice") or [], 4, guided_max)
    _ensure_len("supported_production", student.get("supported_production") or [], 1, 2)
    if not isinstance(student.get("transfer"), dict):
        _raise("missing_section", "transfer object required")
    if not isinstance(student.get("exit_check"), dict):
        _raise("missing_section", "exit_check object required")


def _validate_tasks(student: dict[str, Any]) -> None:
    noticing = student.get("noticing") or {}
    if not str(noticing.get("id") or "").strip():
        _raise("missing_task_id", "noticing.id required")
    if not str(noticing.get("prompt") or "").strip():
        _raise("missing_task_prompt", "noticing.prompt required")
    # Noticing uses prompt + observations, not a regular task type.
    for section in ("understanding_checks", "guided_practice", "supported_production"):
        for index, item in enumerate(student.get(section) or []):
            _validate_task(item, path=f"{section}[{index}]")
    _validate_task(student.get("transfer") or {}, path="transfer")
    exit_check = student.get("exit_check") or {}
    for key in ("recognition", "correction", "production"):
        if key not in exit_check:
            _raise("missing_exit_item", f"exit_check.{key} required")
        _validate_task(exit_check.get(key) or {}, path=f"exit_check.{key}")


def validate_canonical_lesson_output(
    raw: dict[str, Any],
    *,
    allowed_targets: tuple[str, ...],
    support_targets: tuple[str, ...] = (),
    cefr_level: str,
    raw_output: str = "",
    max_contrasts_and_mistakes: int | None = None,
) -> CanonicalLessonPackage:
    """Validate and normalize Claude's final production lesson contract."""
    if not isinstance(raw.get("student_content"), dict):
        _raise("missing_student_content", "Claude output must include student_content object")
    if not isinstance(raw.get("server_teaching_metadata"), dict):
        _raise("missing_server_teaching_metadata", "Claude output must include server_teaching_metadata object")

    forbidden_top_level = {
        "lesson_schema_version",
        "lesson_id",
        "grammar_id",
        "display_name",
        "cefr_level",
        "methodology_version",
    }
    leaked = sorted(k for k in forbidden_top_level if k in raw)
    if leaked:
        _raise("server_owned_identity_returned", "Claude must not return server-owned fields: " + ", ".join(leaked))

    if raw_output and len(raw_output) > 20000:
        _raise("output_too_long", "Claude output exceeds the 5,000-token hard maximum approximation")

    missing = [section for section in METHODOLOGY_SECTIONS if section not in raw["student_content"]]
    if missing:
        _raise("missing_methodology_sections", "Missing methodology sections: " + ", ".join(missing))

    _walk_student_keys(raw["student_content"])
    _validate_section_limits(
        raw["student_content"],
        cefr_level=cefr_level,
        max_contrasts_and_mistakes=max_contrasts_and_mistakes,
    )
    _validate_arabic_first_teaching_model(
        raw["student_content"],
        cefr_level=cefr_level,
        allowed_targets=allowed_targets,
    )
    _validate_practice_progression(raw["student_content"])
    _validate_tasks(raw["student_content"])

    canonical = normalize_canonical_lesson_output(raw)
    _validate_metadata_links(canonical.student_content, canonical.server_teaching_metadata)

    unsupported = detect_unsupported_grammar(
        json.dumps(canonical.student_content, ensure_ascii=True, sort_keys=True),
        allowed_targets=tuple(dict.fromkeys([*allowed_targets, *support_targets])),
    )
    if unsupported:
        _raise(
            "unsupported_grammar_detected",
            "Lesson introduces grammar outside provided targets: " + ", ".join(unsupported),
        )
    return canonical


def validate_student_content_integrity(
    student_content: dict[str, Any],
    *,
    allowed_targets: tuple[str, ...],
    support_targets: tuple[str, ...] = (),
    cefr_level: str,
    max_contrasts_and_mistakes: int | None = None,
) -> None:
    """Validate server-projected lesson content before it can be reused or shown."""
    if not isinstance(student_content, dict):
        _raise("missing_student_content", "Projected lesson must include student_content object")
    missing = [section for section in METHODOLOGY_SECTIONS if section not in student_content]
    if missing:
        _raise("missing_methodology_sections", "Missing methodology sections: " + ", ".join(missing))

    _walk_student_keys(student_content)
    _validate_section_limits(
        student_content,
        cefr_level=cefr_level,
        max_contrasts_and_mistakes=max_contrasts_and_mistakes,
    )
    _validate_arabic_first_teaching_model(
        student_content,
        cefr_level=cefr_level,
        allowed_targets=allowed_targets,
    )
    _validate_practice_progression(student_content)
    _validate_tasks(student_content)

    unsupported = detect_unsupported_grammar(
        json.dumps(student_content, ensure_ascii=True, sort_keys=True),
        allowed_targets=tuple(dict.fromkeys([*allowed_targets, *support_targets])),
    )
    if unsupported:
        _raise(
            "unsupported_grammar_detected",
            "Lesson introduces grammar outside provided targets: " + ", ".join(unsupported),
        )


def validate_lesson_package_shape(package: GrammarLessonPackage) -> None:
    """Backward-compatible validation for projected lesson packages."""
    if package.lesson_schema_version < 1:
        _raise("invalid_lesson_schema_version", "lesson_schema_version >= 1 required")
    if package.lesson_schema_version > LESSON_SCHEMA_VERSION:
        _raise("unsupported_lesson_schema_version", f"Unsupported lesson_schema_version: {package.lesson_schema_version}")
    for name in ("teacher_opening", "lesson_goal", "warmup", "main_activity", "grammar_focus"):
        if not getattr(package, name).strip():
            _raise("missing_lesson_section", f"Lesson section empty: {name}")
    if not package.expected_patterns:
        _raise("invalid_expected_patterns", "expected_patterns must be non-empty")
    if not package.common_mistakes:
        _raise("invalid_common_mistakes", "common_mistakes must be non-empty")
    for hint in (*package.teacher_hints, *package.extra_scaffolding):
        lowered = hint.lower()
        for banned in _ANSWER_REVEAL_MARKERS:
            if banned in lowered:
                _raise("hint_reveals_answer", f"Hints/scaffolding must not reveal full answers ({banned!r})")


def validate_grammar_fidelity(
    package: GrammarLessonPackage,
    *,
    allowed_targets: tuple[str, ...],
) -> None:
    if not allowed_targets:
        _raise("missing_grammar_targets", "Grammar Targets required")
    unsupported = detect_unsupported_grammar(package.section_text_blob(), allowed_targets=allowed_targets)
    if unsupported:
        _raise(
            "unsupported_grammar_detected",
            "Lesson introduces grammar outside provided targets: " + ", ".join(unsupported),
        )


def validate_adaptive_personalization(
    package: GrammarLessonPackage,
    *,
    snapshot: StudentLearningSnapshot,
    allowed_targets: tuple[str, ...],
) -> None:
    """Compatibility guard; canonical lessons carry personalization inside sections."""
    if not snapshot.has_weakness_signal():
        return
    personalization = package.personalization_text_blob().lower()
    if not personalization.strip():
        _raise("missing_personalization", "Adaptive personalization sections required")
    unsupported = detect_unsupported_grammar(personalization, allowed_targets=allowed_targets)
    if unsupported:
        _raise(
            "unsupported_grammar_detected",
            "Personalization introduces grammar outside targets: " + ", ".join(unsupported),
        )
