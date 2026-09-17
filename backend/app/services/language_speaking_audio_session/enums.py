"""Audio session lifecycle enum (S3).

Infrastructure state only. These states describe where an audio artifact is in
the ingestion/processing pipeline. They MUST NEVER represent educational mastery,
pronunciation quality, readiness, or speaking performance.
"""

from __future__ import annotations

from enum import StrEnum


class SpeakingAudioLifecycleState(StrEnum):
    """Lifecycle of a single speaking audio session (infrastructure only).

    This is distinct from ``SpeakingSessionProcessingState`` (S0), which tracks
    the conversation/evaluation processing pipeline. This enum tracks the raw
    audio *ingestion* lifecycle owned by the audio frontend layer.
    """

    created = "created"
    uploading = "uploading"
    uploaded = "uploaded"
    normalizing = "normalizing"
    ready = "ready"
    processing = "processing"
    processed = "processed"
    failed = "failed"
    expired = "expired"
