"""Canonical Claude grammar lesson package schema.

Claude returns only:
- student_content
- server_teaching_metadata

The server wraps that content in ActivitySpecification and may project a small
legacy student view while keeping server metadata private.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Literal

LESSON_SCHEMA_VERSION = 3
LESSON_PACKAGE_VERSION = "2.2.0"
CANONICAL_LESSON_SCHEMA_VERSION = "grammar_lesson_authoring_v2"
METHODOLOGY_VERSION = "grammar_lesson_methodology_v2_arabic_first"

PAYLOAD_LESSON_SCHEMA_VERSION_KEY = "lesson_schema_version"
PAYLOAD_LESSON_PACKAGE_VERSION_KEY = "lesson_package_version"
PAYLOAD_STUDENT_CONTENT_KEY = "student_content"
PAYLOAD_SERVER_TEACHING_METADATA_KEY = "server_teaching_metadata"
PAYLOAD_CANONICAL_LESSON_KEY = "canonical_lesson"
PAYLOAD_METHODOLOGY_VERSION_KEY = "methodology_version"

METHODOLOGY_SECTIONS: tuple[str, ...] = (
    "orientation",
    "meaning_hook",
    "model_examples",
    "noticing",
    "concept_explanation",
    "form_and_rules",
    "arabic_clarification",
    "contrasts_and_mistakes",
    "understanding_checks",
    "guided_practice",
    "supported_production",
    "transfer",
    "exit_check",
    "reflection",
)

# Backward-compatible projected sections consumed by current product response.
REQUIRED_LESSON_SECTIONS: tuple[str, ...] = (
    "teacher_opening",
    "lesson_goal",
    "warmup",
    "main_activity",
    "follow_up_questions",
    "grammar_focus",
    "expected_patterns",
    "common_mistakes",
    "teacher_hints",
    "encouragement_messages",
    "completion_message",
)
REQUIRED_PERSONALIZATION_SECTIONS: tuple[str, ...] = (
    "alternative_examples",
    "extra_scaffolding",
    "adaptive_followups",
    "difficulty_adjustments",
    "review_focus",
    "encouragement",
)
ALL_REQUIRED_LESSON_SECTIONS: tuple[str, ...] = (
    REQUIRED_LESSON_SECTIONS + REQUIRED_PERSONALIZATION_SECTIONS
)

JSON_LIST_SECTIONS: frozenset[str] = frozenset(
    {
        "follow_up_questions",
        "expected_patterns",
        "common_mistakes",
        "teacher_hints",
        "encouragement_messages",
        "alternative_examples",
        "extra_scaffolding",
        "adaptive_followups",
    }
)

TaskType = Literal[
    "choice",
    "fill_blank",
    "reorder",
    "correction",
    "production",
    "transfer",
    "multiple_choice",
    "sentence_builder",
    "transformation",
    "short_answer",
    "open_response",
]


@dataclass(frozen=True, slots=True)
class CommonMistakeExample:
    """Guidance-only mistake pair; never used for scoring."""

    incorrect: str
    correct: str


@dataclass(frozen=True, slots=True)
class LessonTask:
    """Student-facing render payload for an evaluable lesson item."""

    id: str
    type: TaskType
    prompt: str
    options: tuple[str, ...] = ()
    sentence_with_blank: str | None = None
    reorder_tokens: tuple[str, ...] = ()
    word_chips: tuple[str, ...] = ()
    incorrect_sentence: str | None = None
    original_sentence: str | None = None
    transformation_goal: str | None = None
    scaffold: str | None = None
    context: str | None = None
    round_title: str | None = None
    sentence_count_min: int | None = None
    sentence_count_max: int | None = None
    starters: tuple[str, ...] = ()

    def to_student_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "id": self.id,
            "type": self.type,
            "prompt": self.prompt,
        }
        if self.round_title:
            out["round_title"] = self.round_title
        if self.context:
            out["context"] = self.context
        if self.type in {"choice", "multiple_choice"}:
            out["options"] = list(self.options)
        elif self.type == "fill_blank":
            out["sentence_with_blank"] = self.sentence_with_blank
        elif self.type == "reorder":
            out["reorder_tokens"] = list(self.reorder_tokens)
        elif self.type == "sentence_builder":
            out["word_chips"] = list(self.word_chips or self.reorder_tokens)
        elif self.type == "correction":
            out["incorrect_sentence"] = self.incorrect_sentence
        elif self.type == "transformation":
            out["original_sentence"] = self.original_sentence
            out["transformation_goal"] = self.transformation_goal
        elif self.type == "short_answer":
            pass
        elif self.type == "open_response":
            out["sentence_count_min"] = self.sentence_count_min
            out["sentence_count_max"] = self.sentence_count_max
            if self.starters:
                out["starters"] = list(self.starters)
        elif self.type == "production":
            out["scaffold"] = self.scaffold
        elif self.type == "transfer":
            out["context"] = self.context
        return out


@dataclass(frozen=True, slots=True)
class MetadataRecord:
    """Server-only teaching metadata for exactly one student item."""

    item_id: str
    expected_answer: str | None = None
    sample_answer: str | None = None
    success_criteria: tuple[str, ...] = ()
    misconception: str | None = None
    feedback_reasoning: str | None = None
    hint: str | None = None
    similar_retry_prompt: str | None = None

    def to_server_dict(self) -> dict[str, Any]:
        return {
            "item_id": self.item_id,
            "expected_answer": self.expected_answer,
            "sample_answer": self.sample_answer,
            "success_criteria": list(self.success_criteria),
            "misconception": self.misconception,
            "feedback_reasoning": self.feedback_reasoning,
            "hint": self.hint,
            "similar_retry_prompt": self.similar_retry_prompt,
        }


@dataclass(frozen=True, slots=True)
class CanonicalLessonPackage:
    """Canonical lesson content and private teaching metadata."""

    student_content: dict[str, Any]
    server_teaching_metadata: dict[str, Any]

    def to_mapping(self) -> dict[str, Any]:
        return {
            PAYLOAD_STUDENT_CONTENT_KEY: self.student_content,
            PAYLOAD_SERVER_TEACHING_METADATA_KEY: self.server_teaching_metadata,
        }


@dataclass(frozen=True, slots=True)
class GrammarLessonPackage:
    """Compatibility projection for current student lesson response."""

    teacher_opening: str
    lesson_goal: str
    warmup: str
    main_activity: str
    follow_up_questions: tuple[str, ...]
    grammar_focus: str
    expected_patterns: tuple[str, ...]
    common_mistakes: tuple[CommonMistakeExample, ...]
    teacher_hints: tuple[str, ...]
    encouragement_messages: tuple[str, ...]
    completion_message: str
    alternative_examples: tuple[str, ...] = ()
    extra_scaffolding: tuple[str, ...] = ()
    adaptive_followups: tuple[str, ...] = ()
    difficulty_adjustments: str = ""
    review_focus: str = ""
    encouragement: str = ""
    lesson_schema_version: int = LESSON_SCHEMA_VERSION
    lesson_package_version: str = LESSON_PACKAGE_VERSION
    extras: dict[str, str] = field(default_factory=dict)

    def section_text_blob(self) -> str:
        parts = [
            self.teacher_opening,
            self.lesson_goal,
            self.warmup,
            self.main_activity,
            self.grammar_focus,
            self.completion_message,
            self.difficulty_adjustments,
            self.review_focus,
            self.encouragement,
            *self.follow_up_questions,
            *self.expected_patterns,
            *self.teacher_hints,
            *self.encouragement_messages,
            *self.alternative_examples,
            *self.extra_scaffolding,
            *self.adaptive_followups,
        ]
        for mistake in self.common_mistakes:
            parts.append(mistake.incorrect)
            parts.append(mistake.correct)
        return "\n".join(parts)

    def personalization_text_blob(self) -> str:
        return "\n".join(
            [
                self.difficulty_adjustments,
                self.review_focus,
                self.encouragement,
                *self.alternative_examples,
                *self.extra_scaffolding,
                *self.adaptive_followups,
            ]
        )


def _parse_json_maybe(raw: Any) -> Any:
    if isinstance(raw, str):
        text = raw.strip()
        if not text:
            return text
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return raw
    return raw


def _as_str(raw: Any) -> str:
    return str(raw or "").strip()


def _as_optional_str(raw: Any) -> str | None:
    text = _as_str(raw)
    return text or None


def _as_optional_int(raw: Any) -> int | None:
    if raw in (None, ""):
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def _as_str_list(raw: Any, *, field_name: str) -> tuple[str, ...]:
    raw = _parse_json_maybe(raw)
    if raw in (None, "", ()):
        return ()
    if isinstance(raw, tuple):
        raw = list(raw)
    if not isinstance(raw, list):
        raise ValueError(f"{field_name} must be a list")
    return tuple(str(item).strip() for item in raw if str(item).strip())


def _as_mistakes(raw: Any) -> tuple[CommonMistakeExample, ...]:
    raw = _parse_json_maybe(raw)
    if raw in (None, ""):
        return ()
    if not isinstance(raw, list):
        raise ValueError("common_mistakes must be a list")
    out: list[CommonMistakeExample] = []
    for item in raw:
        if not isinstance(item, dict):
            raise ValueError("common_mistakes items must be objects")
        incorrect = _as_str(item.get("incorrect"))
        correct = _as_str(item.get("correct"))
        if incorrect and correct:
            out.append(CommonMistakeExample(incorrect=incorrect, correct=correct))
    return tuple(out)


def _task_from_mapping(raw: dict[str, Any], *, expected_type: str | None = None) -> LessonTask:
    task_type = _as_str(raw.get("type") or expected_type)
    if task_type not in {
        "choice",
        "fill_blank",
        "reorder",
        "correction",
        "production",
        "transfer",
        "multiple_choice",
        "sentence_builder",
        "transformation",
        "short_answer",
        "open_response",
    }:
        raise ValueError(f"Unsupported task type: {task_type}")
    return LessonTask(
        id=_as_str(raw.get("id")),
        type=task_type,  # type: ignore[arg-type]
        prompt=_as_str(raw.get("prompt")),
        options=_as_str_list(raw.get("options") or (), field_name="options"),
        sentence_with_blank=_as_optional_str(raw.get("sentence_with_blank") or raw.get("sentence")),
        reorder_tokens=_as_str_list(raw.get("reorder_tokens") or (), field_name="reorder_tokens"),
        word_chips=_as_str_list(raw.get("word_chips") or raw.get("reorder_tokens") or (), field_name="word_chips"),
        incorrect_sentence=_as_optional_str(raw.get("incorrect_sentence")),
        original_sentence=_as_optional_str(raw.get("original_sentence")),
        transformation_goal=_as_optional_str(raw.get("transformation_goal")),
        scaffold=_as_optional_str(raw.get("scaffold")),
        context=_as_optional_str(raw.get("context")),
        round_title=_as_optional_str(raw.get("round_title")),
        sentence_count_min=_as_optional_int(raw.get("sentence_count_min")),
        sentence_count_max=_as_optional_int(raw.get("sentence_count_max")),
        starters=_as_str_list(raw.get("starters") or (), field_name="starters"),
    )


def _task_to_clean_dict(raw: dict[str, Any], *, expected_type: str | None = None) -> dict[str, Any]:
    return _task_from_mapping(raw, expected_type=expected_type).to_student_dict()


def _metadata_from_mapping(raw: dict[str, Any]) -> MetadataRecord:
    return MetadataRecord(
        item_id=_as_str(raw.get("item_id") or raw.get("id")),
        expected_answer=_as_optional_str(raw.get("expected_answer")),
        sample_answer=_as_optional_str(raw.get("sample_answer")),
        success_criteria=_as_str_list(raw.get("success_criteria") or (), field_name="success_criteria"),
        misconception=_as_optional_str(raw.get("misconception")),
        feedback_reasoning=_as_optional_str(raw.get("feedback_reasoning")),
        hint=_as_optional_str(raw.get("hint")),
        similar_retry_prompt=_as_optional_str(raw.get("similar_retry_prompt")),
    )


def _normalize_metadata_records(raw: Any) -> list[dict[str, Any]]:
    if raw in (None, ""):
        return []
    if isinstance(raw, dict):
        return [_metadata_from_mapping(raw).to_server_dict()]
    if not isinstance(raw, list):
        raise ValueError("metadata records must be objects or arrays")
    return [_metadata_from_mapping(item).to_server_dict() for item in raw if isinstance(item, dict)]


def normalize_canonical_lesson_output(raw: dict[str, Any]) -> CanonicalLessonPackage:
    """Normalize Claude output to the exact canonical package shape."""
    student = dict(raw.get(PAYLOAD_STUDENT_CONTENT_KEY) or {})
    metadata = dict(raw.get(PAYLOAD_SERVER_TEACHING_METADATA_KEY) or {})

    normalized_student: dict[str, Any] = {}
    for section in METHODOLOGY_SECTIONS:
        value = student.get(section)
        normalized_student[section] = value

    normalized_student["model_examples"] = [
        {
            "id": _as_str(item.get("id")),
            "sentence": _as_str(item.get("sentence")),
            "teaching_purpose": _as_str(item.get("teaching_purpose")),
            "target_form": _as_str(item.get("target_form")),
            "arabic_meaning": _as_optional_str(item.get("arabic_meaning")),
            "arabic_explanation": _as_str(item.get("arabic_explanation")),
        }
        for item in (student.get("model_examples") or [])
        if isinstance(item, dict)
    ]
    normalized_student["noticing"] = {
        "id": _as_str((student.get("noticing") or {}).get("id")),
        "prompt": _as_str((student.get("noticing") or {}).get("prompt")),
        "expected_observations": list(
            _as_str_list(
                (student.get("noticing") or {}).get("expected_observations") or (),
                field_name="expected_observations",
            )
        ),
    }
    form_raw = student.get("form_and_rules") or {}
    normalized_student["form_and_rules"] = {
        "patterns": [
            {
                "id": _as_str(item.get("id")),
                "pattern": _as_str(item.get("pattern")),
                "meaning": _as_str(item.get("meaning")),
                "explanation": _as_str(item.get("explanation")),
                "example": _as_str(item.get("example")),
            }
            for item in (form_raw.get("patterns") or [])
            if isinstance(item, dict)
        ],
        "rule_notes": list(
            _as_str_list(form_raw.get("rule_notes") or (), field_name="rule_notes")
        ),
        "use_cases": [
            {
                "id": _as_str(item.get("id")),
                "label": _as_str(item.get("label")),
                "explanation": _as_str(item.get("explanation")),
                "example": _as_str(item.get("example")),
                "arabic_explanation": _as_str(item.get("arabic_explanation")),
            }
            for item in (form_raw.get("use_cases") or [])
            if isinstance(item, dict)
        ],
        "visual_summary": [
            {
                "label": _as_str(item.get("label")),
                "value": _as_str(item.get("value")),
                "warning": _as_optional_str(item.get("warning")),
            }
            for item in (form_raw.get("visual_summary") or [])
            if isinstance(item, dict)
        ],
    }
    normalized_student["arabic_clarification"] = {
        "arabic": _as_optional_str((student.get("arabic_clarification") or {}).get("arabic")),
        "arabic_speaker_warning": _as_optional_str(
            (student.get("arabic_clarification") or {}).get("arabic_speaker_warning")
        ),
        "arabic_english_contrast": _as_optional_str(
            (student.get("arabic_clarification") or {}).get("arabic_english_contrast")
        ),
    }
    normalized_student["contrasts_and_mistakes"] = [
        {
            "id": _as_str(item.get("id")),
            "incorrect": _as_str(item.get("incorrect")),
            "correct": _as_str(item.get("correct")),
            "why": _as_str(item.get("why") or item.get("reason")),
            "misunderstanding": _as_str(item.get("misunderstanding")),
        }
        for item in (student.get("contrasts_and_mistakes") or [])
        if isinstance(item, dict)
    ]
    normalized_student["understanding_checks"] = [
        _task_to_clean_dict(item) for item in (student.get("understanding_checks") or []) if isinstance(item, dict)
    ]
    normalized_student["guided_practice"] = [
        _task_to_clean_dict(item) for item in (student.get("guided_practice") or []) if isinstance(item, dict)
    ]
    normalized_student["supported_production"] = [
        _task_to_clean_dict(item, expected_type="production")
        for item in (student.get("supported_production") or [])
        if isinstance(item, dict)
    ]
    normalized_student["transfer"] = _task_to_clean_dict(student.get("transfer") or {}, expected_type="transfer")
    exit_check = student.get("exit_check") or {}
    normalized_student["exit_check"] = {
        "recognition": _task_to_clean_dict(exit_check.get("recognition") or {}, expected_type="choice"),
        "correction": _task_to_clean_dict(exit_check.get("correction") or {}, expected_type="correction"),
        "production": _task_to_clean_dict(exit_check.get("production") or {}, expected_type="production"),
    }

    normalized_metadata = {
        "noticing": _normalize_metadata_records(metadata.get("noticing")),
        "understanding_checks": _normalize_metadata_records(metadata.get("understanding_checks")),
        "guided_practice": _normalize_metadata_records(metadata.get("guided_practice")),
        "supported_production": _normalize_metadata_records(metadata.get("supported_production")),
        "transfer": _normalize_metadata_records(metadata.get("transfer")),
        "exit_check": _normalize_metadata_records(metadata.get("exit_check")),
    }
    return CanonicalLessonPackage(
        student_content=normalized_student,
        server_teaching_metadata=normalized_metadata,
    )


def _canonical_text_blob(student: dict[str, Any]) -> str:
    return json.dumps(student, ensure_ascii=True, sort_keys=True)


def _project_legacy_from_canonical(
    canonical: CanonicalLessonPackage,
    *,
    grammar_focus: str = "",
) -> GrammarLessonPackage:
    student = canonical.student_content
    orientation = student.get("orientation") if isinstance(student.get("orientation"), dict) else {}
    meaning_hook = student.get("meaning_hook") if isinstance(student.get("meaning_hook"), dict) else {}
    explanation = student.get("concept_explanation")
    if isinstance(explanation, list):
        explanation_text = "\n".join(_as_str(x) for x in explanation if _as_str(x))
    elif isinstance(explanation, dict):
        explanation_text = "\n".join(
            value
            for value in (
                _as_str(explanation.get("arabic_concept_introduction")),
                _as_str(explanation.get("english_bridge")),
                _as_str(explanation.get("summary")),
                _as_str(explanation.get("text")),
            )
            if value
        )
    else:
        explanation_text = _as_str(explanation)

    follow_ups: list[str] = []
    for item in student.get("understanding_checks") or []:
        if isinstance(item, dict) and _as_str(item.get("prompt")):
            follow_ups.append(_as_str(item.get("prompt")))
    for item in student.get("supported_production") or []:
        if isinstance(item, dict) and _as_str(item.get("prompt")):
            follow_ups.append(_as_str(item.get("prompt")))
    transfer = student.get("transfer")
    if isinstance(transfer, dict) and _as_str(transfer.get("prompt")):
        follow_ups.append(_as_str(transfer.get("prompt")))

    patterns = []
    form = student.get("form_and_rules") if isinstance(student.get("form_and_rules"), dict) else {}
    for item in form.get("patterns") or []:
        if isinstance(item, dict):
            value = _as_str(item.get("pattern"))
            if value:
                patterns.append(value)

    mistakes = []
    for item in student.get("contrasts_and_mistakes") or []:
        if isinstance(item, dict):
            incorrect = _as_str(item.get("incorrect"))
            correct = _as_str(item.get("correct"))
            if incorrect and correct:
                mistakes.append(CommonMistakeExample(incorrect=incorrect, correct=correct))

    rule_notes = _as_str_list(form.get("rule_notes") or (), field_name="rule_notes")
    arabic = student.get("arabic_clarification") if isinstance(student.get("arabic_clarification"), dict) else {}
    arabic_notes = tuple(
        note
        for note in (
            _as_str(arabic.get("arabic")),
            _as_str(arabic.get("arabic_speaker_warning")),
            _as_str(arabic.get("arabic_english_contrast")),
        )
        if note
    )
    reflection = student.get("reflection") if isinstance(student.get("reflection"), dict) else {}

    return GrammarLessonPackage(
        teacher_opening=_as_str(orientation.get("teacher_script") or orientation.get("text")),
        lesson_goal=_as_str(meaning_hook.get("situation") or meaning_hook.get("why_it_matters") or explanation_text),
        warmup=_as_str((student.get("noticing") or {}).get("prompt")),
        main_activity=_as_str((student.get("guided_practice") or [{}])[0].get("prompt") if student.get("guided_practice") else explanation_text),
        follow_up_questions=tuple(follow_ups[:8]),
        grammar_focus=grammar_focus,
        expected_patterns=tuple(patterns),
        common_mistakes=tuple(mistakes),
        teacher_hints=tuple(rule_notes + arabic_notes),
        encouragement_messages=tuple(
            x
            for x in (
                _as_str(reflection.get("encouragement")),
                _as_str(reflection.get("next_step")),
            )
            if x
        ),
        completion_message=_as_str(reflection.get("summary") or reflection.get("encouragement")),
        alternative_examples=tuple(
            _as_str(item.get("sentence"))
            for item in student.get("model_examples") or []
            if isinstance(item, dict) and _as_str(item.get("sentence"))
        ),
        extra_scaffolding=tuple(
            _as_str(item.get("scaffold"))
            for item in student.get("supported_production") or []
            if isinstance(item, dict) and _as_str(item.get("scaffold"))
        ),
        adaptive_followups=tuple(follow_ups[:3]),
        difficulty_adjustments=_as_str(reflection.get("difficulty_note")),
        review_focus=_as_str(reflection.get("review_focus") or grammar_focus),
        encouragement=_as_str(reflection.get("encouragement")),
        extras={
            PAYLOAD_STUDENT_CONTENT_KEY: json.dumps(canonical.student_content, ensure_ascii=True, sort_keys=True),
            PAYLOAD_SERVER_TEACHING_METADATA_KEY: json.dumps(
                canonical.server_teaching_metadata, ensure_ascii=True, sort_keys=True
            ),
            PAYLOAD_CANONICAL_LESSON_KEY: json.dumps(
                canonical.to_mapping(), ensure_ascii=True, sort_keys=True
            ),
            PAYLOAD_METHODOLOGY_VERSION_KEY: METHODOLOGY_VERSION,
        },
    )


def canonical_lesson_to_payload(
    canonical: CanonicalLessonPackage | dict[str, Any],
    *,
    grammar_focus: str = "",
) -> dict[str, str]:
    package = (
        canonical
        if isinstance(canonical, CanonicalLessonPackage)
        else normalize_canonical_lesson_output(canonical)
    )
    return lesson_package_to_payload(
        _project_legacy_from_canonical(package, grammar_focus=grammar_focus)
    )


def lesson_package_from_mapping(raw: dict[str, Any]) -> GrammarLessonPackage:
    """Build compatibility package from canonical or legacy payload maps."""
    data = dict(raw or {})

    canonical_raw: Any | None = None
    if PAYLOAD_CANONICAL_LESSON_KEY in data:
        canonical_raw = _parse_json_maybe(data[PAYLOAD_CANONICAL_LESSON_KEY])
    elif PAYLOAD_STUDENT_CONTENT_KEY in data and PAYLOAD_SERVER_TEACHING_METADATA_KEY in data:
        canonical_raw = {
            PAYLOAD_STUDENT_CONTENT_KEY: _parse_json_maybe(data[PAYLOAD_STUDENT_CONTENT_KEY]),
            PAYLOAD_SERVER_TEACHING_METADATA_KEY: _parse_json_maybe(data[PAYLOAD_SERVER_TEACHING_METADATA_KEY]),
        }
    elif PAYLOAD_STUDENT_CONTENT_KEY in data:
        canonical_raw = {
            PAYLOAD_STUDENT_CONTENT_KEY: _parse_json_maybe(data[PAYLOAD_STUDENT_CONTENT_KEY]),
            PAYLOAD_SERVER_TEACHING_METADATA_KEY: {},
        }
    if isinstance(canonical_raw, dict):
        canonical = normalize_canonical_lesson_output(canonical_raw)
        return _project_legacy_from_canonical(
            canonical,
            grammar_focus=_as_str(data.get("grammar_focus")),
        )

    schema_version = int(
        data.get(PAYLOAD_LESSON_SCHEMA_VERSION_KEY)
        or data.get("lesson_schema_version")
        or LESSON_SCHEMA_VERSION
    )
    required = ALL_REQUIRED_LESSON_SECTIONS if schema_version >= 2 else REQUIRED_LESSON_SECTIONS
    missing = [k for k in required if k not in data or data.get(k) in (None, "")]
    if missing:
        raise ValueError(f"Missing lesson sections: {', '.join(missing)}")

    return GrammarLessonPackage(
        teacher_opening=_as_str(data["teacher_opening"]),
        lesson_goal=_as_str(data["lesson_goal"]),
        warmup=_as_str(data["warmup"]),
        main_activity=_as_str(data["main_activity"]),
        follow_up_questions=_as_str_list(data["follow_up_questions"], field_name="follow_up_questions"),
        grammar_focus=_as_str(data["grammar_focus"]),
        expected_patterns=_as_str_list(data["expected_patterns"], field_name="expected_patterns"),
        common_mistakes=_as_mistakes(data["common_mistakes"]),
        teacher_hints=_as_str_list(data["teacher_hints"], field_name="teacher_hints"),
        encouragement_messages=_as_str_list(data["encouragement_messages"], field_name="encouragement_messages"),
        completion_message=_as_str(data["completion_message"]),
        alternative_examples=_as_str_list(data.get("alternative_examples") or (), field_name="alternative_examples"),
        extra_scaffolding=_as_str_list(data.get("extra_scaffolding") or (), field_name="extra_scaffolding"),
        adaptive_followups=_as_str_list(data.get("adaptive_followups") or (), field_name="adaptive_followups"),
        difficulty_adjustments=_as_str(data.get("difficulty_adjustments")),
        review_focus=_as_str(data.get("review_focus")),
        encouragement=_as_str(data.get("encouragement")),
        lesson_schema_version=schema_version,
        lesson_package_version=_as_str(data.get(PAYLOAD_LESSON_PACKAGE_VERSION_KEY) or LESSON_PACKAGE_VERSION),
    )


def lesson_package_to_payload(package: GrammarLessonPackage) -> dict[str, str]:
    """Serialize compatibility package into ActivitySpecification.payload."""
    return {
        PAYLOAD_LESSON_SCHEMA_VERSION_KEY: str(package.lesson_schema_version),
        PAYLOAD_LESSON_PACKAGE_VERSION_KEY: package.lesson_package_version,
        "teacher_opening": package.teacher_opening,
        "lesson_goal": package.lesson_goal,
        "warmup": package.warmup,
        "main_activity": package.main_activity,
        "follow_up_questions": json.dumps(list(package.follow_up_questions), ensure_ascii=True),
        "grammar_focus": package.grammar_focus,
        "expected_patterns": json.dumps(list(package.expected_patterns), ensure_ascii=True),
        "common_mistakes": json.dumps(
            [{"incorrect": m.incorrect, "correct": m.correct} for m in package.common_mistakes],
            ensure_ascii=True,
        ),
        "teacher_hints": json.dumps(list(package.teacher_hints), ensure_ascii=True),
        "encouragement_messages": json.dumps(list(package.encouragement_messages), ensure_ascii=True),
        "completion_message": package.completion_message,
        "alternative_examples": json.dumps(list(package.alternative_examples), ensure_ascii=True),
        "extra_scaffolding": json.dumps(list(package.extra_scaffolding), ensure_ascii=True),
        "adaptive_followups": json.dumps(list(package.adaptive_followups), ensure_ascii=True),
        "difficulty_adjustments": package.difficulty_adjustments,
        "review_focus": package.review_focus,
        "encouragement": package.encouragement,
        **{str(k): str(v) for k, v in package.extras.items()},
    }


def extract_lesson_mapping_from_llm_data(data: dict[str, Any]) -> dict[str, Any]:
    """Pull canonical lesson output or legacy lesson sections."""
    if PAYLOAD_STUDENT_CONTENT_KEY in data:
        return dict(data)
    if isinstance(data.get("lesson"), dict):
        return dict(data["lesson"])
    if isinstance(data.get("lesson_package"), dict):
        return dict(data["lesson_package"])
    payload = data.get("payload")
    if isinstance(payload, dict) and (
        PAYLOAD_STUDENT_CONTENT_KEY in payload or all(k in payload for k in ("teacher_opening", "main_activity"))
    ):
        return dict(payload)
    if "teacher_opening" in data and "main_activity" in data:
        return {k: data[k] for k in ALL_REQUIRED_LESSON_SECTIONS if k in data}
    return {}


def lesson_package_from_specification_payload(payload: dict[str, str]) -> GrammarLessonPackage:
    return lesson_package_from_mapping(dict(payload))


def canonical_student_text_blob(raw: dict[str, Any]) -> str:
    canonical = normalize_canonical_lesson_output(raw)
    return _canonical_text_blob(canonical.student_content)
