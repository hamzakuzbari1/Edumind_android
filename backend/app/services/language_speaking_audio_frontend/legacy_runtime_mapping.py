"""S4 legacy runtime mapping — documents how legacy audio/STT enters canonical path."""

from __future__ import annotations

S4_LEGACY_RUNTIME_MAP: dict[str, str] = {
    "language_transcription_service.transcribe_english_audio": (
        "Legacy English STT — NOT imported by S4; alternative path via legacy_adapter only. "
        "S4 uses FasterWhisperTranscriptionProvider with word_timestamps=True."
    ),
    "language_transcription_service._normalize_to_wav_16k": (
        "Legacy normalization — S4 reimplements equivalent ffmpeg command in normalization_runtime.py"
    ),
    "language_media_service.upload_student_speaking": (
        "MediaObject + local disk -> artifact_from_media_object -> SpeakingAudioArtifact"
    ),
    "language_speaking_feedback_service._read_media_bytes": (
        "Legacy read path — S4 uses media_adapter.read_media_bytes with structured AudioNotFoundError"
    ),
    "MediaObject.storage_key": "SpeakingAudioArtifact.storage_reference (relative path under UPLOAD_DIR)",
    "MediaObject.public_url": "SpeakingAudioArtifact.storage_reference (URL form)",
    "LanguageSpeakingConversationTurn.evaluation_json": (
        "Future persistence target for SpeakingAudioEvidenceBundle serialized dict"
    ),
    "LanguageSpeakingProgress.metrics_json": (
        "Future persistence target for transcript evidence / bundle reference"
    ),
}

S4_PERSISTENCE_MAPPING: dict[str, str] = {
    "source_audio": "MediaObject.id / storage_key referenced by SpeakingAudioArtifact.audio_id",
    "normalized_audio": "NormalizedAudioArtifact.storage_reference (short-lived, not auto-deleted in S4)",
    "session_state": "SpeakingAudioSessionRecord.to_persistence_dict() — in-memory/runtime only in S4",
    "transcript_evidence": "TranscriptEvidence inside SpeakingAudioEvidenceBundle",
    "evidence_bundle_id": "SpeakingAudioEvidenceBundle.evidence_bundle_id",
    "provider_provenance": "ProviderProvenance on TranscriptEvidence + bundle.provider_provenance",
    "processing_warnings": "bundle.processing_warnings + normalization_warnings on NormalizedAudioArtifact",
    "processing_failure": "SpeakingAudioRuntimeResult.error.code + session.failure_reason",
}
