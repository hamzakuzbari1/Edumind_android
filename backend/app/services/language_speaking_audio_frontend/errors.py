"""Provider-neutral S4/S5 runtime errors — no raw provider exceptions escape."""

from __future__ import annotations


class SpeakingAudioRuntimeError(Exception):
    """Base error for speaking audio ingestion / transcription runtime."""

    code: str = "speaking_audio_runtime_error"

    def __init__(self, message: str, *, detail: str = "") -> None:
        self.detail = detail
        super().__init__(message)


class AudioNotFoundError(SpeakingAudioRuntimeError):
    code = "audio_not_found"


class UnsupportedAudioFormatError(SpeakingAudioRuntimeError):
    code = "unsupported_audio_format"


class NormalizationFailedError(SpeakingAudioRuntimeError):
    code = "normalization_failed"


class NormalizedAudioInvalidError(SpeakingAudioRuntimeError):
    code = "normalized_audio_invalid"


class TranscriptionProviderUnavailableError(SpeakingAudioRuntimeError):
    code = "transcription_provider_unavailable"


class TranscriptionTimeoutError(SpeakingAudioRuntimeError):
    code = "transcription_timeout"


class TranscriptionFailedError(SpeakingAudioRuntimeError):
    code = "transcription_failed"


class EmptyTranscriptError(SpeakingAudioRuntimeError):
    code = "empty_transcript"


class SessionTransitionError(SpeakingAudioRuntimeError):
    code = "session_transition_error"


class EvidenceBundleAssemblyFailedError(SpeakingAudioRuntimeError):
    code = "evidence_bundle_assembly_failed"


class PronunciationProviderUnavailableError(SpeakingAudioRuntimeError):
    code = "pronunciation_provider_unavailable"


class PronunciationModelLoadFailedError(SpeakingAudioRuntimeError):
    code = "pronunciation_model_load_failed"


class PronunciationAnalysisFailedError(SpeakingAudioRuntimeError):
    code = "pronunciation_analysis_failed"


class PronunciationTimeoutError(SpeakingAudioRuntimeError):
    code = "pronunciation_timeout"


class PronunciationReferenceMissingError(SpeakingAudioRuntimeError):
    code = "pronunciation_reference_missing"


class PronunciationAudioMissingError(SpeakingAudioRuntimeError):
    code = "pronunciation_audio_missing"


class PronunciationAlignmentFailedError(SpeakingAudioRuntimeError):
    code = "pronunciation_alignment_failed"


class PronunciationEvidenceEmptyError(SpeakingAudioRuntimeError):
    code = "pronunciation_evidence_empty"


class PronunciationEvidenceUnreliableError(SpeakingAudioRuntimeError):
    code = "pronunciation_evidence_unreliable"


class ProsodyProviderUnavailableError(SpeakingAudioRuntimeError):
    code = "prosody_provider_unavailable"


class ProsodyProviderDiscontinuedError(SpeakingAudioRuntimeError):
    code = "prosody_provider_discontinued"


class ProsodyAuthenticationFailedError(SpeakingAudioRuntimeError):
    code = "prosody_authentication_failed"


class ProsodyRateLimitedError(SpeakingAudioRuntimeError):
    code = "prosody_rate_limited"


class ProsodyTimeoutError(SpeakingAudioRuntimeError):
    code = "prosody_timeout"


class ProsodyAnalysisFailedError(SpeakingAudioRuntimeError):
    code = "prosody_analysis_failed"


class ProsodyAudioMissingError(SpeakingAudioRuntimeError):
    code = "prosody_audio_missing"


class ProsodyResponseInvalidError(SpeakingAudioRuntimeError):
    code = "prosody_response_invalid"


class ProsodyEvidenceEmptyError(SpeakingAudioRuntimeError):
    code = "prosody_evidence_empty"


class ProsodyEvidenceUnreliableError(SpeakingAudioRuntimeError):
    code = "prosody_evidence_unreliable"
