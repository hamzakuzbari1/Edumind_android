"""Server-attested activity completion (Wave D P0-1).

Client may supply only activity_session_id + evaluation answers/payload.
Server reconstructs grammar_id, skill, score, lesson_id from the session + stamp.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.language_grammar.enums import GrammarEvidenceSourceSkill
from app.services.language_grammar_integrity.errors import GrammarIntegrityError
from app.services.language_grammar_integrity.ledger import try_append_evidence
from app.services.language_grammar_integrity.sessions import (
    load_owned_open_session,
    mark_session_completed,
)
from app.services.language_grammar_pipeline.completion import (
    ActivityCompletionRequest,
    ActivityCompletionResult,
    apply_activity_completion_async,
)


@dataclass(frozen=True, slots=True)
class AttestedCompletionRequest:
    student_id: int
    activity_session_id: str
    language_id: int = 1
    # Client answers / draft text — never grammar_id or score.
    answers: dict[str, Any] | list[Any] | None = None
    response_text: str = ""
    # Optional server-side score override from a trusted evaluation step already run.
    # Callers must compute this on the server; never pass client score.
    server_score: float | None = None
    server_confidence: float | None = None


@dataclass(frozen=True, slots=True)
class ResolvedActivityScore:
    score: float
    attempt_count: int = 1
    correct_count: int | None = None


def _normalize_answer_value(value: Any) -> str:
    if isinstance(value, list):
        value = " ".join(str(item) for item in value)
    return " ".join(str(value or "").strip().rstrip(" .!?،,;:").casefold().split())


def _score_from_answers(
    session_payload: dict[str, Any],
    answers: dict[str, Any] | list[Any] | None,
) -> ResolvedActivityScore | None:
    """Score MCQ-style answers against server-stored answer key when present."""
    if not isinstance(answers, dict):
        return None
    key = session_payload.get("answer_key")
    if not isinstance(key, dict) or not key:
        return None
    total = 0
    correct = 0
    for qid, expected in key.items():
        total += 1
        resp = answers.get(qid) or answers.get(str(qid)) or {}
        if isinstance(resp, dict):
            chosen = resp.get("choice_index", resp.get("answer"))
        else:
            chosen = resp
        expected_values: list[Any]
        if isinstance(expected, dict):
            expected_values = list(expected.get("expected") or [])
        elif isinstance(expected, list):
            expected_values = expected
        else:
            expected_values = [expected]
        chosen_norm = _normalize_answer_value(chosen)
        expected_norms = {_normalize_answer_value(item) for item in expected_values}
        if chosen_norm and chosen_norm in expected_norms:
            correct += 1
    if total <= 0:
        return None
    return ResolvedActivityScore(
        score=100.0 * (correct / total),
        attempt_count=total,
        correct_count=correct,
    )


def _score_vocabulary_blanks(
    session_payload: dict[str, Any],
    answers: dict[str, Any] | list[Any] | None,
) -> ResolvedActivityScore | None:
    mapping = session_payload.get("blanks_mapping")
    if not isinstance(mapping, dict) or not mapping:
        return None
    # answers: list[{blank, word}] or dict blank->word
    submitted: dict[str, str] = {}
    if isinstance(answers, dict):
        for k, v in answers.items():
            if isinstance(v, dict):
                submitted[str(k)] = str(v.get("word") or v.get("answer") or "")
            else:
                submitted[str(k)] = str(v or "")
    elif isinstance(answers, list):
        for item in answers:
            if not isinstance(item, dict):
                continue
            blank = str(item.get("blank") or item.get("id") or "")
            word = str(item.get("word") or item.get("answer") or "")
            if blank:
                submitted[blank] = word
    total = len(mapping)
    correct = 0
    for blank, expected in mapping.items():
        got = (submitted.get(str(blank)) or submitted.get(str(blank).strip("[]")) or "").strip().lower()
        if got == str(expected).strip().lower():
            correct += 1
    if total <= 0:
        return None
    return ResolvedActivityScore(score=100.0 * (correct / total), attempt_count=total, correct_count=correct)


async def resolve_server_score(
    *,
    skill: str,
    server_payload: dict[str, Any],
    answers: dict[str, Any] | list[Any] | None,
    response_text: str,
    server_score: float | None,
) -> ResolvedActivityScore:
    if server_score is not None:
        score = max(0.0, min(100.0, float(server_score)))
        return ResolvedActivityScore(score=score, correct_count=1 if score >= 70.0 else 0)
    if skill == "vocabulary":
        scored = _score_vocabulary_blanks(server_payload, answers)
        if scored is not None:
            return scored
    scored = _score_from_answers(server_payload, answers)
    if scored is not None:
        if skill in {"grammar_lesson", "grammar"}:
            if scored.attempt_count < 14 or int(scored.correct_count or 0) < scored.attempt_count:
                raise GrammarIntegrityError(
                    "grammar_practice_not_complete",
                    "Complete all Grammar practice items correctly before finishing",
                )
        return scored
    if skill in {"grammar_lesson", "grammar"}:
        expected_count = int(server_payload.get("practice_item_count") or 0)
        if expected_count < 14:
            raise GrammarIntegrityError(
                "grammar_practice_key_unavailable",
                "Grammar lesson completion requires a full server answer key",
            )
        raise GrammarIntegrityError(
            "grammar_practice_answers_required",
            "Complete all Grammar practice items correctly before finishing",
        )
    # Writing: length heuristic only when min_words present (never trust client score).
    if skill == "writing" and response_text.strip():
        min_words = int(server_payload.get("min_words") or 20)
        words = len(response_text.split())
        if words >= min_words:
            return ResolvedActivityScore(score=75.0, correct_count=1)
        score = max(20.0, 100.0 * (words / max(1, min_words)))
        return ResolvedActivityScore(score=score, correct_count=1 if score >= 70.0 else 0)
    # Speaking finalize: server may pass server_score; otherwise require it.
    if skill == "speaking" and server_score is None:
        raise GrammarIntegrityError(
            "score_unavailable",
            "Speaking completion requires server-computed score",
        )
    raise GrammarIntegrityError(
        "score_unavailable",
        "Server could not determine a score from session evaluation data",
    )


async def complete_attested_activity(
    db: AsyncSession,
    request: AttestedCompletionRequest,
) -> ActivityCompletionResult:
    """Validate session+stamp, score server-side, ledger append, then Wave B mastery path."""
    session = await load_owned_open_session(
        db,
        activity_session_id=request.activity_session_id,
        student_id=request.student_id,
    )
    if int(session.language_id) != int(request.language_id):
        raise GrammarIntegrityError("language_mismatch", "Activity session language mismatch")

    payload = dict(session.server_payload_json or {})
    resolved_score = await resolve_server_score(
        skill=session.skill,
        server_payload=payload,
        answers=request.answers if isinstance(request.answers, (dict, list)) else None,
        response_text=request.response_text or "",
        server_score=request.server_score,
    )
    score = resolved_score.score
    confidence = (
        float(request.server_confidence)
        if request.server_confidence is not None
        else max(0.35, min(1.0, score / 100.0))
    )

    observation_id = f"ev_{session.id}_{session.grammar_id}"
    ledger_result = await try_append_evidence(
        db,
        observation_id=observation_id,
        student_id=session.student_id,
        language_id=session.language_id,
        grammar_id=session.grammar_id,
        skill=session.skill,
        score=score,
        confidence=confidence,
        activity_session_id=session.id,
        lesson_id=session.lesson_id,
        activity_type=session.activity_type,
        curriculum_version=session.curriculum_version,
    )
    if ledger_result == "duplicate":
        # Replay: do not re-score mastery; return current state via a no-op completion path.
        raise GrammarIntegrityError(
            "duplicate_observation",
            "This activity completion was already recorded",
        )

    try:
        skill = GrammarEvidenceSourceSkill(session.skill)
    except ValueError as exc:
        raise GrammarIntegrityError("invalid_skill", f"Unsupported skill: {session.skill}") from exc

    result = await apply_activity_completion_async(
        db,
        ActivityCompletionRequest(
            student_id=session.student_id,
            language_id=session.language_id,
            grammar_id=session.grammar_id,
            skill=skill,
            score=score,
            activity_id=str(session.id),
            activity_type=session.activity_type or skill.value,
            lesson_id=session.lesson_id,
            confidence=confidence,
            context=f"attested:{session.skill}:{session.id}",
            observation_id=observation_id,
            attempt_count=resolved_score.attempt_count,
            correct_count=resolved_score.correct_count,
        ),
    )
    await mark_session_completed(db, session=session)
    return result


async def issue_and_stamp_for_context(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
    grammar_ctx,
    skill: GrammarEvidenceSourceSkill | str,
    activity_type: str = "",
    lesson_id: str = "",
    content_item_id: int | None = None,
    server_payload: dict[str, Any] | None = None,
):
    """Convenience wrapper used by skill generate paths."""
    from app.services.language_grammar_integrity.sessions import issue_activity_session

    if grammar_ctx is None:
        raise GrammarIntegrityError(
            "resolver_empty",
            "Grammar resolver returned no target — generation fail-closed",
        )
    return await issue_activity_session(
        db,
        student_id=student_id,
        language_id=language_id,
        grammar_ctx=grammar_ctx,
        skill=skill,
        activity_type=activity_type,
        lesson_id=lesson_id,
        content_item_id=content_item_id,
        server_payload=server_payload,
    )
