"""Legal live session lifecycle transitions (S7.5)."""

from __future__ import annotations

from app.services.language_speaking_live_conversation.enums import SpeakingLiveSessionState as _S


class IllegalLiveTransition(ValueError):
    def __init__(self, from_state: _S, to_state: _S) -> None:
        self.from_state = from_state
        self.to_state = to_state
        super().__init__(f"Illegal live session transition: {from_state.value} -> {to_state.value}")


LEGAL_LIVE_TRANSITIONS: dict[_S, frozenset[_S]] = {
    _S.created: frozenset({_S.connecting, _S.failed, _S.closed}),
    _S.connecting: frozenset({_S.connected, _S.failed, _S.closed}),
    _S.connected: frozenset({_S.listening, _S.failed, _S.closing}),
    _S.listening: frozenset({_S.user_speaking, _S.closing, _S.failed, _S.closed}),
    _S.user_speaking: frozenset({_S.user_turn_complete, _S.interrupted, _S.failed, _S.closing}),
    _S.user_turn_complete: frozenset({_S.assistant_thinking, _S.listening, _S.closing, _S.failed}),
    _S.assistant_thinking: frozenset({_S.assistant_speaking, _S.listening, _S.failed, _S.closing}),
    _S.assistant_speaking: frozenset({_S.interrupted, _S.listening, _S.user_speaking, _S.closing, _S.failed}),
    _S.interrupted: frozenset({_S.listening, _S.user_speaking, _S.closing, _S.failed}),
    _S.closing: frozenset({_S.closed, _S.failed}),
    _S.closed: frozenset(),
    _S.failed: frozenset({_S.closed}),
}


def is_legal_live_transition(from_state: _S, to_state: _S) -> bool:
    return to_state in LEGAL_LIVE_TRANSITIONS.get(from_state, frozenset())
