"""Speaking attempt lineage runtime (S11).

Execution-lineage only — never mastery, CEFR, stage, or promotion authority.
References ``evaluation_id`` (S7) and ``live_turn_id`` (live_conversation); does not
mint them. One authoritative start/resume boundary; EVI granularity is one live task
execution = one attempt with many turns/evaluations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum

from app.services.language_speaking_lesson_planner.identity import (
    new_attempt_id,
    should_start_new_attempt,
)
from app.services.language_speaking_lesson_planner.mission_task_resolver import (
    SpeakingRuntimeTaskResolution,
)
from app.services.language_speaking_lesson_planner.mission_types import SpeakingMissionOutcome

ATTEMPT_LINEAGE_SCHEMA_VERSION = "11.0.0"


class AmbiguousActiveAttemptError(Exception):
    """S14 C-7 — persisted lineage has >1 status=active attempt (fail closed).

    Raised at the runtime boundary so ambiguous execution state never reaches
    Alex context, live-turn attachment, or S8 mutation. Never silently resolved.
    """

    def __init__(self, session_id: str, active_ids: tuple[str, ...]) -> None:
        super().__init__(f"ambiguous_active_attempt:{session_id}:{','.join(active_ids)}")
        self.session_id = session_id
        self.active_ids = active_ids


class SpeakingAttemptStatus(StrEnum):
    """Execution status of one task attempt (not a learning/outcome decision)."""

    active = "active"
    completed = "completed"
    failed = "failed"
    abandoned = "abandoned"


_TERMINAL = frozenset(
    {
        SpeakingAttemptStatus.completed,
        SpeakingAttemptStatus.failed,
        SpeakingAttemptStatus.abandoned,
    }
)


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


@dataclass
class SpeakingTaskAttempt:
    """One student execution of one task (durable lineage unit)."""

    attempt_id: str
    session_id: str
    blueprint_id: str
    mission_id: str
    task_id: str
    attempt_number: int
    status: SpeakingAttemptStatus
    started_at: str
    completed_at: str = ""
    live_session_id: str = ""
    retry_of_attempt_id: str = ""
    evaluation_ids: list[str] = field(default_factory=list)
    live_turn_ids: list[str] = field(default_factory=list)

    @property
    def is_terminal(self) -> bool:
        return self.status in _TERMINAL

    @property
    def is_retry(self) -> bool:
        return bool(self.retry_of_attempt_id)

    def attach_turn(self, live_turn_id: str) -> bool:
        """Append live_turn_id idempotently. Returns True if newly attached."""
        if not live_turn_id or live_turn_id in self.live_turn_ids:
            return False
        self.live_turn_ids.append(live_turn_id)
        return True

    def attach_evaluation(self, evaluation_id: str) -> bool:
        """Append evaluation_id idempotently. Returns True if newly attached."""
        if not evaluation_id or evaluation_id in self.evaluation_ids:
            return False
        self.evaluation_ids.append(evaluation_id)
        return True

    def to_dict(self) -> dict[str, object]:
        return {
            "attempt_id": self.attempt_id,
            "session_id": self.session_id,
            "blueprint_id": self.blueprint_id,
            "mission_id": self.mission_id,
            "task_id": self.task_id,
            "attempt_number": self.attempt_number,
            "status": self.status.value,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "live_session_id": self.live_session_id,
            "retry_of_attempt_id": self.retry_of_attempt_id,
            "evaluation_ids": list(self.evaluation_ids),
            "live_turn_ids": list(self.live_turn_ids),
        }

    @classmethod
    def from_dict(cls, raw: dict[str, object] | None) -> SpeakingTaskAttempt | None:
        if not isinstance(raw, dict) or not raw.get("attempt_id"):
            return None
        return cls(
            attempt_id=str(raw["attempt_id"]),
            session_id=str(raw.get("session_id", "")),
            blueprint_id=str(raw.get("blueprint_id", "")),
            mission_id=str(raw.get("mission_id", "")),
            task_id=str(raw.get("task_id", "")),
            attempt_number=int(raw.get("attempt_number", 1)),
            status=SpeakingAttemptStatus(str(raw.get("status", "active"))),
            started_at=str(raw.get("started_at", "")),
            completed_at=str(raw.get("completed_at", "")),
            live_session_id=str(raw.get("live_session_id", "")),
            retry_of_attempt_id=str(raw.get("retry_of_attempt_id", "")),
            evaluation_ids=[str(x) for x in (raw.get("evaluation_ids") or [])],
            live_turn_ids=[str(x) for x in (raw.get("live_turn_ids") or [])],
        )


@dataclass
class SpeakingSessionAttemptLineage:
    """Session-scoped attempt lineage container (JSONB-persistable)."""

    session_id: str
    active_attempt_id: str = ""
    attempts: list[SpeakingTaskAttempt] = field(default_factory=list)
    schema_version: str = ATTEMPT_LINEAGE_SCHEMA_VERSION

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "session_id": self.session_id,
            "active_attempt_id": self.active_attempt_id,
            "attempts": [a.to_dict() for a in self.attempts],
        }

    @classmethod
    def from_dict(cls, raw: dict[str, object] | None) -> SpeakingSessionAttemptLineage | None:
        if not isinstance(raw, dict) or not raw.get("session_id"):
            return None
        attempts: list[SpeakingTaskAttempt] = []
        for item in raw.get("attempts") or []:
            if not isinstance(item, dict):
                continue
            att = SpeakingTaskAttempt.from_dict(item)
            if att is not None:
                attempts.append(att)
        return cls(
            session_id=str(raw["session_id"]),
            active_attempt_id=str(raw.get("active_attempt_id", "")),
            attempts=attempts,
            schema_version=str(raw.get("schema_version", ATTEMPT_LINEAGE_SCHEMA_VERSION)),
        )

    @staticmethod
    def empty_for_session(session_id: str) -> SpeakingSessionAttemptLineage:
        return SpeakingSessionAttemptLineage(session_id=session_id)


# ---------------------------------------------------------------------------
# Queries (PART 9)
# ---------------------------------------------------------------------------


def get_attempt(
    lineage: SpeakingSessionAttemptLineage,
    attempt_id: str,
) -> SpeakingTaskAttempt | None:
    for att in lineage.attempts:
        if att.attempt_id == attempt_id:
            return att
    return None


def find_active_attempts(
    lineage: SpeakingSessionAttemptLineage,
) -> tuple[SpeakingTaskAttempt, ...]:
    """All attempts persisted with status=active (used for C-7 integrity checks)."""
    return tuple(a for a in lineage.attempts if a.status == SpeakingAttemptStatus.active)


def assert_active_attempt_integrity(lineage: SpeakingSessionAttemptLineage) -> None:
    """S14 C-7 — fail closed when persisted lineage has >1 active attempt.

    Deterministic: detects the malformed state and never silently chooses one.
    """
    actives = find_active_attempts(lineage)
    if len(actives) > 1:
        raise AmbiguousActiveAttemptError(
            lineage.session_id,
            tuple(a.attempt_id for a in actives),
        )


def get_active_attempt(
    lineage: SpeakingSessionAttemptLineage,
) -> SpeakingTaskAttempt | None:
    # C-7: never resolve an active attempt from ambiguous lineage.
    assert_active_attempt_integrity(lineage)
    if not lineage.active_attempt_id:
        return None
    att = get_attempt(lineage, lineage.active_attempt_id)
    if att is None or att.is_terminal:
        return None
    return att


def attempts_for_task(
    lineage: SpeakingSessionAttemptLineage,
    task_id: str,
) -> tuple[SpeakingTaskAttempt, ...]:
    return tuple(
        sorted(
            (a for a in lineage.attempts if a.task_id == task_id),
            key=lambda a: a.attempt_number,
        )
    )


def latest_attempt_for_task(
    lineage: SpeakingSessionAttemptLineage,
    task_id: str,
) -> SpeakingTaskAttempt | None:
    task_attempts = attempts_for_task(lineage, task_id)
    return task_attempts[-1] if task_attempts else None


def retry_chain_for_attempt(
    lineage: SpeakingSessionAttemptLineage,
    attempt_id: str,
) -> tuple[SpeakingTaskAttempt, ...]:
    """Return the attempt-based retry chain ending at ``attempt_id`` (oldest → newest).

    Detects malformed cycles and raises ValueError.
    """
    chain_rev: list[SpeakingTaskAttempt] = []
    seen: set[str] = set()
    current_id = attempt_id
    while current_id:
        if current_id in seen:
            raise ValueError(f"malformed_retry_cycle:{current_id}")
        seen.add(current_id)
        att = get_attempt(lineage, current_id)
        if att is None:
            raise ValueError(f"missing_attempt_in_retry_chain:{current_id}")
        chain_rev.append(att)
        current_id = att.retry_of_attempt_id
    return tuple(reversed(chain_rev))


# ---------------------------------------------------------------------------
# Attempt creation / resume (PART 4) — single authoritative boundary
# ---------------------------------------------------------------------------


def start_or_resume_attempt(
    lineage: SpeakingSessionAttemptLineage,
    resolution: SpeakingRuntimeTaskResolution,
    *,
    session_id: str,
    blueprint_id: str,
    is_resume: bool = False,
    live_session_id: str = "",
    force_new: bool = False,
    now: str | None = None,
) -> SpeakingTaskAttempt:
    """Single authoritative decide-reuse-vs-fresh boundary.

    A. First execution → fresh attempt_id, attempt_number=1, retry_of=None
    B. Resume/reconnect of SAME active execution → reuse attempt_id/number/live_session_id
    C. Retry after terminal → fresh, attempt_number=prev+1, retry_of=prev
    D. Different task → fresh for that task lineage
    """
    if not resolution.is_task or not resolution.task_id:
        raise ValueError("cannot_start_attempt_without_executable_task")

    ts = now or _now_iso()
    task_id = resolution.task_id
    latest = latest_attempt_for_task(lineage, task_id)
    active = get_active_attempt(lineage)

    # B — Resume: same active attempt for this task, reconnect of same logical execution.
    if (
        not force_new
        and is_resume
        and active is not None
        and active.task_id == task_id
        and not should_start_new_attempt(is_resume=True, previous_attempt_completed=False)
    ):
        if live_session_id and not active.live_session_id:
            active.live_session_id = live_session_id
        lineage.active_attempt_id = active.attempt_id
        return active

    # Also reuse without explicit is_resume if there is already an active attempt for this task
    # and caller did not force a new one (turn attachment path within same conversation).
    if (
        not force_new
        and active is not None
        and active.task_id == task_id
        and not should_start_new_attempt(is_resume=True, previous_attempt_completed=False)
    ):
        # Treat continuing an in-flight attempt as reuse (EVI multi-turn).
        if live_session_id and not active.live_session_id:
            active.live_session_id = live_session_id
        lineage.active_attempt_id = active.attempt_id
        return active

    # A / C / D — mint a fresh attempt.
    # If another attempt is still marked active (different task, or force_new), abandon it.
    if active is not None and (active.task_id != task_id or force_new):
        if not active.is_terminal:
            active.status = SpeakingAttemptStatus.abandoned
            active.completed_at = ts
        lineage.active_attempt_id = ""

    previous_completed = latest is not None and latest.status in (
        SpeakingAttemptStatus.completed,
        SpeakingAttemptStatus.failed,
    )
    attempt_number = 1
    retry_of = ""
    if latest is not None:
        attempt_number = latest.attempt_number + 1
        # C — retry lineage only after failed/completed — not after abandon.
        if latest.status in (SpeakingAttemptStatus.completed, SpeakingAttemptStatus.failed):
            retry_of = latest.attempt_id

    attempt = SpeakingTaskAttempt(
        attempt_id=new_attempt_id(task_id),
        session_id=session_id,
        blueprint_id=blueprint_id,
        mission_id=resolution.mission_id,
        task_id=task_id,
        attempt_number=attempt_number,
        status=SpeakingAttemptStatus.active,
        started_at=ts,
        live_session_id=live_session_id or (
            latest.live_session_id if latest and not previous_completed and latest.task_id == task_id else ""
        ),
        retry_of_attempt_id=retry_of,
    )
    lineage.attempts.append(attempt)
    lineage.active_attempt_id = attempt.attempt_id
    lineage.session_id = session_id
    return attempt


# ---------------------------------------------------------------------------
# Outcome → attempt state (PART 7)
# ---------------------------------------------------------------------------


def apply_outcome_to_attempt(
    attempt: SpeakingTaskAttempt,
    outcome: SpeakingMissionOutcome,
    *,
    now: str | None = None,
) -> SpeakingTaskAttempt:
    """Map a mission flow outcome onto attempt execution status.

    continue → remain active
    retry_same_task / retry_with_scaffold → terminal (failed) so next start creates retry
    move_to_transfer / complete → completed
    """
    ts = now or _now_iso()
    if outcome is SpeakingMissionOutcome.proceed:
        return attempt
    if outcome in (
        SpeakingMissionOutcome.retry_same_task,
        SpeakingMissionOutcome.retry_with_scaffold,
    ):
        attempt.status = SpeakingAttemptStatus.failed
        attempt.completed_at = ts
        return attempt
    if outcome in (
        SpeakingMissionOutcome.move_to_transfer,
        SpeakingMissionOutcome.complete,
    ):
        attempt.status = SpeakingAttemptStatus.completed
        attempt.completed_at = ts
        return attempt
    return attempt


def reconcile_active_attempt_on_cursor_leave(
    lineage: SpeakingSessionAttemptLineage,
    *,
    current_task_id: str,
    now: str | None = None,
) -> SpeakingTaskAttempt | None:
    """S14 C-3 — when the execution cursor no longer points at the active attempt's
    task (task->non-task advance, or task->different-task), the prior attempt must
    not remain accidentally active.

    Truthful terminal semantics: an attempt the student left without a completing
    outcome is ``abandoned`` (never ``completed``/``failed`` — no invented success,
    no mastery). Pass ``current_task_id=""`` for a non-task cursor.
    """
    ts = now or _now_iso()
    active = get_active_attempt(lineage)
    if active is None:
        return None
    if active.task_id == current_task_id and current_task_id:
        return active
    if not active.is_terminal:
        active.status = SpeakingAttemptStatus.abandoned
        active.completed_at = ts
    lineage.active_attempt_id = ""
    return active


def mark_active_attempt_for_outcome(
    lineage: SpeakingSessionAttemptLineage,
    outcome: SpeakingMissionOutcome,
    *,
    now: str | None = None,
) -> SpeakingTaskAttempt | None:
    """Apply outcome to the active attempt and clear active_attempt_id when terminal."""
    active = get_active_attempt(lineage)
    if active is None:
        return None
    apply_outcome_to_attempt(active, outcome, now=now)
    if active.is_terminal:
        lineage.active_attempt_id = ""
    return active


# ---------------------------------------------------------------------------
# Student-safe projection helpers (PART 10)
# ---------------------------------------------------------------------------


def student_safe_attempt_projection(
    lineage: SpeakingSessionAttemptLineage | None,
    *,
    task_id: str = "",
) -> dict[str, object]:
    """Minimal student-safe attempt fields for journey (no IDs beyond count/flags)."""
    if lineage is None:
        return {
            "current_attempt_number": 0,
            "is_retry": False,
            "completed_task_attempt_count": 0,
        }
    active = get_active_attempt(lineage)
    focus_task = task_id or (active.task_id if active else "")
    if focus_task:
        task_attempts = attempts_for_task(lineage, focus_task)
        completed_count = sum(1 for a in task_attempts if a.is_terminal)
        current = active if active and active.task_id == focus_task else latest_attempt_for_task(lineage, focus_task)
    else:
        completed_count = sum(1 for a in lineage.attempts if a.is_terminal)
        current = active or (lineage.attempts[-1] if lineage.attempts else None)
    return {
        "current_attempt_number": current.attempt_number if current else 0,
        "is_retry": bool(current and current.is_retry),
        "completed_task_attempt_count": completed_count,
    }
