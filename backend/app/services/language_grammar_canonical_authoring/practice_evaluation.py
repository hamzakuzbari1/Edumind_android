"""Server-side practice evaluation for canonical grammar lesson previews."""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.language.grammar_canonical_lesson import (
    GrammarCanonicalLesson,
    GrammarCanonicalLessonRevision,
)
from app.services.language_grammar_activity_authoring.llm.lesson_schema import METHODOLOGY_VERSION
from app.services.language_grammar_canonical_authoring.validation import validate_persisted_revision_payload
from app.services.language_grammar_canonical_lessons import GrammarCanonicalRevisionStatus


_FINAL_PUNCTUATION_RE = re.compile(r"[\s.!?؟،,;:]+$")
_WHITESPACE_RE = re.compile(r"\s+")


class GrammarPracticeEvaluationError(ValueError):
    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(code, message)


@dataclass(frozen=True, slots=True)
class PracticeEvaluationResult:
    correct: bool
    feedback: str
    hint: str | None
    may_continue: bool
    attempt_number: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "correct": self.correct,
            "feedback": self.feedback,
            "hint": self.hint,
            "may_continue": self.may_continue,
            "attempt_number": self.attempt_number,
        }


async def evaluate_canonical_revision_preview_practice(
    db: AsyncSession,
    *,
    revision_id: uuid.UUID,
    item_id: str,
    learner_response: Any,
    attempt_number: int = 1,
) -> PracticeEvaluationResult:
    """Evaluate one public preview practice item against private revision metadata without writes."""
    return await _evaluate_canonical_revision_practice(
        db,
        revision_id=revision_id,
        item_id=item_id,
        learner_response=learner_response,
        attempt_number=attempt_number,
        allowed_statuses={GrammarCanonicalRevisionStatus.REVIEWABLE.value},
        unavailable_code="revision_not_reviewable",
    )


async def evaluate_canonical_revision_student_practice(
    db: AsyncSession,
    *,
    revision_id: uuid.UUID,
    item_id: str,
    learner_response: Any,
    attempt_number: int = 1,
    allow_reviewable: bool = False,
) -> PracticeEvaluationResult:
    """Evaluate one public student practice item against private revision metadata without writes."""
    allowed_statuses = {GrammarCanonicalRevisionStatus.PUBLISHED.value}
    if allow_reviewable:
        allowed_statuses.add(GrammarCanonicalRevisionStatus.REVIEWABLE.value)
    return await _evaluate_canonical_revision_practice(
        db,
        revision_id=revision_id,
        item_id=item_id,
        learner_response=learner_response,
        attempt_number=attempt_number,
        allowed_statuses=allowed_statuses,
        unavailable_code="revision_not_available",
    )


async def build_canonical_revision_practice_answer_key(
    db: AsyncSession,
    *,
    revision_id: uuid.UUID,
    allowed_statuses: set[str] | None = None,
) -> dict[str, Any]:
    """Build a private server-only answer key for canonical lesson completion."""
    revision = await db.get(GrammarCanonicalLessonRevision, revision_id)
    if revision is None:
        raise GrammarPracticeEvaluationError("revision_not_found", "Canonical grammar revision was not found")
    if allowed_statuses is not None and revision.status not in allowed_statuses:
        raise GrammarPracticeEvaluationError(
            "revision_not_available",
            f"Revision status cannot be evaluated here; got {revision.status!r}",
        )

    lesson = await db.get(GrammarCanonicalLesson, revision.lesson_id)
    if lesson is None:
        raise GrammarPracticeEvaluationError("canonical_lesson_not_found", "Revision parent lesson was not found")
    if lesson.methodology_version != METHODOLOGY_VERSION:
        raise GrammarPracticeEvaluationError("methodology_mismatch", "Revision uses an unsupported methodology")

    validation = validate_persisted_revision_payload(lesson=lesson, revision=revision)
    if not validation.valid:
        raise GrammarPracticeEvaluationError("revision_payload_invalid", "Revision failed canonical validation")

    student_content = validation.normalized_student_content or revision.student_content_json or {}
    metadata = validation.normalized_server_teaching_metadata or revision.server_teaching_metadata_json or {}
    answer_key: dict[str, dict[str, Any]] = {}
    for task in _practice_tasks(student_content):
        item_id = str(task.get("id") or "").strip()
        if not item_id:
            continue
        record = _metadata_by_item_id(metadata, item_id)
        if record is None:
            continue
        expected = _expected_answers(record, task)
        if not expected:
            continue
        answer_key[item_id] = {
            "task_type": _task_type(task),
            "expected": list(expected),
        }
    return {
        "answer_key": answer_key,
        "practice_item_count": len(answer_key),
    }


async def _evaluate_canonical_revision_practice(
    db: AsyncSession,
    *,
    revision_id: uuid.UUID,
    item_id: str,
    learner_response: Any,
    attempt_number: int,
    allowed_statuses: set[str],
    unavailable_code: str,
) -> PracticeEvaluationResult:
    revision = await db.get(GrammarCanonicalLessonRevision, revision_id)
    if revision is None:
        raise GrammarPracticeEvaluationError("revision_not_found", "Canonical grammar revision was not found")
    if revision.status not in allowed_statuses:
        raise GrammarPracticeEvaluationError(
            unavailable_code,
            f"Revision status cannot be evaluated here; got {revision.status!r}",
        )

    lesson = await db.get(GrammarCanonicalLesson, revision.lesson_id)
    if lesson is None:
        raise GrammarPracticeEvaluationError("canonical_lesson_not_found", "Revision parent lesson was not found")
    if lesson.methodology_version != METHODOLOGY_VERSION:
        raise GrammarPracticeEvaluationError("methodology_mismatch", "Revision uses an unsupported methodology")

    validation = validate_persisted_revision_payload(lesson=lesson, revision=revision)
    if not validation.valid:
        raise GrammarPracticeEvaluationError("revision_payload_invalid", "Revision failed canonical validation")

    student_content = validation.normalized_student_content or revision.student_content_json or {}
    metadata = validation.normalized_server_teaching_metadata or revision.server_teaching_metadata_json or {}
    task = _practice_task_by_id(student_content, item_id)
    if task is None:
        raise GrammarPracticeEvaluationError("unknown_task_id", "Practice item does not belong to this revision")
    record = _metadata_by_item_id(metadata, item_id)
    if record is None:
        raise GrammarPracticeEvaluationError("missing_private_metadata", "Practice item has no private evaluator metadata")

    task_type = _task_type(task)
    if task_type == "open_response":
        return _evaluate_open_response(
            task=task,
            record=record,
            learner_response=learner_response,
            attempt_number=attempt_number,
        )

    expected = _expected_answers(record, task)
    if not expected:
        raise GrammarPracticeEvaluationError("missing_expected_answer", "Practice item cannot be evaluated safely")

    response_norm = _normalize_response(learner_response, task_type=task_type)
    correct = any(_responses_match(response_norm, expected_norm, task_type=task_type) for expected_norm in expected)
    attempt = max(1, min(int(attempt_number or 1), 2))

    if correct:
        return PracticeEvaluationResult(
            correct=True,
            feedback="صحيح. اخترت الشكل المناسب للجملة.",
            hint=None,
            may_continue=True,
            attempt_number=attempt,
        )

    if attempt <= 1:
        return PracticeEvaluationResult(
            correct=False,
            feedback="قريب، لكن راجع شكل الجملة قبل أن تحاول مرة ثانية.",
            hint=_safe_hint(record, expected),
            may_continue=False,
            attempt_number=1,
        )

    return PracticeEvaluationResult(
        correct=False,
        feedback=_answer_reveal_feedback(record, _display_expected_answer(record, task)),
        hint=None,
        may_continue=True,
        attempt_number=2,
    )


def _practice_task_by_id(student_content: dict[str, Any], item_id: str) -> dict[str, Any] | None:
    wanted = str(item_id or "").strip()
    if not wanted:
        return None
    noticing = student_content.get("noticing")
    if isinstance(noticing, dict) and str(noticing.get("id") or "").strip() == wanted:
        return {**noticing, "type": "recognition"}
    for section in ("understanding_checks", "guided_practice"):
        for task in student_content.get(section) or []:
            if isinstance(task, dict) and str(task.get("id") or "").strip() == wanted:
                return task
    return None


def _practice_tasks(student_content: dict[str, Any]) -> list[dict[str, Any]]:
    tasks: list[dict[str, Any]] = []
    for section in ("understanding_checks", "guided_practice"):
        for task in student_content.get(section) or []:
            if isinstance(task, dict):
                tasks.append(task)
    return tasks


def _metadata_by_item_id(metadata: dict[str, Any], item_id: str) -> dict[str, Any] | None:
    wanted = str(item_id or "").strip()
    for section in ("noticing", "understanding_checks", "guided_practice"):
        raw = metadata.get(section)
        records = raw if isinstance(raw, list) else [raw]
        for record in records:
            if isinstance(record, dict) and str(record.get("item_id") or record.get("id") or "").strip() == wanted:
                return record
    return None


def _task_type(task: dict[str, Any]) -> str:
    return str(task.get("type") or "recognition").strip() or "recognition"


def _expected_answers(record: dict[str, Any], task: dict[str, Any]) -> tuple[str, ...]:
    values: list[str] = []
    for key in ("expected_answer", "sample_answer"):
        value = record.get(key)
        if isinstance(value, str) and value.strip():
            values.extend(_split_answer_variants(value))
        elif isinstance(value, list):
            for item in value:
                values.extend(_split_answer_variants(str(item)))

    if _task_type(task) == "recognition":
        values.extend(str(item) for item in task.get("expected_observations") or [] if str(item).strip())

    normalized: list[str] = []
    for value in values:
        if not str(value).strip():
            continue
        normalized.append(_normalize_text(value))
        normalized.append(_normalize_expected(value, task))
    return tuple(dict.fromkeys(item for item in normalized if item))


def _display_expected_answer(record: dict[str, Any], task: dict[str, Any]) -> str:
    for key in ("expected_answer", "sample_answer"):
        value = record.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
        if isinstance(value, list):
            first = next((str(item).strip() for item in value if str(item).strip()), "")
            if first:
                return first
    if _task_type(task) == "recognition":
        first = next((str(item).strip() for item in task.get("expected_observations") or [] if str(item).strip()), "")
        if first:
            return first
    return ""


def _split_answer_variants(value: str) -> list[str]:
    return [part.strip() for part in re.split(r"\s*(?:\|\||؛|;)\s*", str(value or "")) if part.strip()]


def _normalize_expected(value: str, task: dict[str, Any]) -> str:
    task_type = _task_type(task)
    text = _normalize_text(value)
    if task_type == "reorder":
        return _normalize_token_order(value)
    if task_type == "fill_blank":
        sentence = str(task.get("sentence_with_blank") or "")
        if "_____" in sentence and "_____" not in value:
            return _normalize_text(sentence.replace("_____", str(value).strip()))
    return text


def _normalize_response(value: Any, *, task_type: str) -> str:
    if task_type in {"reorder", "sentence_builder"}:
        if isinstance(value, list):
            return _normalize_token_order(" ".join(str(item) for item in value))
        return _normalize_token_order(str(value or ""))
    if isinstance(value, list):
        return _normalize_text(" ".join(str(item) for item in value))
    return _normalize_text(str(value or ""))


def _normalize_text(value: str) -> str:
    text = _WHITESPACE_RE.sub(" ", str(value or "").strip())
    text = _FINAL_PUNCTUATION_RE.sub("", text)
    return text.casefold()


def _normalize_token_order(value: str) -> str:
    text = _FINAL_PUNCTUATION_RE.sub("", str(value or "").strip())
    return " ".join(_WHITESPACE_RE.split(text.casefold()))


def _responses_match(response_norm: str, expected_norm: str, *, task_type: str) -> bool:
    if not response_norm or not expected_norm:
        return False
    if response_norm == expected_norm:
        return True
    if task_type == "recognition":
        response_key = _concept_match_key(response_norm)
        expected_key = _concept_match_key(expected_norm)
        return len(response_key) >= 4 and response_key in expected_key
    return False


def _safe_hint(record: dict[str, Any], expected: tuple[str, ...]) -> str | None:
    text = str(record.get("hint") or "").strip()
    if text and not _reveals_expected_answer(text, expected):
        return _shorten(text, 120)
    return "انظر إلى الفاعل، ثم اختر الشكل المناسب قبل أن تكمل."


def _answer_reveal_feedback(record: dict[str, Any], answer: str) -> str:
    reason = _shorten(str(record.get("feedback_reasoning") or "").strip(), 120)
    visible_answer = str(answer or "").strip()
    if reason:
        return f"الإجابة الصحيحة: {visible_answer}. السبب: {reason}"
    return f"الإجابة الصحيحة: {visible_answer}. راجع الفاعل ثم اختر شكل be المناسب."


def _shorten(value: str, max_length: int) -> str:
    text = _WHITESPACE_RE.sub(" ", value).strip()
    if len(text) <= max_length:
        return text
    return f"{text[:max_length].rstrip()}..."


def _reveals_expected_answer(text: str, expected: tuple[str, ...]) -> bool:
    normalized_hint = _normalize_text(text)
    if any(marker in normalized_hint for marker in ("the answer is", "correct answer", "الإجابة الصحيحة")):
        return True
    return any(answer and answer in normalized_hint for answer in expected)


def _concept_match_key(value: str) -> str:
    return re.sub(r"[^a-z0-9\u0600-\u06ff]+", "", value.casefold())


def _evaluate_open_response(
    *,
    task: dict[str, Any],
    record: dict[str, Any],
    learner_response: Any,
    attempt_number: int,
) -> PracticeEvaluationResult:
    attempt = max(1, min(int(attempt_number or 1), 2))
    text = str(learner_response or "").strip()
    issues = _open_response_issues(text, task)
    correct = not issues
    if correct:
        return PracticeEvaluationResult(
            correct=True,
            feedback="جيد. كتبت معنى شخصيًا واستخدمت فعل be بشكل مناسب.",
            hint=None,
            may_continue=True,
            attempt_number=attempt,
        )
    feedback = "راجع إجابتك: " + " ".join(issues[:2])
    if attempt <= 1:
        return PracticeEvaluationResult(
            correct=False,
            feedback=feedback,
            hint="اكتب جملاً قصيرة تبدأ بفاعل واضح، مثل I am أو I am at.",
            may_continue=False,
            attempt_number=1,
        )
    model = str(record.get("sample_answer") or "").strip()
    if model:
        feedback = f"{feedback} مثال مساعد: {model}"
    return PracticeEvaluationResult(
        correct=False,
        feedback=feedback,
        hint=None,
        may_continue=True,
        attempt_number=2,
    )


def _open_response_issues(text: str, task: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    min_sentences = int(task.get("sentence_count_min") or 2)
    max_sentences = int(task.get("sentence_count_max") or 4)
    sentences = [part.strip() for part in re.split(r"[.!?]+", text) if part.strip()]
    lowered = text.casefold()
    if len(sentences) < min_sentences:
        issues.append(f"اكتب على الأقل {min_sentences} جمل قصيرة.")
    if len(sentences) > max_sentences:
        issues.append(f"اجعل الإجابة بين {min_sentences} و {max_sentences} جمل.")
    if not re.search(r"\b(i|he|she|it|we|they|you)\s+(am|is|are)\b", lowered):
        issues.append("استخدم شكلاً صحيحًا من am/is/are مع الفاعل.")
    if re.search(r"\bi\s+(is|are)\b|\b(he|she|it)\s+(am|are)\b|\b(we|they|you)\s+(am|is)\b", lowered):
        issues.append("راجع تطابق الفاعل مع am/is/are.")
    if re.search(r"\b(was|were|will be|has been|have been|am going|is going|are going)\b", lowered):
        issues.append("ابقَ في حاضر be فقط، بدون ماضي أو مستقبل أو أزمنة أخرى.")
    if not re.search(r"\b(student|teacher|friend|brother|sister|home|school|class|ready|happy|tired|fine|from|at)\b", lowered):
        issues.append("اكتب معنى واضحًا عن من أنت، أين أنت، أو كيف تشعر.")
    return issues
