"""Speaking audio_frontend (S3).

RESPONSIBILITY: Canonical audio ingestion and evidence contracts. Provider-neutral
boundaries for transcript, embedding, phoneme alignment, and prosody evidence.
Orchestrates providers into SpeakingAudioEvidenceBundle. No provider SDKs,
no educational scoring, no raw audio bytes in educational objects.
"""

from app.services.language_speaking_audio_frontend.types import (
    AudioFrontendResult,
    LANGUAGE_SPEAKING_AUDIO_FRONTEND_VERSION,
    SpeakingAudioArtifact,
    SpeakingAudioEvidenceBundle,
    SpeakingAudioInput,
    assemble_evidence_bundle,
)

__all__ = [
    "AudioFrontendResult",
    "LANGUAGE_SPEAKING_AUDIO_FRONTEND_VERSION",
    "SpeakingAudioArtifact",
    "SpeakingAudioEvidenceBundle",
    "SpeakingAudioInput",
    "assemble_evidence_bundle",
]
