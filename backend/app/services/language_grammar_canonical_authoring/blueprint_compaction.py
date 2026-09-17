"""Compact Claude blueprint plan validation and server-owned normalization."""

from __future__ import annotations

import json
import re
from typing import Any

from app.models.language.grammar_canonical_lesson import GrammarCanonicalLesson
from app.services.language_grammar_activity_authoring.llm.errors import LLMSchemaError
from app.services.language_grammar_canonical_authoring.validation import safe_diagnostics

SERVER_OWNED_BLUEPRINT_KEYS = frozenset(
    {
        "grammar_id",
        "grammar_target",
        "display_name",
        "cefr_level",
        "locale",
        "methodology_version",
        "schema_version",
        "prompt_version",
        "catalog_version",
        "support_grammar_targets",
        "required_forms",
        "stable_ids",
        "unit_keys",
        "revision_id",
        "cross_section_consistency",
    }
)
COMPACT_BLUEPRINT_REQUIRED_KEYS = (
    "core_meaning",
    "english_need",
    "arabic_contrast",
    "form_teaching_notes",
    "use_case_intents",
    "example_intents",
    "practice_plan",
    "production_goal",
    "cefr_language_guidance",
    "single_appearance_topics",
)
_GENERIC_RE = re.compile(
    r"\b(welcome|today you will learn|this grammar is useful|use this grammar for communication)\b",
    re.IGNORECASE,
)
_ARABIC_RE = re.compile(r"[\u0600-\u06ff]")


def deterministic_blueprint_stable_ids() -> dict[str, Any]:
    return {
        "examples": ["ex_1", "ex_2", "ex_3"],
        "noticing": "notice_1",
        "patterns": ["pat_1", "pat_2", "pat_3"],
        "use_cases": ["use_1", "use_2", "use_3"],
        "mistakes": ["mistake_1", "mistake_2", "mistake_3", "mistake_4", "mistake_5", "mistake_6"],
        "understanding_checks": ["check_1", "check_2"],
        "guided_practice": ["practice_1", "practice_2", "practice_3", "practice_4"],
        "supported_production": ["produce_1"],
        "transfer": ["transfer_1"],
        "exit_check": {
            "recognition": "exit_recognition",
            "correction": "exit_correction",
            "production": "exit_production",
        },
    }


def is_compact_blueprint_plan(payload: dict[str, Any]) -> bool:
    return "core_meaning" in payload or "english_need" in payload


def validate_compact_blueprint_plan(
    plan: dict[str, Any],
    *,
    lesson: GrammarCanonicalLesson,
    grammar_profile: dict[str, Any],
) -> dict[str, Any]:
    try:
        _validate_compact_blueprint_plan(plan, lesson=lesson, grammar_profile=grammar_profile)
        return {"status": "valid"}
    except LLMSchemaError as exc:
        return safe_diagnostics(str(getattr(exc, "code", "compact_blueprint_invalid")), str(exc))


def normalize_compact_blueprint_plan(
    plan: dict[str, Any],
    *,
    lesson: GrammarCanonicalLesson,
    grammar_profile: dict[str, Any],
) -> dict[str, Any]:
    _validate_compact_blueprint_plan(plan, lesson=lesson, grammar_profile=grammar_profile)
    forms = _server_required_forms(grammar_profile)
    form_notes = _form_teaching_notes(plan.get("form_teaching_notes"), forms)
    mistake_categories = _server_required_mistake_categories(grammar_profile)
    mistake_notes = _mistake_notes(plan.get("mistake_intents"), mistake_categories)
    return {
        "grammar_target": lesson.grammar_id,
        "display_name": str(grammar_profile.get("display_name") or lesson.grammar_id),
        "cefr_level": lesson.cefr_level,
        "locale": lesson.locale,
        "teaching_language_behavior": str(plan["cefr_language_guidance"]),
        "core_communicative_meaning": str(plan["core_meaning"]),
        "why_english_uses_it": str(plan["english_need"]),
        "required_forms": forms,
        "subject_trigger_relationships": [f"{form}: {note}" for form, note in form_notes.items()],
        "main_use_cases": [str(item.get("label") or item.get("meaning") or "") for item in _dict_list(plan["use_case_intents"])],
        "arabic_english_contrast": str(plan.get("arabic_contrast") or ""),
        "likely_arabic_speaker_mistakes": mistake_categories,
        "support_grammar_targets": _support_targets(grammar_profile),
        "example_intentions": [str(item.get("meaning") or item.get("intent") or "") for item in _dict_list(plan["example_intents"])],
        "mistake_intentions": mistake_categories,
        "mistake_teaching_notes": mistake_notes,
        "practice_progression_plan": [str(item) for item in plan["practice_plan"]],
        "production_goal": str(plan["production_goal"]),
        "terminology_limits": str(plan["cefr_language_guidance"]),
        "stable_ids": deterministic_blueprint_stable_ids(),
        "duplication_avoidance": [str(item) for item in plan["single_appearance_topics"]],
        "content_once": [str(item) for item in plan["single_appearance_topics"]],
        "cross_section_consistency": [
            "Use server-owned stable IDs exactly",
            "All later units must teach the required forms",
            "Do not repeat single-appearance topics across sections",
        ],
        "compact_plan": dict(plan),
    }


def _validate_compact_blueprint_plan(
    plan: dict[str, Any],
    *,
    lesson: GrammarCanonicalLesson,
    grammar_profile: dict[str, Any],
) -> None:
    if not isinstance(plan, dict):
        _raise("invalid_compact_blueprint", "Compact blueprint plan must be an object")
    echoed = sorted(key for key in SERVER_OWNED_BLUEPRINT_KEYS if key in plan)
    if echoed:
        _raise("server_owned_blueprint_field_echoed", "Claude echoed server-owned blueprint fields: " + ", ".join(echoed))
    missing = [key for key in COMPACT_BLUEPRINT_REQUIRED_KEYS if plan.get(key) in (None, "", [], {})]
    if missing:
        _raise("missing_compact_blueprint_fields", "Missing compact blueprint fields: " + ", ".join(missing))
    blob = json.dumps(plan, ensure_ascii=False, sort_keys=True)
    if _GENERIC_RE.search(blob):
        _raise("generic_blueprint_filler", "Compact blueprint contains generic filler")
    if len(blob) > 8000:
        _raise("compact_blueprint_too_large", "Compact blueprint plan is too large")
    for key in ("core_meaning", "english_need", "production_goal", "cefr_language_guidance"):
        _max_words(str(plan.get(key) or ""), 20, key)
    if plan.get("arabic_contrast") is not None:
        _max_words(str(plan.get("arabic_contrast") or ""), 30, "arabic_contrast")
    _validate_form_teaching_notes(plan.get("form_teaching_notes"), _server_required_forms(grammar_profile))
    for key in ("use_case_intents", "example_intents", "single_appearance_topics"):
        values = plan.get(key)
        if not isinstance(values, list) or not values or len(values) > 3:
            _raise("invalid_compact_blueprint_list", f"{key} requires 1-3 items")
    mistakes = plan.get("mistake_intents") or []
    if not isinstance(mistakes, list) or len(mistakes) > 6:
        _raise("invalid_compact_blueprint_list", "mistake_intents requires 1-6 items")
    _validate_mistake_intents(mistakes, _server_required_mistake_categories(grammar_profile))
    if [str(item) for item in plan.get("practice_plan") or []] != ["recognition", "choice", "fill_blank", "reorder", "correction"]:
        _raise("invalid_practice_plan", "Practice plan must be recognition, choice, fill_blank, reorder, correction")
    _reject_duplicate_intentions(plan)
    if lesson.grammar_id == "gram_be_present":
        _validate_be_present_plan(plan, grammar_profile=grammar_profile)


def _validate_be_present_plan(plan: dict[str, Any], *, grammar_profile: dict[str, Any]) -> None:
    blob = json.dumps(plan, ensure_ascii=False, sort_keys=True).lower()
    forms = set(_server_required_forms(grammar_profile))
    required = {
        "affirmative_am",
        "affirmative_is",
        "affirmative_are",
        "negative_am_not",
        "negative_is_not",
        "negative_are_not",
        "question_am",
        "question_is",
        "question_are",
        "short_answer_am",
        "short_answer_is",
        "short_answer_are",
    }
    if not required.issubset(forms):
        missing = ", ".join(sorted(required - forms))
        _raise("missing_be_required_forms", "Server profile missing Present of be form keys: " + missing)
    if "english" not in blob or not any(token in blob for token in ("needs", "requires", "verb")):
        _raise("missing_english_need", "Present of be plan must explain why English requires be")
    if not (_ARABIC_RE.search(str(plan.get("arabic_contrast") or "")) and any(token in blob for token in ("omit", "visible verb", "بدون", "يحذف"))):
        _raise("missing_arabic_contrast", "Present of be plan must mention Arabic visible-verb omission")
    _reject_be_present_forbidden_extensions(blob)
    categories = set(_server_required_mistake_categories(grammar_profile))
    required_mistakes = {
        "be_deletion",
        "wrong_be_agreement",
        "missing_not",
        "statement_order_question",
        "do_does_with_be",
        "incomplete_short_answer",
    }
    if not required_mistakes.issubset(categories):
        missing = ", ".join(sorted(required_mistakes - categories))
        _raise("missing_be_mistake_categories", "Server profile missing Present of be mistake categories: " + missing)


def _reject_be_present_forbidden_extensions(blob: str) -> None:
    checks = (
        ("forbidden_past_be", r"\b(was|were)\b"),
        ("forbidden_future_be", r"\b(will be|going to be)\b"),
        ("forbidden_perfect_be", r"\b(have been|has been|had been)\b"),
        ("forbidden_continuous_be", r"\b(am|is|are)\s+[a-z]+ing\b"),
        ("forbidden_modal_be", r"\b(can|could|should|must|may|might|would)\s+be\b"),
        ("forbidden_tag_question", r"\b(isn't it|aren't you|is she not|are they not)\?\b"),
        ("forbidden_wh_question_scope", r"\b(wh-?question|wh question|where/what/who|what/where/who)\b"),
    )
    for code, pattern in checks:
        if re.search(pattern, blob, re.IGNORECASE):
            _raise(code, "Present of be compact blueprint includes forbidden extension")


def _server_required_forms(grammar_profile: dict[str, Any]) -> list[str]:
    explicit = [str(item) for item in grammar_profile.get("required_form_keys") or [] if str(item).strip()]
    if explicit:
        return explicit
    patterns = [str(item) for item in grammar_profile.get("canonical_patterns") or []]
    blob = " ".join(patterns).lower()
    forms = [form for form in ("am", "is", "are") if re.search(rf"\b{form}\b", blob)]
    if forms:
        return forms
    return patterns[:4] or [str(grammar_profile.get("display_name") or "target form")]


def _support_targets(grammar_profile: dict[str, Any]) -> list[str]:
    return [str(item) for item in grammar_profile.get("support_grammar_targets") or [] if str(item).strip()]


def _server_required_mistake_categories(grammar_profile: dict[str, Any]) -> list[str]:
    categories = [
        str(item).strip()
        for item in grammar_profile.get("mistake_categories") or []
        if str(item).strip()
    ]
    return list(dict.fromkeys(categories))


def _validate_mistake_intents(raw: Any, categories: list[str]) -> None:
    allowed = set(categories)
    seen: set[str] = set()
    for item in _dict_list(raw):
        category = str(
            item.get("error_type")
            or item.get("category")
            or item.get("mistake_category")
            or ""
        ).strip()
        if not category:
            _raise("invalid_mistake_intent", "mistake_intents entries require a server-owned category")
        if allowed and category not in allowed:
            _raise("unknown_mistake_category", f"Unknown mistake category: {category}")
        if category in seen:
            _raise("duplicate_mistake_category", f"Duplicate mistake category: {category}")
        seen.add(category)
        note = str(item.get("misunderstanding") or item.get("note") or "")
        if note:
            _max_words(note, 20, f"mistake_intents.{category}")
            if _GENERIC_RE.search(note):
                _raise("generic_blueprint_filler", f"mistake_intents.{category} contains generic filler")


def _mistake_notes(raw: Any, categories: list[str]) -> dict[str, str]:
    _validate_mistake_intents(raw or [], categories)
    notes: dict[str, str] = {}
    for item in _dict_list(raw or []):
        category = str(
            item.get("error_type")
            or item.get("category")
            or item.get("mistake_category")
            or ""
        ).strip()
        note = str(item.get("misunderstanding") or item.get("note") or "").strip()
        if category and note:
            notes[category] = note
    return notes


def _validate_form_teaching_notes(raw: Any, forms: list[str]) -> None:
    if not isinstance(raw, dict) or not raw:
        _raise("invalid_form_teaching_notes", "form_teaching_notes must be an object keyed by server form keys")
    expected = set(forms)
    actual = {str(key) for key in raw.keys()}
    if actual != expected:
        details = []
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        if missing:
            details.append("missing: " + ", ".join(missing))
        if extra:
            details.append("extra: " + ", ".join(extra))
        _raise("invalid_form_teaching_notes_keys", "form_teaching_notes must match server form keys; " + "; ".join(details))
    for key, value in raw.items():
        note = str(value or "").strip()
        if not note:
            _raise("invalid_form_teaching_notes", f"form_teaching_notes.{key} is empty")
        _max_words(note, 20, f"form_teaching_notes.{key}")
        if _GENERIC_RE.search(note):
            _raise("generic_blueprint_filler", f"form_teaching_notes.{key} contains generic filler")


def _form_teaching_notes(raw: Any, forms: list[str]) -> dict[str, str]:
    _validate_form_teaching_notes(raw, forms)
    return {form: str(raw[form]).strip() for form in forms}


def _reject_duplicate_intentions(plan: dict[str, Any]) -> None:
    seen: list[str] = []
    for key in ("use_case_intents", "example_intents", "mistake_intents", "single_appearance_topics"):
        for item in plan.get(key) or []:
            text = json.dumps(item, ensure_ascii=False, sort_keys=True).strip().lower()
            if text:
                seen.append(text)
    duplicates = sorted({item for item in seen if seen.count(item) > 1})
    if duplicates:
        _raise("duplicate_blueprint_intentions", "Compact blueprint repeats intentions")


def _dict_list(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [dict(item) for item in value if isinstance(item, dict)]


def _max_words(text: str, limit: int, field: str) -> None:
    if len([part for part in text.split() if part.strip()]) > limit:
        _raise("compact_blueprint_field_too_long", f"{field} exceeds {limit} words")


def _raise(code: str, message: str) -> None:
    raise LLMSchemaError(code, message)
