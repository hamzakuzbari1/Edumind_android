"""Independent validators for sectioned canonical grammar authoring units."""

from __future__ import annotations

import json
import re
import copy
from typing import Any

from app.models.language.grammar_canonical_lesson import GrammarCanonicalLesson
from app.services.language_grammar_activity_authoring.llm.errors import LLMSchemaError
from app.services.language_grammar_canonical_authoring.types import UnitValidationResult
from app.services.language_grammar_canonical_authoring.unit_repository import compute_unit_attempt_hash
from app.services.language_grammar_canonical_authoring.validation import safe_diagnostics
from app.services.language_grammar_pipeline.stages import _grammar_authoring_profile
from app.services.language_grammar_practice_contract import (
    RICH_PRACTICE_REQUIRED_COUNTS,
    RICH_PRACTICE_REQUIRED_TOTAL,
    RICH_PRACTICE_TASK_TYPES,
    is_rich_practice_payload,
    rich_practice_ids_for_grammar,
)

_ARABIC_RE = re.compile(r"[\u0600-\u06ff]")
_GENERIC_PATTERNS = (
    re.compile(r"\bwelcome!\s*today we focus on\b", re.IGNORECASE),
    re.compile(r"\btoday you will learn\b", re.IGNORECASE),
    re.compile(r"\bthis grammar is useful\b", re.IGNORECASE),
    re.compile(r"\buse this pattern for communication\b", re.IGNORECASE),
    re.compile(r"مرحبا[ً،,\s]+اليوم\s+سنتعلم", re.IGNORECASE),
    re.compile(r"في\s+هذا\s+الدرس\s+سوف\s+نتعلم", re.IGNORECASE),
)
_PRIVATE_KEYS = {
    "expected_answer",
    "sample_answer",
    "success_criteria",
    "feedback_reasoning",
    "hint",
    "similar_retry_prompt",
    "misconception",
}
_BE_PRESENT_FORM_PATTERNS: dict[str, tuple[str, ...]] = {
    "affirmative_am": (r"\bi\s+am\b(?!\s+not)",),
    "affirmative_is": (r"\b(he|she|it|this|that|[a-z]+)\s+is\b(?!\s+not|\s*n['’]t)",),
    "affirmative_are": (r"\b(you|we|they|[a-z]+s)\s+are\b(?!\s+not|\s*n['’]t)",),
    "negative_am_not": (r"\bi\s+am\s+not\b", r"\bi['’]m\s+not\b"),
    "negative_is_not": (r"\b(he|she|it|this|that|[a-z]+)\s+is\s+not\b", r"\b(he|she|it|this|that|[a-z]+)\s+isn['’]t\b"),
    "negative_are_not": (r"\b(you|we|they|[a-z]+s)\s+are\s+not\b", r"\b(you|we|they|[a-z]+s)\s+aren['’]t\b"),
    "question_am": (r"\bam\s+i\b",),
    "question_is": (r"\bis\s+(he|she|it|this|that|[a-z]+)\b",),
    "question_are": (r"\bare\s+(you|we|they|[a-z]+s)\b",),
    "short_answer_am": (r"\byes,\s+i\s+am\b", r"\bno,\s+i\s+am\s+not\b", r"\bno,\s+i['’]m\s+not\b"),
    "short_answer_is": (
        r"\byes,\s+(he|she|it|this|that)\s+is\b",
        r"\bno,\s+(he|she|it|this|that)\s+is\s+not\b",
        r"\bno,\s+(he|she|it|this|that)\s+isn['’]t\b",
    ),
    "short_answer_are": (
        r"\byes,\s+(you|we|they)\s+are\b",
        r"\bno,\s+(you|we|they)\s+are\s+not\b",
        r"\bno,\s+(you|we|they)\s+aren['’]t\b",
    ),
}


def validate_blueprint_unit(
    blueprint: dict[str, Any],
    *,
    lesson: GrammarCanonicalLesson,
) -> UnitValidationResult:
    try:
        if str(blueprint.get("grammar_target") or "") != lesson.grammar_id:
            _raise("blueprint_identity_mismatch", "Blueprint grammar target does not match canonical lesson")
        if str(blueprint.get("cefr_level") or "").upper() != lesson.cefr_level:
            _raise("blueprint_identity_mismatch", "Blueprint CEFR does not match canonical lesson")
        if str(blueprint.get("locale") or "") != lesson.locale:
            _raise("blueprint_identity_mismatch", "Blueprint locale does not match canonical lesson")
        required_forms = _as_list(blueprint.get("required_forms"))
        if not required_forms:
            _raise("missing_required_forms", "Blueprint requires required_forms")
        expected_forms = _profile_required_form_keys(lesson)
        if expected_forms:
            missing = sorted(set(expected_forms) - set(required_forms))
            extra = sorted(set(required_forms) - set(expected_forms))
            if missing or extra:
                details = []
                if missing:
                    details.append("missing: " + ", ".join(missing))
                if extra:
                    details.append("extra: " + ", ".join(extra))
                _raise(
                    "blueprint_required_forms_mismatch",
                    "Blueprint required_forms must match current server profile; " + "; ".join(details),
                )
        support = _as_list(blueprint.get("support_grammar_targets"))
        allowed_support = set((_grammar_authoring_profile((lesson.grammar_id,)).get("support_grammar_targets") or []))
        invalid_support = sorted(set(support) - allowed_support - {lesson.grammar_id})
        if invalid_support:
            _raise("invalid_support_target", "Unsupported support targets: " + ", ".join(invalid_support))
        ids = _stable_ids(blueprint)
        duplicates = sorted({item for item in ids if ids.count(item) > 1})
        if duplicates:
            _raise("duplicate_stable_ids", "Duplicate stable IDs: " + ", ".join(duplicates))
        required_groups = ("examples", "mistakes", "understanding_checks", "guided_practice", "supported_production", "exit_check")
        missing_groups = [group for group in required_groups if not _stable_id_group(blueprint, group)]
        if missing_groups:
            _raise("missing_stable_id_group", "Missing stable ID groups: " + ", ".join(missing_groups))
        if not _as_list(blueprint.get("practice_progression_plan")):
            _raise("missing_practice_plan", "Blueprint requires practice_progression_plan")
        if not str(blueprint.get("production_goal") or "").strip():
            _raise("missing_production_goal", "Blueprint requires production_goal")
        _reject_raw_grammar_id_in_publicish_text(blueprint, grammar_id=lesson.grammar_id)
        normalized = dict(blueprint)
        return _valid("blueprint", blueprint_json=normalized)
    except LLMSchemaError as exc:
        return _invalid(exc)


def validate_concept_unit(
    payload: dict[str, Any],
    *,
    blueprint: dict[str, Any],
    lesson: GrammarCanonicalLesson,
) -> UnitValidationResult:
    try:
        _require_keys(payload, ("meaning_hook", "concept_explanation", "arabic_clarification"))
        blob = _blob(payload)
        _reject_generic(blob, display_name=str(blueprint.get("display_name") or ""))
        if "model_examples" in payload or "patterns" in payload:
            _raise("concept_rules_dump", "Concept unit must not duplicate examples or rules dump")
        intro = _concept_intro_text(payload)
        if lesson.cefr_level in {"A1", "A2"} and not _starts_with_arabic(intro):
            _raise("concept_not_arabic_first", "A1-A2 concept explanation must begin with natural Arabic")
        _reject_out_of_scope_teaching(blob, lesson=lesson)
        if lesson.cefr_level in {"A1", "A2"} and _arabic_count(blob) < 120:
            _raise("arabic_first_failure", "A1-A2 concept unit requires detailed natural Arabic")
        if blueprint.get("arabic_english_contrast") and _arabic_count(_blob(payload.get("arabic_clarification"))) < 20:
            _raise("missing_arabic_english_contrast", "Concept unit must include Arabic-English contrast")
        _reject_public_private_keys(payload)
        return _valid("concept", public_payload=payload)
    except LLMSchemaError as exc:
        return _invalid(exc)


def validate_examples_unit(
    payload: dict[str, Any],
    private_metadata: dict[str, Any] | None,
    *,
    blueprint: dict[str, Any],
    lesson: GrammarCanonicalLesson,
) -> UnitValidationResult:
    try:
        examples = _as_dict_list(payload.get("model_examples"))
        if not (3 <= len(examples) <= 5):
            _raise("invalid_example_count", "Examples unit requires 3-5 model examples")
        blueprint_ids = set(_stable_id_group(blueprint, "examples"))
        for item in examples:
            _id_in_blueprint(item.get("id"), blueprint_ids, "example_id_mismatch")
            sentence = str(item.get("sentence") or "")
            if not sentence or _fake_grammar_name_sentence(sentence, str(blueprint.get("display_name") or "")):
                _raise("fake_grammar_name_example", "Model examples must be real grammar uses")
            if not str(item.get("target_form") or "").strip():
                _raise("missing_target_form", "Every example requires target_form")
            if lesson.cefr_level in {"A1", "A2", "B1"} and _arabic_count(str(item.get("arabic_explanation") or "")) < 5:
                _raise("missing_example_arabic_explanation", "Every example needs Arabic explanation")
        use_case_ids = set(_stable_id_group(blueprint, "use_cases"))
        for use_case in _as_dict_list(payload.get("use_cases")):
            _id_in_blueprint(use_case.get("id"), use_case_ids, "use_case_id_mismatch")
            _require_keys(use_case, ("label", "explanation", "example", "arabic_explanation"))
        if not isinstance(payload.get("noticing"), dict) or str(payload["noticing"].get("id") or "") != _stable_id_scalar(blueprint, "noticing"):
            _raise("noticing_id_mismatch", "Noticing ID must match blueprint")
        _reject_public_private_keys(payload)
        return _valid("examples", public_payload=payload, private_metadata=private_metadata or {})
    except LLMSchemaError as exc:
        return _invalid(exc)


def validate_rules_unit(
    payload: dict[str, Any],
    *,
    blueprint: dict[str, Any],
    lesson: GrammarCanonicalLesson,
) -> UnitValidationResult:
    try:
        patterns = _as_dict_list(payload.get("patterns"))
        if not patterns:
            _raise("missing_patterns", "Rules unit requires patterns")
        text = _blob(payload)
        for form in _as_list(blueprint.get("required_forms")):
            if not required_form_covered(form, text, lesson=lesson):
                _raise("required_form_missing", f"Required form not covered: {form}")
        pattern_ids = set(_stable_id_group(blueprint, "patterns"))
        for pattern in patterns:
            if pattern_ids:
                _id_in_blueprint(pattern.get("id"), pattern_ids, "pattern_id_mismatch")
            if not str(pattern.get("example") or "").strip():
                _raise("rule_without_example", "Every pattern needs an immediate example")
        mistake_ids = set(_stable_id_group(blueprint, "mistakes"))
        mistakes = _as_dict_list(payload.get("contrasts_and_mistakes"))
        if len(mistakes) < 2:
            _raise("missing_mistakes", "Rules unit requires at least two mistakes")
        for mistake in mistakes:
            _id_in_blueprint(mistake.get("id"), mistake_ids, "mistake_id_mismatch")
            _require_keys(mistake, ("incorrect", "correct", "why", "misunderstanding"))
            if lesson.cefr_level in {"A1", "A2", "B1"} and _arabic_count(str(mistake.get("why") or "")) < 5:
                _raise("missing_mistake_reason", "Mistake reason must be Arabic for A1-B1")
        if lesson.grammar_id == "gram_be_present":
            for category in _as_list(blueprint.get("mistake_intentions")):
                if not required_mistake_category_covered(category, mistakes, lesson=lesson):
                    _raise("required_mistake_category_missing", f"Required mistake category not covered: {category}")
        if not _as_dict_list(payload.get("visual_summary")):
            _raise("missing_visual_summary", "Rules unit requires visual_summary")
        return _valid("rules", public_payload=payload)
    except LLMSchemaError as exc:
        return _invalid(exc)


def validate_practice_unit(
    payload: dict[str, Any],
    private_metadata: dict[str, Any] | None,
    *,
    blueprint: dict[str, Any],
    lesson: GrammarCanonicalLesson | None = None,
) -> UnitValidationResult:
    try:
        tasks = [*_as_dict_list(payload.get("understanding_checks")), *_as_dict_list(payload.get("guided_practice"))]
        task_types = [str(task.get("type") or "") for task in tasks]
        if is_rich_practice_payload(payload):
            normalized_private_metadata = _normalize_rich_practice_metadata(
                payload,
                private_metadata or {},
                lesson=lesson,
            )
            _validate_rich_practice_payload(payload, normalized_private_metadata, lesson=lesson, tasks=tasks)
            return _valid("practice", public_payload=payload, private_metadata=normalized_private_metadata)
        required = {"choice", "fill_blank", "reorder", "correction"}
        if not required.issubset(task_types):
            _raise("incomplete_practice_progression", "Practice requires choice, fill_blank, reorder, and correction")
        if "production" in task_types or "transfer" in task_types:
            _raise("production_before_controlled_practice", "Production cannot appear in practice unit")
        blueprint_ids = set(_stable_id_group(blueprint, "understanding_checks") + _stable_id_group(blueprint, "guided_practice"))
        ids = []
        for task in tasks:
            ids.append(str(task.get("id") or ""))
            _id_in_blueprint(task.get("id"), blueprint_ids, "practice_id_mismatch")
            _reject_public_private_keys(task)
        if len(ids) != len(set(ids)):
            _raise("duplicate_practice_ids", "Practice task IDs must be unique")
        return _valid("practice", public_payload=payload, private_metadata=private_metadata or {})
    except LLMSchemaError as exc:
        return _invalid(exc)


def validate_production_unit(
    payload: dict[str, Any],
    private_metadata: dict[str, Any] | None,
    *,
    blueprint: dict[str, Any],
) -> UnitValidationResult:
    try:
        _require_keys(payload, ("supported_production", "transfer", "exit_check", "reflection"))
        display_name = str(blueprint.get("display_name") or "")
        prompt_blob = _blob(payload)
        generic_patterns = (
            rf"\b(write|use)\b.{0,30}\b{re.escape(display_name)}\b.{0,30}\bsentence\b",
            rf"\bwrite\s+(one|a)?\s*sentence\s+using\s+{re.escape(display_name)}\b",
            rf"\buse\s+{re.escape(display_name)}\s+in\s+a\s+sentence\b",
        )
        if any(re.search(pattern, prompt_blob, re.IGNORECASE) for pattern in generic_patterns):
            _raise("generic_production_prompt", "Production prompt must ask for real meaning, not grammar-name usage")
        if re.search(r"\b(mastered|you mastered|now you know perfectly)\b", prompt_blob, re.IGNORECASE):
            _raise("mastery_claim_in_reflection", "Reflection must not claim mastery")
        production_ids = set(
            _stable_id_group(blueprint, "supported_production")
            + _stable_id_group(blueprint, "transfer")
            + _stable_id_group(blueprint, "exit_check")
        )
        for item in _as_dict_list(payload.get("supported_production")):
            _id_in_blueprint(item.get("id"), production_ids, "production_id_mismatch")
        _id_in_blueprint((payload.get("transfer") or {}).get("id"), production_ids, "transfer_id_mismatch")
        exit_check = payload.get("exit_check") if isinstance(payload.get("exit_check"), dict) else {}
        for key in ("recognition", "correction", "production"):
            if key not in exit_check:
                _raise("missing_exit_task", f"Missing exit_check.{key}")
            _id_in_blueprint((exit_check.get(key) or {}).get("id"), production_ids, "exit_id_mismatch")
        _reject_public_private_keys(payload)
        return _valid("production", public_payload=payload, private_metadata=private_metadata or {})
    except LLMSchemaError as exc:
        return _invalid(exc)


def validate_sectioned_unit(
    unit_key: str,
    payload: dict[str, Any],
    private_metadata: dict[str, Any] | None,
    *,
    blueprint: dict[str, Any] | None,
    lesson: GrammarCanonicalLesson,
) -> UnitValidationResult:
    if unit_key == "blueprint":
        return validate_blueprint_unit(payload, lesson=lesson)
    if not blueprint:
        return UnitValidationResult(valid=False, diagnostics_json=safe_diagnostics("missing_blueprint", "Blueprint required"))
    if unit_key == "concept":
        return validate_concept_unit(payload, blueprint=blueprint, lesson=lesson)
    if unit_key == "examples":
        return validate_examples_unit(payload, private_metadata, blueprint=blueprint, lesson=lesson)
    if unit_key == "rules":
        return validate_rules_unit(payload, blueprint=blueprint, lesson=lesson)
    if unit_key == "practice":
        return validate_practice_unit(payload, private_metadata, blueprint=blueprint, lesson=lesson)
    if unit_key == "production":
        return validate_production_unit(payload, private_metadata, blueprint=blueprint)
    return UnitValidationResult(valid=False, diagnostics_json=safe_diagnostics("invalid_unit_key", unit_key))


def _valid(
    unit_key: str,
    *,
    public_payload: dict[str, Any] | None = None,
    private_metadata: dict[str, Any] | None = None,
    blueprint_json: dict[str, Any] | None = None,
) -> UnitValidationResult:
    return UnitValidationResult(
        valid=True,
        normalized_public_payload=dict(public_payload) if public_payload is not None else None,
        normalized_private_metadata=dict(private_metadata or {}),
        normalized_blueprint=dict(blueprint_json) if blueprint_json is not None else None,
        content_hash=compute_unit_attempt_hash(
            unit_key=unit_key,
            public_payload_json=public_payload,
            private_metadata_json=private_metadata or {},
            blueprint_json=blueprint_json,
        ),
        diagnostics_json={"status": "valid"},
    )


def _invalid(exc: LLMSchemaError) -> UnitValidationResult:
    return UnitValidationResult(valid=False, diagnostics_json=safe_diagnostics(str(getattr(exc, "code", "unit_invalid")), str(exc)))


def _raise(code: str, message: str) -> None:
    raise LLMSchemaError(code, message)


def _require_keys(payload: dict[str, Any], keys: tuple[str, ...]) -> None:
    missing = [key for key in keys if payload.get(key) in (None, "", [], {})]
    if missing:
        _raise("missing_unit_fields", "Missing fields: " + ", ".join(missing))


def _as_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return []


def _as_dict_list(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [dict(item) for item in value if isinstance(item, dict)]


def _arabic_count(text: str) -> int:
    return len(_ARABIC_RE.findall(text or ""))


def _blob(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _reject_generic(text: str, *, display_name: str) -> None:
    if any(pattern.search(text or "") for pattern in _GENERIC_PATTERNS):
        _raise("generic_filler_detected", "Unit contains generic filler")
    if display_name and _fake_grammar_name_sentence(text, display_name):
        _raise("fake_grammar_name_example", "Unit contains grammar-name fake example")


def _concept_intro_text(payload: dict[str, Any]) -> str:
    explanation = payload.get("concept_explanation")
    if isinstance(explanation, dict):
        return str(
            explanation.get("arabic_concept_introduction")
            or explanation.get("arabic_concept_intro")
            or explanation.get("summary")
            or ""
        ).strip()
    if isinstance(explanation, list):
        return " ".join(str(item or "") for item in explanation).strip()
    return str(explanation or "").strip()


def _starts_with_arabic(text: str) -> bool:
    stripped = (text or "").lstrip(" \t\r\n\"'`،.؛:-")
    return bool(stripped and _ARABIC_RE.match(stripped[0]))


def _reject_out_of_scope_teaching(text: str, *, lesson: GrammarCanonicalLesson) -> None:
    if lesson.grammar_id == "gram_be_present":
        _reject_be_present_scope_creep(text)


def _reject_be_present_scope_creep(text: str) -> None:
    blob = text or ""
    checks = (
        ("past_be_scope_creep", r"\b(was|were)\b", "Present of be must not teach past be"),
        ("future_be_scope_creep", r"\b(will be|going to be)\b", "Present of be must not teach future be"),
        ("perfect_be_scope_creep", r"\b(have been|has been|had been)\b", "Present of be must not teach perfect be"),
        ("continuous_scope_creep", r"\b(am|is|are)\s+[A-Za-z]+ing\b", "Present of be must not teach present continuous"),
        ("modal_be_scope_creep", r"\b(can|could|should|must|may|might|would)\s+be\b", "Present of be must not teach modal be"),
        ("tag_question_scope_creep", r"\b(isn't it|aren't you|is she not|are they not)\?\b", "Present of be must not teach tag questions"),
    )
    for code, pattern, message in checks:
        if re.search(pattern, blob, re.IGNORECASE):
            _raise(code, message)
    if re.search(r"\b(wh-?question|wh question|where/what/who|what/where/who)\b", blob, re.IGNORECASE):
        _raise("wh_question_scope_creep", "Present of be must not teach broad WH-question formation")


def _profile_required_form_keys(lesson: GrammarCanonicalLesson) -> list[str]:
    if lesson.grammar_id != "gram_be_present":
        return []
    profile = _grammar_authoring_profile((lesson.grammar_id,))
    return _as_list(profile.get("required_form_keys"))


def required_form_covered(form: str, text: str, *, lesson: GrammarCanonicalLesson) -> bool:
    form_key = str(form or "").strip()
    if lesson.grammar_id == "gram_be_present":
        patterns = _BE_PRESENT_FORM_PATTERNS.get(form_key)
        if patterns:
            return any(re.search(pattern, text or "", re.IGNORECASE) for pattern in patterns)
    return bool(form_key and form_key.lower() in (text or "").lower())


def required_mistake_category_covered(
    category: str,
    mistakes: list[dict[str, Any]] | str,
    *,
    lesson: GrammarCanonicalLesson,
) -> bool:
    key = str(category or "").strip()
    if not key:
        return True
    if lesson.grammar_id != "gram_be_present":
        blob = mistakes if isinstance(mistakes, str) else _blob(mistakes)
        return key.lower() in str(blob or "").lower()
    blob = mistakes if isinstance(mistakes, str) else _blob(mistakes)
    text = str(blob or "").lower()
    patterns = {
        "be_deletion": (r"\bi\s+student\b", r"\b(she|he|it|they|we|you)\s+(ready|happy|home|student|teacher)\b", r"\bomitt?ing be\b", r"\bdelete be\b"),
        "wrong_be_agreement": (r"\b(she|he|it)\s+are\b", r"\bi\s+is\b", r"\bthey\s+is\b", r"\bagreement\b", r"\bwrong\s+(am|is|are|form)\b"),
        "missing_not": (r"\bmissing not\b", r"\bforget not\b", r"\bnot\b", r"\bisn['’]t\b", r"\baren['’]t\b"),
        "statement_order_question": (r"\bstatement order\b", r"\bquestion order\b", r"\binversion\b", r"\byou\s+are\s+[^.?]+\?", r"\bshe\s+is\s+[^.?]+\?"),
        "do_does_with_be": (r"\bdo\s+(you|we|they)\s+are\b", r"\bdoes\s+(he|she|it)\s+is\b", r"\bdo/does\b", r"\bdo\s+or\s+does\b"),
        "incomplete_short_answer": (r"\bincomplete short answer\b", r"\bshort answer\b", r"\byes/no without\b", r"\byes,\s*(?!i am|she is|he is|it is|they are|we are|you are)\b"),
    }.get(key, (re.escape(key),))
    return any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns)


def _fake_grammar_name_sentence(text: str, display_name: str) -> bool:
    if not display_name:
        return False
    escaped = re.escape(display_name)
    patterns = (
        rf"\bi use {escaped}\b",
        rf"\bshe uses {escaped}\b",
        rf"\bthey practice {escaped}\b",
        rf"\bthis sentence shows {escaped}\b",
    )
    return any(re.search(pattern, text or "", re.IGNORECASE) for pattern in patterns)


def _reject_public_private_keys(value: Any) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if key in _PRIVATE_KEYS:
                _raise("private_metadata_in_public_payload", f"Private key in public payload: {key}")
            _reject_public_private_keys(child)
    elif isinstance(value, list):
        for item in value:
            _reject_public_private_keys(item)


def _stable_ids(blueprint: dict[str, Any]) -> list[str]:
    values: list[str] = []

    def walk(value: Any) -> None:
        if isinstance(value, str):
            if value.strip():
                values.append(value.strip())
        elif isinstance(value, list):
            for item in value:
                walk(item)
        elif isinstance(value, dict):
            for item in value.values():
                walk(item)

    walk(blueprint.get("stable_ids") or {})
    return values


def _stable_id_group(blueprint: dict[str, Any], key: str) -> list[str]:
    raw = (blueprint.get("stable_ids") or {}).get(key) if isinstance(blueprint.get("stable_ids"), dict) else None
    if isinstance(raw, str):
        return [raw]
    if isinstance(raw, list):
        return [str(item).strip() for item in raw if str(item).strip()]
    if isinstance(raw, dict):
        return [str(item).strip() for item in raw.values() if str(item).strip()]
    return []


def _stable_id_scalar(blueprint: dict[str, Any], key: str) -> str:
    group = _stable_id_group(blueprint, key)
    return group[0] if group else ""


def _id_in_blueprint(raw_id: Any, blueprint_ids: set[str], code: str) -> None:
    item_id = str(raw_id or "").strip()
    if not item_id or item_id not in blueprint_ids:
        _raise(code, f"ID not owned by blueprint: {item_id}")


def _reject_raw_grammar_id_in_publicish_text(value: Any, *, grammar_id: str, key: str = "") -> None:
    if isinstance(value, dict):
        for child_key, child in value.items():
            if child_key in {"grammar_target", "support_grammar_targets"}:
                continue
            _reject_raw_grammar_id_in_publicish_text(child, grammar_id=grammar_id, key=child_key)
    elif isinstance(value, list):
        for item in value:
            _reject_raw_grammar_id_in_publicish_text(item, grammar_id=grammar_id, key=key)
    elif isinstance(value, str) and grammar_id in value:
        _raise("raw_grammar_id_exposed", "Blueprint learner-intended text contains raw grammar_id")


def _validate_rich_practice_payload(
    payload: dict[str, Any],
    private_metadata: dict[str, Any],
    *,
    lesson: GrammarCanonicalLesson | None,
    tasks: list[dict[str, Any]],
) -> None:
    if len(tasks) != RICH_PRACTICE_REQUIRED_TOTAL:
        _raise("invalid_rich_practice_count", f"Rich practice requires {RICH_PRACTICE_REQUIRED_TOTAL} tasks")
    if len(_as_dict_list(payload.get("understanding_checks"))) != 3:
        _raise("invalid_rich_practice_round", "Rich practice requires three multiple-choice understanding_checks")
    counts = {task_type: task_types_count(tasks, task_type) for task_type in RICH_PRACTICE_TASK_TYPES}
    mismatches = {
        key: {"expected": expected, "actual": counts.get(key, 0)}
        for key, expected in RICH_PRACTICE_REQUIRED_COUNTS.items()
        if counts.get(key, 0) != expected
    }
    if mismatches:
        _raise("invalid_rich_practice_variety", json.dumps(mismatches, ensure_ascii=False, sort_keys=True))
    if any(str(task.get("type") or "") != "multiple_choice" for task in _as_dict_list(payload.get("understanding_checks"))):
        _raise("invalid_rich_practice_round", "understanding_checks must contain only multiple_choice tasks")
    expected_ids = set(rich_practice_ids_for_grammar(lesson.grammar_id if lesson else ""))
    task_ids = [str(task.get("id") or "").strip() for task in tasks]
    if expected_ids:
        missing = sorted(expected_ids - set(task_ids))
        extra = sorted(set(task_ids) - expected_ids)
        if missing or extra:
            details = []
            if missing:
                details.append("missing: " + ", ".join(missing))
            if extra:
                details.append("extra: " + ", ".join(extra))
            _raise("rich_practice_id_mismatch", "; ".join(details))
    if len(task_ids) != len(set(task_ids)):
        _raise("duplicate_practice_ids", "Practice task IDs must be unique")
    for task in tasks:
        _validate_rich_public_task(task)
        _reject_public_private_keys(task)
    _validate_practice_metadata(tasks, private_metadata)


def task_types_count(tasks: list[dict[str, Any]], task_type: str) -> int:
    return sum(1 for task in tasks if str(task.get("type") or "") == task_type)


def _validate_rich_public_task(task: dict[str, Any]) -> None:
    task_id = str(task.get("id") or "").strip()
    task_type = str(task.get("type") or "").strip()
    if not task_id:
        _raise("missing_task_id", "Rich practice task requires id")
    if task_type not in RICH_PRACTICE_TASK_TYPES:
        _raise("invalid_task_type", f"Unsupported rich practice type: {task_type}")
    if not str(task.get("prompt") or "").strip():
        _raise("missing_task_prompt", f"{task_id} requires prompt")
    if not str(task.get("round_title") or "").strip():
        _raise("missing_round_title", f"{task_id} requires round_title")
    if task_type == "multiple_choice":
        options = task.get("options")
        if not isinstance(options, list) or not (2 <= len(options) <= 4):
            _raise("invalid_choice_payload", f"{task_id}.options requires 2-4 separate options")
        if len(options) != len({str(option).strip() for option in options}):
            _raise("invalid_choice_payload", f"{task_id}.options must be unique")
        if any(not isinstance(option, str) or not option.strip() for option in options):
            _raise("invalid_choice_payload", f"{task_id}.options must be strings")
        if any("\n" in option or "||" in option or " / " in option and len(option.split(" / ")) > 3 for option in options):
            _raise("concatenated_choice_options", f"{task_id}.options must be separate selectable values")
    elif task_type == "fill_blank":
        sentence = str(task.get("sentence_with_blank") or "")
        if "_____" not in sentence:
            _raise("invalid_fill_blank_payload", f"{task_id}.sentence_with_blank must include _____")
    elif task_type == "sentence_builder":
        chips = task.get("word_chips") or task.get("reorder_tokens")
        if not isinstance(chips, list) or len(chips) < 3:
            _raise("invalid_sentence_builder_payload", f"{task_id}.word_chips requires at least 3 chips")
    elif task_type == "transformation":
        if not str(task.get("original_sentence") or "").strip():
            _raise("invalid_transformation_payload", f"{task_id}.original_sentence required")
        if not str(task.get("transformation_goal") or "").strip():
            _raise("invalid_transformation_payload", f"{task_id}.transformation_goal required")
    elif task_type == "correction":
        if not str(task.get("incorrect_sentence") or "").strip():
            _raise("invalid_correction_payload", f"{task_id}.incorrect_sentence required")
    elif task_type == "short_answer":
        if not str(task.get("context") or "").strip():
            _raise("invalid_short_answer_payload", f"{task_id}.context required")
    elif task_type == "open_response":
        minimum = int(task.get("sentence_count_min") or 0)
        maximum = int(task.get("sentence_count_max") or 0)
        if minimum < 2 or maximum < minimum:
            _raise("invalid_open_response_payload", f"{task_id} requires sentence_count_min/max")
        starters = task.get("starters")
        if starters is not None and not isinstance(starters, list):
            _raise("invalid_open_response_payload", f"{task_id}.starters must be an array when present")


def _validate_practice_metadata(tasks: list[dict[str, Any]], metadata: dict[str, Any]) -> None:
    records = [
        *_as_dict_list(metadata.get("understanding_checks")),
        *_as_dict_list(metadata.get("guided_practice")),
    ]
    task_ids = [str(task.get("id") or "").strip() for task in tasks]
    metadata_ids = [str(record.get("item_id") or record.get("id") or "").strip() for record in records]
    missing = sorted(set(task_ids) - set(metadata_ids))
    unknown = sorted(set(metadata_ids) - set(task_ids))
    if missing:
        _raise("missing_server_metadata", "Missing metadata for rich practice item ids: " + ", ".join(missing))
    if unknown:
        _raise("unknown_metadata_item_id", "Metadata references unknown rich practice item ids: " + ", ".join(unknown))
    if len(metadata_ids) != len(set(metadata_ids)):
        _raise("duplicate_metadata_item_ids", "Duplicate metadata item ids")
    for task in tasks:
        item_id = str(task.get("id") or "")
        task_type = str(task.get("type") or "")
        record = next((item for item in records if str(item.get("item_id") or item.get("id") or "") == item_id), {})
        if task_type == "open_response":
            if not record.get("success_criteria") or not record.get("sample_answer"):
                _raise("incomplete_server_metadata", f"{item_id} needs success_criteria and sample_answer")
        elif not record.get("expected_answer"):
            _raise("incomplete_server_metadata", f"{item_id} needs expected_answer")


def _normalize_rich_practice_metadata(
    payload: dict[str, Any],
    metadata: dict[str, Any],
    *,
    lesson: GrammarCanonicalLesson | None,
) -> dict[str, Any]:
    normalized = copy.deepcopy(metadata or {})
    normalized.setdefault("understanding_checks", [])
    normalized.setdefault("guided_practice", [])
    existing_ids = {
        str(record.get("item_id") or record.get("id") or "").strip()
        for record in [
            *_as_dict_list(normalized.get("understanding_checks")),
            *_as_dict_list(normalized.get("guided_practice")),
        ]
    }
    if (lesson.grammar_id if lesson else "") != "gram_be_present":
        return normalized

    for task in _as_dict_list(payload.get("guided_practice")):
        if str(task.get("type") or "") != "open_response":
            continue
        item_id = str(task.get("id") or "").strip()
        if not item_id or item_id in existing_ids:
            continue
        normalized["guided_practice"].append(
            {
                "item_id": item_id,
                "sample_answer": "I am a student. I am at home. I am happy today.",
                "success_criteria": [
                    "2-4 short English sentences",
                    "uses present be forms correctly",
                    "communicates identity, location, or state",
                ],
                "hint": "Use short sentences with I am, I am at, or I am ... today.",
                "feedback_reasoning": "Open writing is checked by meaning, sentence count, and correct am/is/are use.",
            }
        )
        existing_ids.add(item_id)
    return normalized
