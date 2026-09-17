"""Backend-authoritative live identity + pre-evaluation authorization boundary (S14).

Identity semantics (single source of truth):
- ``lease_id``        : S13 budget authorization identity (backend owned).
- ``live_session_id`` : logical educational live-execution identity, DERIVED from the
                        lease by the backend. Frontend echoes it; it does NOT mint it.
- ``attempt_id``      : S11 execution lineage identity — backend only, never exposed
                        to the frontend and never chosen by the client.

``live_session_id`` is deterministically derived from ``lease_id`` so a reconnect on
the same valid lease resolves to the SAME logical conversation (no new attempt, no
budget reset). A forged/stale ``live_session_id`` that does not match the active lease
is rejected BEFORE the S4->S8 evaluation/mutation path runs.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.language.progression import LanguageProgression
from app.services.language_progression_service import ensure_progression_row
from app.services.language_speaking_journey.alex_context import authoritative_task_prompt
from app.services.language_speaking_journey.errors import (
    AmbiguousActiveAttemptError,
    InvalidLiveSessionError,
    LiveExecutionNotReadyError,
    LiveSessionNotOwnedError,
)
from app.services.language_speaking_knowledge_model.storage import speaking_bucket_from_payload
from app.services.language_speaking_lesson_planner.attempt_lineage import (
    AmbiguousActiveAttemptError as LineageAmbiguousActiveAttemptError,
)
from app.services.language_speaking_lesson_planner.attempt_lineage import (
    assert_active_attempt_integrity,
)
from app.services.language_speaking_lesson_planner.mission_task_resolver import (
    SpeakingRuntimeTaskResolution,
    resolve_current_task,
)
from app.services.language_speaking_lesson_planner.storage import load_s9_state
from app.services.language_speaking_lesson_planner.types import SpeakingSessionPhase
from app.services.language_speaking_live_budget import validate_active_lease

LIVE_SESSION_ID_PREFIX = "lsx-"


def derive_live_session_id(lease_id: str) -> str:
    """Backend-issued logical live conversation id, stable per lease (reconnect-safe)."""
    if not lease_id:
        return ""
    return f"{LIVE_SESSION_ID_PREFIX}{lease_id}"


def is_backend_live_session_id(live_session_id: str, lease_id: str) -> bool:
    """True only when ``live_session_id`` is the backend-derived id for ``lease_id``."""
    if not live_session_id or not lease_id:
        return False
    return live_session_id == derive_live_session_id(lease_id)


@dataclass(frozen=True, slots=True)
class LiveTurnAuthorization:
    """Result of the pre-evaluation execution authorization boundary."""

    live_session_id: str
    lease_id: str
    task_prompt: str
    mission_id: str
    task_id: str
    execution_mode: str
    attempt_number: int
    is_retry: bool
    session_id: str

    def to_safe_dict(self) -> dict[str, object]:
        # No attempt_id / no internal ids leaked.
        return {
            "live_session_id": self.live_session_id,
            "task_prompt": self.task_prompt,
            "attempt_number": self.attempt_number,
            "is_retry": self.is_retry,
        }


async def authorize_live_turn_execution(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
    lease_id: str,
    live_session_id: str,
) -> LiveTurnAuthorization:
    """Fail-closed boundary that MUST run before S4->S8 for any live turn.

    Order (PART 15):
      1. active S13 lease owned by this student
      2. backend-issued live_session_id matches the lease
      3. authoritative educational session/task exists (else not ready)
      4. lineage integrity (C-7 ambiguous active → fail closed)
      5. current cursor is an executable task (else not ready)
      6. establish the authoritative task prompt

    A forged / stale / mismatched live_session_id cannot pass step 2, so it never
    reaches S8 mutation.
    """
    if not lease_id:
        raise InvalidLiveSessionError(detail="missing_lease")

    owned = await validate_active_lease(db, student_id=student_id, lease_id=lease_id)
    if not owned:
        raise LiveSessionNotOwnedError(detail="lease_not_owned_or_inactive")

    expected = derive_live_session_id(lease_id)
    if not live_session_id or live_session_id != expected:
        # Forged, stale, or client-minted id — reject before any evaluation/mutation.
        raise InvalidLiveSessionError(detail="live_session_id_mismatch")

    row: LanguageProgression = await ensure_progression_row(
        db, student_id=student_id, language_id=language_id
    )
    bucket = speaking_bucket_from_payload(dict(row.promotion_readiness_json or {}))
    state = load_s9_state(bucket)
    blueprint, session, lineage = state.blueprint, state.session, state.attempt_lineage
    if blueprint is None or session is None or session.phase == SpeakingSessionPhase.completed:
        raise LiveExecutionNotReadyError(detail="no_active_session")

    if lineage is not None:
        try:
            assert_active_attempt_integrity(lineage)
        except LineageAmbiguousActiveAttemptError as exc:
            raise AmbiguousActiveAttemptError(detail=str(exc)) from exc

    resolution: SpeakingRuntimeTaskResolution = resolve_current_task(blueprint, session)
    if not resolution.is_task or not resolution.task_id:
        raise LiveExecutionNotReadyError(detail="current_activity_is_not_a_task")

    task_prompt = authoritative_task_prompt(blueprint)
    if not task_prompt:
        raise LiveExecutionNotReadyError(detail="missing_task_prompt")

    return LiveTurnAuthorization(
        live_session_id=expected,
        lease_id=lease_id,
        task_prompt=task_prompt,
        mission_id=resolution.mission_id,
        task_id=resolution.task_id,
        execution_mode=resolution.execution_mode,
        attempt_number=0,
        is_retry=False,
        session_id=session.session_id,
    )
