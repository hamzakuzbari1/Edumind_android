"""Bounded per-user-turn student audio accumulator (S7.5).

RETENTION: buffers exist only for the active user turn in memory.
- Accumulates student microphone PCM only (never assistant audio).
- Finalizes once at turn boundary; cleared after handoff or on session close/failure.
- Max bytes/duration enforced from config; overflow raises LiveTurnTooLargeError/LiveTurnTimeoutError.
"""

from __future__ import annotations

import time
import wave
import io
from dataclasses import dataclass, field

from app.services.language_speaking_live_conversation.errors import (
    LiveTurnFinalizationFailedError,
    LiveTurnTimeoutError,
    LiveTurnTooLargeError,
)


@dataclass
class StudentTurnAudioAccumulator:
    max_turn_bytes: int
    max_turn_seconds: float
    sample_rate_hz: int = 16000
    channels: int = 1
    _chunks: list[bytes] = field(default_factory=list)
    _started_monotonic: float | None = None
    _finalized: bool = False
    _byte_count: int = 0

    def start_turn(self) -> None:
        self._chunks.clear()
        self._byte_count = 0
        self._finalized = False
        self._started_monotonic = time.monotonic()

    def append_student_pcm(self, pcm_bytes: bytes) -> None:
        if self._finalized:
            raise LiveTurnFinalizationFailedError("Cannot append after turn finalized")
        if not pcm_bytes:
            return
        elapsed = time.monotonic() - (self._started_monotonic or time.monotonic())
        if elapsed > self.max_turn_seconds:
            raise LiveTurnTimeoutError("Student turn exceeded max duration")
        if self._byte_count + len(pcm_bytes) > self.max_turn_bytes:
            raise LiveTurnTooLargeError("Student turn exceeded max bytes")
        self._chunks.append(pcm_bytes)
        self._byte_count += len(pcm_bytes)

    def finalize_wav(self) -> bytes:
        if self._finalized:
            raise LiveTurnFinalizationFailedError("Turn already finalized")
        if not self._chunks:
            raise LiveTurnFinalizationFailedError("No student audio captured for turn")
        self._finalized = True
        pcm = b"".join(self._chunks)
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(self.channels)
            wf.setsampwidth(2)
            wf.setframerate(self.sample_rate_hz)
            wf.writeframes(pcm)
        return buf.getvalue()

    def clear(self) -> None:
        self._chunks.clear()
        self._byte_count = 0
        self._finalized = False
        self._started_monotonic = None

    @property
    def is_finalized(self) -> bool:
        return self._finalized

    @property
    def byte_count(self) -> int:
        return self._byte_count
