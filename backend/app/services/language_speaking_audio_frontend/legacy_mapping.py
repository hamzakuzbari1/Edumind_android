"""Legacy → canonical audio contract mapping (S3).

Documents how frozen legacy speaking/audio paths map into the new S3 contracts.
No legacy code is modified — this is the adapter boundary specification only.

Legacy modules remain running behind ``language_speaking_legacy_adapter``.
"""

from __future__ import annotations

# Legacy module → canonical S3 contract mapping.
# Values describe the target contract, not an implemented adapter yet (S7+).
LEGACY_AUDIO_CONTRACT_MAP: dict[str, str] = {
    # Upload / storage
    "language_media_service.upload_student_speaking": "SpeakingAudioArtifact (raw, storage_reference from MediaObject)",
    "language_placement_service.upload_speaking_audio": "SpeakingAudioArtifact (raw, placement path)",
    "MediaObject": "storage_reference + integrity metadata on SpeakingAudioArtifact",
    # Normalization
    "language_transcription_service._normalize_to_wav_16k": "NormalizedAudioArtifact (future impl, contract only in S3)",
    # Transcription
    "language_transcription_service.ConversationTranscription": "TranscriptEvidence + ProviderProvenance",
    "language_transcription_service.transcribe_english_audio": "SpeechTranscriptionProvider → TranscriptEvidence",
    "student_chat_stt_service.transcribe_student_chat_audio": "SpeechTranscriptionProvider (Arabic path, out of scope for English speaking)",
    "voice_service.transcribe_audio": "SpeechTranscriptionProvider (lesson video path)",
    # Pronunciation / phoneme (legacy Claude+STT, not canonical yet)
    "language_pronunciation_service.assess_pronunciation": "PhonemeAlignmentEvidence + ProsodyFeatureEvidence (S4+ mapping)",
    # Conversation turn orchestration
    "language_conversation_service.process_conversation_turn": "SpeakingAudioEvidenceBundle → evaluation_runtime (S7+)",
    "language_speaking_feedback_service.analyze_speaking_recording": "SpeakingAudioEvidenceBundle → evaluation_runtime (S7+)",
    # Session lifecycle (legacy DB tables)
    "LanguageSpeakingConversationSession": "SpeakingAudioSessionRecord (session_id, student_id, lifecycle)",
    "LanguageSpeakingConversationTurn.user_media_object_id": "SpeakingAudioArtifact.audio_id linkage",
    "LanguageSpeakingProgress.media_object_id": "SpeakingAudioArtifact.audio_id linkage",
    # TTS (output path — not audio frontend input, documented for completeness)
    "language_reply_tts_service.synthesize_english_reply": "SpeakingSpeechOutputProvider (Supertonic legacy wrapper)",
    "language_supertonic_service.synthesize_language_speech": "SpeakingSpeechOutputProvider (Supertonic impl)",
}

# Known legacy → canonical field mappings for ConversationTranscription.
LEGACY_TRANSCRIPTION_FIELD_MAP: dict[str, str] = {
    "text": "TranscriptEvidence.text",
    "engine": "ProviderProvenance.provider_name",
    "model": "ProviderProvenance.model_name",
    "avg_logprob": "TranscriptEvidence.provider_confidence (transformed)",
    "no_speech_prob": "AudioEvidenceQualityFlag.low_audio_quality (if threshold exceeded)",
    "low_confidence": "AudioEvidenceQualityFlag.low_audio_quality",
    "meta": "ProviderProvenance.processing_version (opaque)",
}

# Known legacy → canonical field mappings for MediaObject audio storage.
LEGACY_STORAGE_FIELD_MAP: dict[str, str] = {
    "storage_key": "SpeakingAudioArtifact.storage_reference",
    "public_url": "SpeakingAudioArtifact.storage_reference (URL form)",
    "mime_type": "SpeakingAudioArtifact.content_type",
    "file_size_bytes": "SpeakingAudioArtifact.byte_size",
    "original_filename": "SpeakingAudioArtifact.original_filename",
    "id": "SpeakingAudioArtifact.audio_id (when used as FK)",
}

# Retention boundaries (contract documentation — no storage platform in S3).
AUDIO_RETENTION_BOUNDARIES: dict[str, str] = {
    "raw_audio": "Short-lived. Delete after evidence extraction. Never passed to educational engines.",
    "normalized_audio": "Short-lived. Delete after evidence extraction or when session expires.",
    "derived_evidence": "Persisted as SpeakingAudioEvidenceBundle / SpeakingSpeechEvidence. Long-lived.",
    "embeddings": "Stored by opaque embedding_reference only. Raw vectors never in educational objects.",
    "deletion_traceability": "Session expiry (SpeakingAudioSessionRecord.expires_at) drives raw/normalized cleanup.",
    "student_ownership": "All artifacts scoped to student_id + session_id. Cross-student access forbidden.",
}
