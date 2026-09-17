"""Prosody runtime — provider dict to S3 ProsodyFeatureEvidence (S6)."""

from __future__ import annotations

import asyncio
from datetime import datetime

from app.core.config import get_settings
from app.services.language_speaking.types import PauseMarker
from app.services.language_speaking_audio_frontend.enums import (
    AudioEvidenceQualityFlag,
    SpeakingEvidenceFamily,
)
from app.services.language_speaking_audio_frontend.errors import (
    ProsodyAnalysisFailedError,
    ProsodyAudioMissingError,
    ProsodyAuthenticationFailedError,
    ProsodyEvidenceEmptyError,
    ProsodyEvidenceUnreliableError,
    ProsodyProviderDiscontinuedError,
    ProsodyRateLimitedError,
    ProsodyResponseInvalidError,
    ProsodyTimeoutError,
)
from app.services.language_speaking_audio_frontend.evidence import (
    EnergySummary,
    IntonationEvidence,
    PauseEvidence,
    PitchSummary,
    ProsodyFeatureEvidence,
    ProviderProvenance,
    RhythmEvidence,
    SpeakingRateEvidence,
    StressEvidence,
)
from app.services.language_speaking_audio_frontend.prosody_factory import build_prosody_provider
from app.services.language_speaking_providers.providers import AcousticFeatureProvider

settings = get_settings()


def _signal_value(raw: dict[str, object], tag: str, default: float = 0.0) -> float:
    for item in list(raw.get("signal_observations") or []):
        if isinstance(item, dict) and str(item.get("signal_tag") or "") == tag:
            return float(item.get("value") or default)
    return default


def provider_dict_to_prosody_evidence(
    raw: dict[str, object],
    *,
    generated_at: datetime | None = None,
) -> tuple[ProsodyFeatureEvidence, tuple[AudioEvidenceQualityFlag, ...]]:
    """Convert provider-native dict to canonical S3 ProsodyFeatureEvidence."""
    pitch_mean = _signal_value(raw, "pitch_mean_hz")
    pitch_std = _signal_value(raw, "pitch_std_hz")
    pitch_range = _signal_value(raw, "pitch_range_hz")
    energy_mean = _signal_value(raw, "energy_mean")
    energy_std = _signal_value(raw, "energy_std")
    energy_peak = _signal_value(raw, "energy_peak")
    pause_count = int(_signal_value(raw, "pause_count"))
    total_pause = _signal_value(raw, "total_pause_duration_sec")
    rate_proxy = _signal_value(raw, "speaking_rate_proxy")
    rhythm_reg = _signal_value(raw, "rhythm_regularity")

    # Word-aligned pause locations are unavailable in S6 — do not fabricate.
    pauses: tuple[PauseMarker, ...] = ()

    quality_flags: list[AudioEvidenceQualityFlag] = []
    unavailable = list(raw.get("unavailable_evidence") or [])
    if "evidence_unreliable" in unavailable or "audio_too_short" in unavailable:
        quality_flags.append(AudioEvidenceQualityFlag.low_audio_quality)
    if not list(raw.get("expression_observations") or []) and not list(raw.get("signal_observations") or []):
        quality_flags.append(AudioEvidenceQualityFlag.prosody_unavailable)

    provenance = ProviderProvenance(
        provider_name=str(raw.get("provider_name") or "unknown"),
        model_name=str(raw.get("model") or ""),
        provider_version=str(raw.get("provider_version") or ""),
        processing_version=str(raw.get("processing_version") or "s6"),
        generated_at=generated_at,
        evidence_family=SpeakingEvidenceFamily.prosody,
    )

    evidence = ProsodyFeatureEvidence(
        pitch=PitchSummary(
            mean_hz=pitch_mean,
            std_hz=pitch_std,
            range_hz=pitch_range,
            min_hz=max(0.0, pitch_mean - pitch_std),
            max_hz=pitch_mean + pitch_std,
        ),
        energy=EnergySummary(mean=energy_mean, std=energy_std, peak=energy_peak),
        speaking_rate=SpeakingRateEvidence(
            words_per_minute=0.0,
            syllables_per_minute=rate_proxy,
            articulation_rate_wpm=rate_proxy,
        ),
        pause=PauseEvidence(
            pauses=pauses,
            total_pause_duration_sec=total_pause,
            pause_count=pause_count,
        ),
        rhythm=RhythmEvidence(regularity=rhythm_reg, nPVI=0.0),
        stress=StressEvidence(stressed_syllable_count=0, stress_accuracy_ratio=None),
        intonation=IntonationEvidence(phrase_final_rise=None, contour_type=""),
        provenance=provenance,
    )
    return evidence, tuple(quality_flags)


async def analyze_prosody_audio(
    wav_bytes: bytes,
    *,
    provider: AcousticFeatureProvider | None = None,
    provider_name: str | None = None,
    mime_type: str = "audio/wav",
    generated_at: datetime | None = None,
) -> tuple[dict[str, object], ProsodyFeatureEvidence, tuple[AudioEvidenceQualityFlag, ...], AcousticFeatureProvider]:
    """Run prosody analysis on normalized WAV bytes."""
    if not wav_bytes:
        raise ProsodyAudioMissingError("Normalized audio bytes are missing")

    prov = provider or build_prosody_provider(provider_name)
    timeout = max(1, int(settings.SPEAKING_PROSODY_TIMEOUT_SECONDS or 120))
    try:
        raw = await asyncio.wait_for(
            prov.extract(audio_bytes=wav_bytes, mime_type=mime_type),
            timeout=timeout + 15,
        )
    except asyncio.TimeoutError as exc:
        raise ProsodyTimeoutError("Prosody analysis timed out") from exc
    except PermissionError as exc:
        raise ProsodyAuthenticationFailedError("Hume authentication failed") from exc
    except TimeoutError as exc:
        raise ProsodyTimeoutError("Prosody analysis timed out") from exc
    except (
        ProsodyAudioMissingError,
        ProsodyTimeoutError,
        ProsodyAuthenticationFailedError,
        ProsodyRateLimitedError,
    ):
        raise
    except RuntimeError as exc:
        msg = str(exc).lower()
        if "discontinued" in msg:
            raise ProsodyProviderDiscontinuedError(
                "Prosody provider API is discontinued", detail=str(exc)
            ) from exc
        if "rate limited" in msg:
            raise ProsodyRateLimitedError("Hume rate limited") from exc
        if "authentication failed" in msg:
            raise ProsodyAuthenticationFailedError("Hume authentication failed") from exc
        raise ProsodyAnalysisFailedError("Prosody analysis failed", detail=type(exc).__name__) from exc
    except Exception as exc:
        raise ProsodyAnalysisFailedError(
            "Prosody analysis failed",
            detail=type(exc).__name__,
        ) from exc

    if not isinstance(raw, dict):
        raise ProsodyResponseInvalidError("Provider returned non-dict response")

    unavailable = list(raw.get("unavailable_evidence") or [])
    if "audio_missing" in unavailable:
        raise ProsodyAudioMissingError("Provider reported missing audio")

    try:
        evidence, flags = provider_dict_to_prosody_evidence(raw, generated_at=generated_at)
    except Exception as exc:
        raise ProsodyResponseInvalidError(
            "Failed to map prosody evidence",
            detail=type(exc).__name__,
        ) from exc

    has_direct = bool(raw.get("expression_observations"))
    has_derived = bool(raw.get("signal_observations"))
    if not has_direct and not has_derived and "audio_missing" not in unavailable:
        raise ProsodyEvidenceEmptyError("Prosody evidence is empty")

    if "evidence_unreliable" in unavailable and not has_direct and not has_derived:
        raise ProsodyEvidenceUnreliableError("Prosody evidence is unreliable")

    return raw, evidence, flags, prov
