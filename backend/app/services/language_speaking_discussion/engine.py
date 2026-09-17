"""E3 guided discussion engine — open / submit / advance / resume."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.models.language.progression import LanguageProgression
from app.services.language_educational_package.lifecycle import PackageLifecycleStatus
from app.services.language_educational_package.types import DiscussionStep, EducationalPackage
from app.services.language_speaking_discussion.claude_tutor import (
    call_discussion_opening,
    call_discussion_tutor,
)
from app.services.language_speaking_discussion.storage import (
    discussion_from_payload,
    merge_discussion_into_payload,
)
from app.services.language_speaking_discussion.types import (
    DISCUSSION_RUNTIME_SCHEMA_VERSION,
    DiscussionPhase,
    DiscussionRuntimeState,
    DiscussionTurn,
)
from app.services.language_speaking_educational_package.persistence import (
    get_package_item_by_id,
    package_from_item,
)
from app.services.language_speaking_educational_package.projection import project_package_for_student
from app.services.language_speaking_lesson_runtime.storage import runtime_from_payload as lesson_runtime_from_payload
from app.services.language_speaking_lesson_runtime.types import LessonRuntimeSection

DISCUSSION_RUNTIME_VERSION = DISCUSSION_RUNTIME_SCHEMA_VERSION
EFFECTIVE_MAX_ASSISTANT_TURNS_PER_STEP = 1
MIN_WORDS_TO_ADVANCE_DISCUSSION_STEP = 4


class DiscussionRuntimeError(Exception):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


@dataclass(slots=True)
class DiscussionView:
    state: DiscussionRuntimeState
    package_title: str
    current_step: dict[str, Any] | None
    steps_total: int
    opening_move: str
    closing_move: str
    latest_assistant: dict[str, Any] | None
    provider: str
    package_snippet: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "runtime_version": DISCUSSION_RUNTIME_VERSION,
            "state": self.state.to_dict(),
            "package_title": self.package_title,
            "current_step": self.current_step,
            "steps_total": self.steps_total,
            "opening_move": self.opening_move,
            "closing_move": self.closing_move,
            "latest_assistant": self.latest_assistant,
            "provider": self.provider,
            "package_snippet": self.package_snippet,
        }


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _lock_row(
    db: AsyncSession, *, student_id: int, language_id: int
) -> LanguageProgression | None:
    result = await db.execute(
        select(LanguageProgression)
        .where(
            LanguageProgression.student_id == student_id,
            LanguageProgression.language_id == language_id,
        )
        .with_for_update()
    )
    return result.scalar_one_or_none()


def _assert_frozen(pkg: EducationalPackage) -> None:
    if pkg.status != PackageLifecycleStatus.frozen:
        raise DiscussionRuntimeError("not_frozen", "Learning package is not frozen.")
    if not pkg.discussion.steps:
        raise DiscussionRuntimeError("no_steps", "Frozen package has no discussion steps.")


def _current_step(package: EducationalPackage, state: DiscussionRuntimeState) -> DiscussionStep | None:
    steps = package.discussion.steps
    if not steps:
        return None
    idx = min(max(0, state.step_index), len(steps) - 1)
    return steps[idx]


def _effective_turn_limit(step: DiscussionStep) -> int:
    return max(1, min(int(step.max_assistant_turns or 1), EFFECTIVE_MAX_ASSISTANT_TURNS_PER_STEP))


def _student_answer_is_enough(text: str) -> bool:
    return len((text or "").split()) >= MIN_WORDS_TO_ADVANCE_DISCUSSION_STEP


def _snippet(package: EducationalPackage) -> dict[str, Any]:
    """Student-safe subset — never full teacher notes / fingerprints internals dump beyond ids."""
    proj = project_package_for_student(package)
    spine = package.story_spine
    return {
        "package_id": package.package_id,
        "title": package.input_material.title,
        "discussion": proj.get("discussion"),
        "input_material": {
            "kind": package.input_material.kind.value,
            "title": package.input_material.title,
        },
        "story_spine": {
            "title": spine.title or package.input_material.title,
            "setting": spine.setting,
            "decision_point": spine.decision_point,
            "characters": [c.name for c in spine.characters[:6]],
        },
    }


def _latest_assistant_from_turns(state: DiscussionRuntimeState) -> dict[str, Any] | None:
    """Rebuild ephemeral tutor utterance from persisted turns (needed for resume TTS)."""
    for turn in reversed(state.turns or []):
        if turn.role == "assistant" and (turn.text or "").strip():
            return {"utterance": turn.text.strip(), "correction": None}
    return None


def _view(
    state: DiscussionRuntimeState,
    package: EducationalPackage,
    *,
    provider: str = "",
    latest_assistant: dict[str, Any] | None = None,
) -> DiscussionView:
    step = _current_step(package, state)
    resolved_latest = latest_assistant
    if not (isinstance(resolved_latest, dict) and str(resolved_latest.get("utterance") or "").strip()):
        resolved_latest = _latest_assistant_from_turns(state)
    return DiscussionView(
        state=state,
        package_title=package.input_material.title,
        current_step=step.to_dict() if step else None,
        steps_total=len(package.discussion.steps),
        opening_move=package.discussion.opening_move,
        closing_move=package.discussion.closing_move,
        latest_assistant=resolved_latest,
        provider=provider,
        package_snippet=_snippet(package),
    )


def _save(row: LanguageProgression, state: DiscussionRuntimeState) -> None:
    state.updated_at = _now()
    row.promotion_readiness_json = merge_discussion_into_payload(
        row.promotion_readiness_json, state
    )
    flag_modified(row, "promotion_readiness_json")


def _require_lesson_ready(row: LanguageProgression | None):
    lesson = lesson_runtime_from_payload(row.promotion_readiness_json if row else None)
    if lesson is None:
        raise DiscussionRuntimeError(
            "lesson_required",
            "Complete the prepared lesson before starting discussion.",
        )
    if not lesson.ready_for_discussion and lesson.current_section != LessonRuntimeSection.completed:
        raise DiscussionRuntimeError(
            "lesson_not_ready",
            "Finish the prepared lesson before guided discussion.",
        )
    return lesson


def _require_current_lesson_package(lesson, package_id: str) -> None:
    if not lesson or not lesson.package_id or lesson.package_id != package_id:
        raise DiscussionRuntimeError(
            "stale_runtime",
            "This discussion belongs to an older lesson package.",
        )


async def _load_package(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
    package_id: str,
) -> tuple[Any, EducationalPackage]:
    item = await get_package_item_by_id(
        db, student_id=student_id, language_id=language_id, package_id=package_id
    )
    if item is None:
        raise DiscussionRuntimeError("not_found", "Learning package not found.")
    package = package_from_item(item)
    if package is None:
        raise DiscussionRuntimeError("corrupt", "Learning package payload missing.")
    _assert_frozen(package)
    return item, package


async def _load_first_available_package(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
    package_ids: list[str],
    explicit_package_id: bool,
) -> tuple[Any, EducationalPackage]:
    last_missing = False
    for pid in package_ids:
        try:
            return await _load_package(
                db,
                student_id=student_id,
                language_id=language_id,
                package_id=pid,
            )
        except DiscussionRuntimeError as exc:
            if exc.code == "not_found" and not explicit_package_id:
                last_missing = True
                continue
            raise
    if last_missing:
        raise DiscussionRuntimeError("not_found", "Learning package not found.")
    raise DiscussionRuntimeError("no_package", "No Learning Package for discussion.")


async def open_discussion(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
    package_id: str | None = None,
    force_restart: bool = False,
) -> DiscussionView:
    row = await _lock_row(db, student_id=student_id, language_id=language_id)
    lesson = _require_lesson_ready(row)

    existing = discussion_from_payload(row.promotion_readiness_json if row else None)
    candidates: list[str] = []
    if package_id:
        candidates.append(package_id)
    else:
        candidates.append(lesson.package_id)
    if not candidates:
        raise DiscussionRuntimeError("no_package", "No Learning Package for discussion.")

    item, package = await _load_first_available_package(
        db,
        student_id=student_id,
        language_id=language_id,
        package_ids=candidates,
        explicit_package_id=bool(package_id),
    )
    _require_current_lesson_package(lesson, package.package_id)

    if (
        not force_restart
        and existing
        and existing.package_id == package.package_id
        and existing.content_fingerprint == package.content_fingerprint
        and not existing.completed
    ):
        return _view(existing, package)

    first = package.discussion.steps[0]
    now = _now()
    opening, provider = await call_discussion_opening(package=package, step=first)
    first_utterance = (opening.get("assistant_utterance") or first.prompt).strip() or first.prompt
    state = DiscussionRuntimeState(
        package_id=package.package_id,
        content_item_id=item.id,
        content_fingerprint=package.content_fingerprint,
        phase=DiscussionPhase.waiting_for_student,
        step_index=0,
        current_step_id=first.step_id,
        assistant_turns_used=0,
        answered_step_ids=[],
        corrections_shown=[],
        turns=[
            DiscussionTurn(
                role="system",
                text=package.discussion.opening_move or "Let's discuss what you prepared.",
                step_id=first.step_id,
                created_at=now,
            ),
            DiscussionTurn(
                role="assistant",
                text=first_utterance,
                step_id=first.step_id,
                created_at=now,
            ),
        ],
        completed=False,
        ready_for_alex=False,
        opening_shown=True,
        started_at=now,
        updated_at=now,
    )
    if row is not None:
        _save(row, state)
    return _view(
        state,
        package,
        provider=provider,
        latest_assistant={"utterance": first_utterance, "correction": None},
    )


async def get_discussion_view(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
) -> DiscussionView:
    row = await _lock_row(db, student_id=student_id, language_id=language_id)
    lesson = _require_lesson_ready(row)
    state = discussion_from_payload(row.promotion_readiness_json if row else None)
    if state is None:
        raise DiscussionRuntimeError("no_runtime", "No active discussion.")
    _require_current_lesson_package(lesson, state.package_id)
    _item, package = await _load_package(
        db, student_id=student_id, language_id=language_id, package_id=state.package_id
    )
    if state.content_fingerprint and state.content_fingerprint != package.content_fingerprint:
        raise DiscussionRuntimeError(
            "fingerprint_mismatch",
            "Frozen package changed; reopen discussion.",
        )
    return _view(state, package)


async def submit_discussion_response(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
    student_response: str,
) -> DiscussionView:
    text = (student_response or "").strip()
    if not text:
        raise DiscussionRuntimeError("empty_response", "Student response required.")

    row = await _lock_row(db, student_id=student_id, language_id=language_id)
    if row is None:
        raise DiscussionRuntimeError("no_progression", "No progression row.")
    lesson = _require_lesson_ready(row)
    state = discussion_from_payload(row.promotion_readiness_json)
    if state is None:
        raise DiscussionRuntimeError("no_runtime", "No active discussion.")
    if state.completed:
        raise DiscussionRuntimeError("already_complete", "Discussion already completed.")
    _require_current_lesson_package(lesson, state.package_id)

    _item, package = await _load_package(
        db, student_id=student_id, language_id=language_id, package_id=state.package_id
    )
    step = _current_step(package, state)
    if step is None:
        raise DiscussionRuntimeError("no_steps", "No discussion step.")

    turn_limit = _effective_turn_limit(step)
    if state.assistant_turns_used >= turn_limit:
        # Force advance path — student may call advance
        raise DiscussionRuntimeError(
            "step_turn_limit",
            "Max turns for this question reached — advance to the next question.",
        )

    now = _now()
    state.phase = DiscussionPhase.processing
    state.turns.append(
        DiscussionTurn(role="student", text=text, step_id=step.step_id, created_at=now)
    )
    if step.step_id not in state.answered_step_ids:
        state.answered_step_ids.append(step.step_id)

    tutor, provider = await call_discussion_tutor(
        package=package,
        state=state,
        step=step,
        student_response=text,
    )
    enough_to_advance = _student_answer_is_enough(text)
    if enough_to_advance:
        tutor["request_advance"] = True
    utterance = tutor["assistant_utterance"] or step.prompt
    if enough_to_advance and ("?" in str(utterance or "") or not str(utterance or "").strip()):
        utterance = "Good, that answers this question. Move to the next one when you are ready."
    correction = tutor.get("micro_correction")
    corr_brief = ""
    if isinstance(correction, dict):
        corr_brief = correction.get("brief") or ""
        if correction.get("corrected_form"):
            corr_brief = (corr_brief + " → " + correction["corrected_form"]).strip(" →")
        state.corrections_shown.append(
            {
                "step_id": step.step_id,
                "brief": correction.get("brief") or "",
                "corrected_form": correction.get("corrected_form") or "",
                "shown_at": now,
            }
        )

    state.turns.append(
        DiscussionTurn(
            role="assistant",
            text=utterance,
            step_id=step.step_id,
            correction_brief=corr_brief,
            created_at=now,
        )
    )
    state.assistant_turns_used += 1
    state.phase = DiscussionPhase.assistant_reply

    # Backend may mark advance eligibility; actual step change requires advance API
    # or auto-advance when tutor requests and policy allows.
    auto_advance = bool(tutor.get("request_advance")) and state.assistant_turns_used >= 1
    if auto_advance and enough_to_advance:
        state.phase = DiscussionPhase.next_question

    _save(row, state)
    return _view(
        state,
        package,
        provider=provider,
        latest_assistant={
            "utterance": utterance,
            "correction": correction,
            "can_advance": state.phase == DiscussionPhase.next_question
            or state.assistant_turns_used >= turn_limit,
        },
    )


async def advance_discussion_step(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
) -> DiscussionView:
    row = await _lock_row(db, student_id=student_id, language_id=language_id)
    if row is None:
        raise DiscussionRuntimeError("no_progression", "No progression row.")
    lesson = _require_lesson_ready(row)
    state = discussion_from_payload(row.promotion_readiness_json)
    if state is None:
        raise DiscussionRuntimeError("no_runtime", "No active discussion.")
    _require_current_lesson_package(lesson, state.package_id)
    if state.completed:
        _item, package = await _load_package(
            db, student_id=student_id, language_id=language_id, package_id=state.package_id
        )
        return _view(state, package)

    _item, package = await _load_package(
        db, student_id=student_id, language_id=language_id, package_id=state.package_id
    )
    steps = package.discussion.steps
    step = _current_step(package, state)
    if step is None:
        raise DiscussionRuntimeError("no_steps", "No discussion step.")

    # Require at least one student answer before leaving a step
    if step.step_id not in state.answered_step_ids:
        raise DiscussionRuntimeError(
            "answer_required",
            "Answer the current question before advancing.",
        )

    nxt = state.step_index + 1
    now = _now()
    if nxt >= len(steps):
        state.completed = True
        state.ready_for_alex = True
        state.phase = DiscussionPhase.completed
        state.turns.append(
            DiscussionTurn(
                role="assistant",
                text=package.discussion.closing_move
                or "Great work — you finished this story. You are ready for live speaking in the same situation.",
                step_id=step.step_id,
                created_at=now,
            )
        )
        _save(row, state)
        return _view(
            state,
            package,
            latest_assistant={
                "utterance": package.discussion.closing_move,
                "correction": None,
                "can_advance": False,
            },
        )

    next_step = steps[nxt]
    opening, provider = await call_discussion_opening(package=package, step=next_step)
    next_utterance = (opening.get("assistant_utterance") or next_step.prompt).strip() or next_step.prompt
    state.step_index = nxt
    state.current_step_id = next_step.step_id
    state.assistant_turns_used = 0
    state.phase = DiscussionPhase.waiting_for_student
    state.turns.append(
        DiscussionTurn(
            role="assistant",
            text=next_utterance,
            step_id=next_step.step_id,
            created_at=now,
        )
    )
    _save(row, state)
    return _view(
        state,
        package,
        provider=provider,
        latest_assistant={"utterance": next_utterance, "correction": None, "can_advance": False},
    )
