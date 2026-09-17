"""Mock AcousticFeatureProvider — deterministic QA only (S6)."""

from __future__ import annotations

from app.services.language_speaking_providers.capabilities import AcousticFeatureCapabilities
from app.services.language_speaking_providers.providers import AcousticFeatureProvider


class MockProsodyProvider(AcousticFeatureProvider):
    """Returns fixed prosody/expression facts for structural verification."""

    def capabilities(self) -> AcousticFeatureCapabilities:
        return AcousticFeatureCapabilities(
            supports_pitch=True,
            supports_energy=True,
            supports_rhythm=True,
            supports_stress=False,
            provider_name="mock",
        )

    async def extract(
        self,
        *,
        audio_bytes: bytes,
        mime_type: str,
    ) -> dict[str, object]:
        if not audio_bytes:
            return {
                "provider_name": "mock",
                "model": "mock-prosody-v1",
                "provider_version": "mock",
                "processing_version": "s6_mock",
                "expression_observations": [],
                "signal_observations": [],
                "turn_segments": [],
                "evidence_coverage": 0.0,
                "evidence_reliability": 0.0,
                "unavailable_evidence": ["audio_missing"],
                "processing_warnings": ["audio_missing"],
            }

        return {
            "provider_name": "mock",
            "model": "mock-prosody-v1",
            "provider_version": "mock",
            "processing_version": "s6_mock",
            "expression_observations": [
                {
                    "provider_label": "Concentration",
                    "normalized_tag": "expression:concentration",
                    "confidence": 0.64,
                    "source": "direct_provider",
                    "segment_start_sec": 0.0,
                    "segment_end_sec": 1.2,
                }
            ],
            "signal_observations": [
                {"signal_tag": "pitch_std_hz", "value": 42.0, "source": "derived_acoustic", "reliability": 0.7},
                {"signal_tag": "pause_density", "value": 0.12, "source": "derived_acoustic", "reliability": 0.7},
                {"signal_tag": "energy_std", "value": 0.08, "source": "derived_acoustic", "reliability": 0.7},
            ],
            "turn_segments": [{"start_sec": 0.0, "end_sec": 1.2, "speaker_id": "unknown"}],
            "evidence_coverage": 0.85,
            "evidence_reliability": 0.7,
            "unavailable_evidence": ["word_aligned_pauses_unavailable"],
            "processing_warnings": [],
        }
