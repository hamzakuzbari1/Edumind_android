"""Real derived-acoustic prosody provider (S6 production).

Computes prosody/delivery evidence directly from the normalized 16k mono WAV
using numpy (pitch/energy/pause/rate/rhythm). No external API, no expression
model. All evidence is tagged DERIVED_ACOUSTIC; expression/word-aligned signals
are explicitly reported as unavailable — never faked.
"""

from __future__ import annotations

import asyncio

from app.services.language_speaking_providers.acoustic_derive import derive_acoustic_prosody
from app.services.language_speaking_providers.capabilities import AcousticFeatureCapabilities
from app.services.language_speaking_providers.providers import AcousticFeatureProvider

_MODEL = "numpy-derived-prosody-v1"


def _analyze_sync(audio_bytes: bytes) -> dict[str, object]:
    if not audio_bytes:
        return {
            "provider_name": "acoustic",
            "model": _MODEL,
            "provider_version": "numpy",
            "processing_version": "s6_acoustic",
            "expression_observations": [],
            "signal_observations": [],
            "turn_segments": [],
            "evidence_coverage": 0.0,
            "evidence_reliability": 0.0,
            "unavailable_evidence": ["audio_missing"],
            "processing_warnings": ["audio_missing"],
        }

    derived = derive_acoustic_prosody(audio_bytes)
    signals = list(derived.get("signal_observations") or [])
    unavailable = list(derived.get("unavailable_evidence") or [])
    warnings = list(derived.get("processing_warnings") or [])

    # This provider has no expression model and no provider-native turn segments.
    unavailable.append("expression_evidence_unavailable")
    unavailable.append("provider_turn_segments_unavailable")

    reliabilities = [float(s.get("reliability") or 0.0) for s in signals if isinstance(s, dict)]
    reliability = sum(reliabilities) / len(reliabilities) if reliabilities else 0.0
    coverage = min(1.0, len(signals) / 12.0) if signals else 0.0

    return {
        "provider_name": "acoustic",
        "model": _MODEL,
        "provider_version": "numpy",
        "processing_version": "s6_acoustic",
        "expression_observations": [],
        "signal_observations": signals,
        "turn_segments": [],
        "evidence_coverage": round(coverage, 4),
        "evidence_reliability": round(reliability, 4),
        "unavailable_evidence": list(dict.fromkeys(unavailable)),
        "processing_warnings": warnings,
    }


class AcousticProsodyProvider(AcousticFeatureProvider):
    """Production prosody via numpy-derived acoustics on the normalized WAV."""

    def capabilities(self) -> AcousticFeatureCapabilities:
        return AcousticFeatureCapabilities(
            supports_pitch=True,
            supports_energy=True,
            supports_rhythm=True,
            supports_stress=False,
            provider_name="acoustic",
        )

    async def extract(
        self,
        *,
        audio_bytes: bytes,
        mime_type: str,
    ) -> dict[str, object]:
        return await asyncio.to_thread(_analyze_sync, audio_bytes)
