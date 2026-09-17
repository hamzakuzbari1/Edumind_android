"""Internal transcript contract for uploaded lesson-video STT."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class TranscriptSegment:
    """Normalized segment/paragraph compatible with the legacy string pipeline."""

    text: str
    start: float | None = None
    end: float | None = None


@dataclass(frozen=True)
class TranscriptResult:
    """Provider-neutral transcript returned to the lesson video flow.

    Downstream ``process_lesson`` currently consumes ``text`` only; segments,
    language, and duration are preserved for logging and future contracts.
    """

    text: str
    provider: str
    model: str
    language: str
    duration_s: float | None = None
    audio_duration_s: float | None = None
    segments: tuple[TranscriptSegment, ...] = field(default_factory=tuple)
    status: str = "ok"
    error_category: str | None = None

    def normalized_text(self) -> str:
        return (self.text or "").strip()
