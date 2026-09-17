"""Legal state transitions for the speaking audio session lifecycle (S3).

The transition graph is intentionally narrow: audio moves forward through
ingestion/processing, may fail or expire from any non-terminal state, and can
never move backward. This prevents impossible transitions such as
``processed -> processing`` or ``created -> ready`` (skipping normalization).

Session state is infrastructure state only — it never encodes educational
mastery or speaking performance.
"""

from __future__ import annotations

from app.services.language_speaking_audio_session.enums import SpeakingAudioLifecycleState

_S = SpeakingAudioLifecycleState

# Forward-only lifecycle. ``failed`` and ``expired`` are reachable from any
# active state; ``expired`` is the sole absorbing terminal state.
LEGAL_AUDIO_SESSION_TRANSITIONS: dict[SpeakingAudioLifecycleState, frozenset[SpeakingAudioLifecycleState]] = {
    _S.created: frozenset({_S.uploading, _S.failed, _S.expired}),
    _S.uploading: frozenset({_S.uploaded, _S.failed, _S.expired}),
    _S.uploaded: frozenset({_S.normalizing, _S.failed, _S.expired}),
    _S.normalizing: frozenset({_S.ready, _S.failed, _S.expired}),
    _S.ready: frozenset({_S.processing, _S.failed, _S.expired}),
    _S.processing: frozenset({_S.processed, _S.failed, _S.expired}),
    _S.processed: frozenset({_S.expired}),
    _S.failed: frozenset({_S.expired}),
    _S.expired: frozenset(),
}

# States from which no forward progress (beyond expiry) is possible.
TERMINAL_AUDIO_SESSION_STATES: frozenset[SpeakingAudioLifecycleState] = frozenset(
    {_S.processed, _S.failed, _S.expired}
)

# The single absorbing state.
ABSORBING_AUDIO_SESSION_STATE: SpeakingAudioLifecycleState = _S.expired


class IllegalAudioSessionTransition(ValueError):
    """Raised when an impossible audio session transition is attempted."""

    def __init__(
        self,
        from_state: SpeakingAudioLifecycleState,
        to_state: SpeakingAudioLifecycleState,
    ) -> None:
        self.from_state = from_state
        self.to_state = to_state
        super().__init__(
            f"Illegal audio session transition: {from_state.value} -> {to_state.value}"
        )


def is_legal_transition(
    from_state: SpeakingAudioLifecycleState,
    to_state: SpeakingAudioLifecycleState,
) -> bool:
    """Return True if ``from_state -> to_state`` is a permitted transition."""
    return to_state in LEGAL_AUDIO_SESSION_TRANSITIONS.get(from_state, frozenset())


def next_states(
    from_state: SpeakingAudioLifecycleState,
) -> frozenset[SpeakingAudioLifecycleState]:
    """Return the set of states reachable from ``from_state`` in one step."""
    return LEGAL_AUDIO_SESSION_TRANSITIONS.get(from_state, frozenset())
