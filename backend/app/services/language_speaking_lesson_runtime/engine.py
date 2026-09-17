"""E2 lesson runtime engine — open / advance / mark / resume. Read-only on frozen packages."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.models.language.progression import LanguageProgression
from app.services.language_educational_package.lifecycle import PackageLifecycleStatus
from app.services.language_educational_package.types import EducationalPackage
from app.services.language_speaking_educational_package.persistence import (
    get_package_item_by_id,
    package_from_item,
)
from app.services.language_speaking_educational_package.projection import project_package_for_student
from app.services.language_speaking_educational_package.storage_index import (
    elp_index_from_payload,
    merge_elp_index_into_payload,
)
from app.services.language_speaking_lesson_runtime.storage import (
    clear_runtime_from_payload,
    merge_runtime_into_payload,
    runtime_from_payload,
)
from app.services.language_speaking_lesson_runtime.types import (
    LESSON_RUNTIME_SCHEMA_VERSION,
    LessonRuntimeSection,
    LessonRuntimeState,
    next_section,
)

LESSON_RUNTIME_VERSION = LESSON_RUNTIME_SCHEMA_VERSION


class LessonRuntimeError(Exception):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


@dataclass(slots=True)
class LessonRuntimeView:
    state: LessonRuntimeState
    package: dict[str, Any]
    constraints_summary: dict[str, Any]
    section_progress: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "runtime_version": LESSON_RUNTIME_VERSION,
            "state": self.state.to_dict(),
            "package": self.package,
            "constraints_summary": self.constraints_summary,
            "section_progress": self.section_progress,
        }


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _current_runtime_authoring_day() -> str:
    try:
        return datetime.now(ZoneInfo("Asia/Damascus")).date().isoformat()
    except Exception:  # noqa: BLE001 - timezone data may be unavailable in CI
        return datetime.now(timezone.utc).date().isoformat()


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
        raise LessonRuntimeError("not_frozen", "Learning package is not frozen.")


def _official_cefr_from_row(row: LanguageProgression | None) -> str:
    if row is None:
        return ""
    val = getattr(row, "official_speaking_cefr", None)
    return (val.value if hasattr(val, "value") else str(val or "")).upper()


def _build_constraints_summary(item_body: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(item_body, dict):
        return {}
    raw = item_body.get("package_constraints")
    if not isinstance(raw, dict):
        return {}
    return {
        "official_cefr": raw.get("official_cefr"),
        "learning_stage": raw.get("learning_stage"),
        "mission_id": raw.get("mission_id"),
        "mission_kind": raw.get("mission_kind"),
        "learning_focus": raw.get("learning_focus"),
        "objectives": list(raw.get("objectives") or []),
        "lesson_length_band": raw.get("lesson_length_band"),
        "scenario_type": raw.get("scenario_type"),
        "difficulty": raw.get("difficulty"),
        "schema_version": raw.get("schema_version"),
        "authoring_day": raw.get("authoring_day"),
        "daily_story_key": raw.get("daily_story_key"),
        "daily_story_seed": raw.get("daily_story_seed"),
    }


def _package_matches_current_runtime_context(
    row: LanguageProgression | None,
    constraints_summary: dict[str, Any],
) -> bool:
    official = _official_cefr_from_row(row)
    package_cefr = str(constraints_summary.get("official_cefr") or "").upper()
    if official and package_cefr != official:
        return False
    if not str(constraints_summary.get("daily_story_key") or "").strip():
        return False
    authoring_day = str(constraints_summary.get("authoring_day") or "").strip()
    if authoring_day != _current_runtime_authoring_day():
        return False
    return True


def _clear_stale_package_runtime_references(
    payload: dict[str, Any] | None,
    *,
    package_id: str,
    constraints_fingerprint: str = "",
    mission_id: str = "",
) -> dict[str, Any]:
    out = clear_runtime_from_payload(payload)
    index = elp_index_from_payload(out)
    index["order"] = [str(pid) for pid in (index.get("order") or []) if str(pid) != package_id]
    by_id = dict(index.get("by_package_id") or {})
    by_id.pop(package_id, None)
    index["by_package_id"] = by_id
    index["by_fingerprint"] = {
        str(fp): str(pid)
        for fp, pid in dict(index.get("by_fingerprint") or {}).items()
        if str(pid) != package_id and (not constraints_fingerprint or str(fp) != constraints_fingerprint)
    }
    index["active_by_mission"] = {
        str(mid): str(pid)
        for mid, pid in dict(index.get("active_by_mission") or {}).items()
        if str(pid) != package_id and (not mission_id or str(mid) != mission_id)
    }
    return merge_elp_index_into_payload(out, index)


def _section_progress(state: LessonRuntimeState, package: EducationalPackage) -> dict[str, Any]:
    sections = [
        LessonRuntimeSection.introduction.value,
        LessonRuntimeSection.reading.value,
        LessonRuntimeSection.vocabulary.value,
        LessonRuntimeSection.teaching.value,
        LessonRuntimeSection.mini_practice.value,
        LessonRuntimeSection.completed.value,
    ]
    done = set(state.completed_sections)
    return {
        "sections": sections,
        "current": state.current_section.value,
        "completed": list(state.completed_sections),
        "percent": int(100 * len(done.intersection(sections[:-1])) / max(1, len(sections) - 1)),
        "vocabulary_total": len(package.vocabulary_in_context.entries),
        "vocabulary_viewed": len(state.viewed_vocabulary_ids),
        "teaching_total": len(package.teaching_blocks_authored),
        "teaching_completed": len(state.completed_teaching_block_ids),
        "mini_practice_prep_done": state.mini_practice_prep_done,
        "ready_for_discussion": state.ready_for_discussion,
    }


def _candidate_package_ids(
    payload: dict[str, Any] | None,
    package_id: str | None,
) -> list[str]:
    if package_id:
        return [package_id]
    candidates: list[str] = []
    existing = runtime_from_payload(payload)
    if existing and existing.package_id:
        candidates.append(existing.package_id)
    index = elp_index_from_payload(payload)
    for pid in reversed(index.get("order") or []):
        value = str(pid)
        if value and value not in candidates:
            candidates.append(value)
    return candidates


def _view(
    state: LessonRuntimeState,
    package: EducationalPackage,
    constraints_summary: dict[str, Any],
) -> LessonRuntimeView:
    return LessonRuntimeView(
        state=state,
        package=project_package_for_student(package),
        constraints_summary=constraints_summary,
        section_progress=_section_progress(state, package),
    )


async def open_lesson_runtime(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
    package_id: str | None = None,
    force_restart: bool = False,
) -> LessonRuntimeView:
    row = await _lock_row(db, student_id=student_id, language_id=language_id)
    payload = row.promotion_readiness_json if row else None
    candidates = _candidate_package_ids(payload, package_id)
    if not candidates:
        raise LessonRuntimeError("no_package", "No Learning Package available to open.")

    item = None
    stale_seen = False
    for pid in candidates:
        item = await get_package_item_by_id(
            db, student_id=student_id, language_id=language_id, package_id=pid
        )
        if item is None:
            continue
        body = item.body_json if isinstance(item.body_json, dict) else {}
        summary = _build_constraints_summary(body)
        if row is not None and not _package_matches_current_runtime_context(row, summary):
            stale_seen = True
            row.promotion_readiness_json = _clear_stale_package_runtime_references(
                row.promotion_readiness_json,
                package_id=pid,
                constraints_fingerprint=str(body.get("constraints_fingerprint") or ""),
                mission_id=str(summary.get("mission_id") or ""),
            )
            flag_modified(row, "promotion_readiness_json")
            item = None
            continue
        break
    if item is None:
        if stale_seen:
            raise LessonRuntimeError("no_package", "No Learning Package available to open.")
        if package_id:
            raise LessonRuntimeError("not_found", "Learning package not found.")
        raise LessonRuntimeError("no_package", "No Learning Package available to open.")
    package = package_from_item(item)
    if package is None:
        raise LessonRuntimeError("corrupt", "Learning package payload missing.")
    _assert_frozen(package)

    body = item.body_json if isinstance(item.body_json, dict) else {}
    summary = _build_constraints_summary(body)
    # Prove immutability: never write back to content item
    existing = runtime_from_payload(row.promotion_readiness_json if row else None)
    now = _now()

    if (
        not force_restart
        and existing
        and existing.package_id == package.package_id
        and existing.content_fingerprint == package.content_fingerprint
    ):
        return _view(existing, package, summary)

    state = LessonRuntimeState(
        package_id=package.package_id,
        content_item_id=item.id,
        constraints_fingerprint=package.constraints_fingerprint,
        content_fingerprint=package.content_fingerprint,
        current_section=LessonRuntimeSection.introduction,
        completed_sections=[],
        viewed_vocabulary_ids=[],
        completed_teaching_block_ids=[],
        mini_practice_prep_done=False,
        ready_for_discussion=False,
        position_hint="introduction",
        started_at=now,
        updated_at=now,
    )
    if row is not None:
        row.promotion_readiness_json = merge_runtime_into_payload(
            row.promotion_readiness_json, state
        )
        flag_modified(row, "promotion_readiness_json")
    return _view(state, package, summary)


async def get_lesson_runtime_view(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
) -> LessonRuntimeView:
    row = await _lock_row(db, student_id=student_id, language_id=language_id)
    state = runtime_from_payload(row.promotion_readiness_json if row else None)
    if state is None:
        raise LessonRuntimeError("no_runtime", "No active lesson runtime.")
    item = await get_package_item_by_id(
        db,
        student_id=student_id,
        language_id=language_id,
        package_id=state.package_id,
    )
    if item is None:
        raise LessonRuntimeError("not_found", "Learning package not found.")
    package = package_from_item(item)
    if package is None:
        raise LessonRuntimeError("corrupt", "Learning package payload missing.")
    _assert_frozen(package)
    if state.content_fingerprint and state.content_fingerprint != package.content_fingerprint:
        raise LessonRuntimeError(
            "fingerprint_mismatch",
            "Frozen package changed; reopen the lesson.",
        )
    body = item.body_json if isinstance(item.body_json, dict) else {}
    summary = _build_constraints_summary(body)
    if row is not None and not _package_matches_current_runtime_context(row, summary):
        row.promotion_readiness_json = _clear_stale_package_runtime_references(
            row.promotion_readiness_json,
            package_id=state.package_id,
            constraints_fingerprint=str(body.get("constraints_fingerprint") or ""),
            mission_id=str(summary.get("mission_id") or ""),
        )
        flag_modified(row, "promotion_readiness_json")
        raise LessonRuntimeError("no_runtime", "No active lesson runtime.")
    return _view(state, package, summary)


async def _load_mutable(
    db: AsyncSession, *, student_id: int, language_id: int
) -> tuple[LanguageProgression, LessonRuntimeState, EducationalPackage, dict[str, Any]]:
    row = await _lock_row(db, student_id=student_id, language_id=language_id)
    if row is None:
        raise LessonRuntimeError("no_progression", "No progression row.")
    state = runtime_from_payload(row.promotion_readiness_json)
    if state is None:
        raise LessonRuntimeError("no_runtime", "No active lesson runtime.")
    item = await get_package_item_by_id(
        db,
        student_id=student_id,
        language_id=language_id,
        package_id=state.package_id,
    )
    if item is None:
        raise LessonRuntimeError("not_found", "Learning package not found.")
    package = package_from_item(item)
    if package is None:
        raise LessonRuntimeError("corrupt", "Learning package payload missing.")
    _assert_frozen(package)
    body = item.body_json if isinstance(item.body_json, dict) else {}
    summary = _build_constraints_summary(body)
    if not _package_matches_current_runtime_context(row, summary):
        row.promotion_readiness_json = _clear_stale_package_runtime_references(
            row.promotion_readiness_json,
            package_id=state.package_id,
            constraints_fingerprint=str(body.get("constraints_fingerprint") or ""),
            mission_id=str(summary.get("mission_id") or ""),
        )
        flag_modified(row, "promotion_readiness_json")
        raise LessonRuntimeError("no_runtime", "No active lesson runtime.")
    return row, state, package, summary


def _save(
    row: LanguageProgression, state: LessonRuntimeState
) -> None:
    state.updated_at = _now()
    row.promotion_readiness_json = merge_runtime_into_payload(
        row.promotion_readiness_json, state
    )
    flag_modified(row, "promotion_readiness_json")


async def advance_lesson_section(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
) -> LessonRuntimeView:
    row, state, package, summary = await _load_mutable(
        db, student_id=student_id, language_id=language_id
    )
    current = state.current_section
    if current == LessonRuntimeSection.completed:
        return _view(state, package, summary)

    # Gate mini_practice → completed: prep must be marked done
    nxt = next_section(current)
    if nxt is None:
        return _view(state, package, summary)

    if (
        current == LessonRuntimeSection.mini_practice
        and nxt == LessonRuntimeSection.completed
        and not state.mini_practice_prep_done
    ):
        raise LessonRuntimeError(
            "mini_prep_required",
            "Complete mini speaking preparation before finishing the lesson.",
        )

    if current.value not in state.completed_sections and current != LessonRuntimeSection.not_started:
        state.completed_sections.append(current.value)

    state.current_section = nxt
    state.position_hint = nxt.value
    if nxt == LessonRuntimeSection.completed:
        if nxt.value not in state.completed_sections:
            state.completed_sections.append(nxt.value)
        state.ready_for_discussion = True

    _save(row, state)
    return _view(state, package, summary)


async def mark_vocabulary_viewed(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
    vocabulary_id: str,
) -> LessonRuntimeView:
    row, state, package, summary = await _load_mutable(
        db, student_id=student_id, language_id=language_id
    )
    allowed = {e.vocabulary_id for e in package.vocabulary_in_context.entries}
    if vocabulary_id not in allowed:
        raise LessonRuntimeError("unknown_vocab", "Vocabulary id not in frozen package.")
    if vocabulary_id not in state.viewed_vocabulary_ids:
        state.viewed_vocabulary_ids.append(vocabulary_id)
    _save(row, state)
    return _view(state, package, summary)


async def mark_teaching_block_viewed(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
    block_id: str,
) -> LessonRuntimeView:
    row, state, package, summary = await _load_mutable(
        db, student_id=student_id, language_id=language_id
    )
    allowed = {b.block_id for b in package.teaching_blocks_authored}
    if block_id not in allowed:
        raise LessonRuntimeError("unknown_block", "Teaching block id not in frozen package.")
    if block_id not in state.completed_teaching_block_ids:
        state.completed_teaching_block_ids.append(block_id)
    _save(row, state)
    return _view(state, package, summary)


async def mark_mini_prep_complete(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
) -> LessonRuntimeView:
    """Preparation only — no recording, STT, or evaluation."""
    row, state, package, summary = await _load_mutable(
        db, student_id=student_id, language_id=language_id
    )
    state.mini_practice_prep_done = True
    _save(row, state)
    return _view(state, package, summary)
