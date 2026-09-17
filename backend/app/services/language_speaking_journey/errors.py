"""Typed S14 failure semantics for deterministic Alex context + live identity.

These are the single source of truth for fail-closed behavior: when educational
context or live-execution identity cannot be established truthfully, the system
MUST NOT fall back to a generic Alex conversation. Every error carries a stable
``code`` (mapped to safe frontend behavior) and a student-safe ``message`` that
never leaks internal ids, provider details, or credentials.
"""

from __future__ import annotations


class SpeakingLiveExecutionError(Exception):
    """Base class for S14 educational-live failures (fail closed)."""

    code = "live_execution_error"
    http_status = 409
    student_message = "This speaking session can't continue right now. Please try again."

    def __init__(self, message: str = "", *, detail: str = "") -> None:
        super().__init__(message or self.code)
        self.detail = detail

    def to_student_dict(self) -> dict[str, object]:
        return {"error_code": self.code, "message": self.student_message}


class SpeakingContextUnavailableError(SpeakingLiveExecutionError):
    """No authoritative educational context exists — cannot ground Alex."""

    code = "speaking_context_unavailable"
    http_status = 409
    student_message = (
        "Your speaking lesson isn't ready yet. Start your lesson before talking with Alex."
    )


class SpeakingContextStaleError(SpeakingLiveExecutionError):
    """The context fingerprint no longer matches authoritative state."""

    code = "speaking_context_stale"
    http_status = 409
    student_message = "Your lesson has moved on. Refreshing your speaking session…"


class InvalidLiveSessionError(SpeakingLiveExecutionError):
    """The live_session_id is not backend-issued / does not match the active lease."""

    code = "invalid_live_session"
    http_status = 409
    student_message = "This live session is no longer valid. Please start again."


class LiveSessionNotOwnedError(SpeakingLiveExecutionError):
    """The live_session_id belongs to a different student/lease."""

    code = "live_session_not_owned"
    http_status = 403
    student_message = "This live session can't be used on this account."


class LiveTaskMismatchError(SpeakingLiveExecutionError):
    """The live execution's task no longer matches the current educational cursor."""

    code = "live_task_mismatch"
    http_status = 409
    student_message = "Your speaking task changed. Refreshing your session…"


class AmbiguousActiveAttemptError(SpeakingLiveExecutionError):
    """Persisted lineage has more than one active attempt (fail closed, C-7)."""

    code = "ambiguous_active_attempt"
    http_status = 409
    student_message = "We hit a problem tracking this task. Please restart your speaking session."


class LiveExecutionNotReadyError(SpeakingLiveExecutionError):
    """No active educational task/attempt to bind this live turn to."""

    code = "live_execution_not_ready"
    http_status = 409
    student_message = "Your speaking task isn't ready yet. Please start your lesson first."


LIVE_EXECUTION_ERROR_CODES: frozenset[str] = frozenset(
    {
        SpeakingContextUnavailableError.code,
        SpeakingContextStaleError.code,
        InvalidLiveSessionError.code,
        LiveSessionNotOwnedError.code,
        LiveTaskMismatchError.code,
        AmbiguousActiveAttemptError.code,
        LiveExecutionNotReadyError.code,
    }
)
