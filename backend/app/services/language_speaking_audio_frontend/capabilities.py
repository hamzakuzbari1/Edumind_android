"""Provider capability descriptors and evidence availability (S3).

Capability discovery lets the audio frontend compose multiple providers without
assuming any single provider supports everything.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.services.language_speaking_audio_frontend.enums import (
    ProviderCapabilityFlag,
    SpeakingEvidenceFamily,
)

# All known capability flags for validation and discovery.
ALL_PROVIDER_CAPABILITY_FLAGS: frozenset[ProviderCapabilityFlag] = frozenset(ProviderCapabilityFlag)

# Which capabilities each evidence family requires (at least one must be present
# for the family to be considered available).
EVIDENCE_FAMILY_REQUIRED_CAPABILITIES: dict[SpeakingEvidenceFamily, frozenset[ProviderCapabilityFlag]] = {
    SpeakingEvidenceFamily.transcript: frozenset({ProviderCapabilityFlag.transcription}),
    SpeakingEvidenceFamily.speech_embedding: frozenset({ProviderCapabilityFlag.speech_embeddings}),
    SpeakingEvidenceFamily.phoneme_alignment: frozenset({ProviderCapabilityFlag.phoneme_alignment}),
    SpeakingEvidenceFamily.prosody: frozenset(
        {
            ProviderCapabilityFlag.pitch,
            ProviderCapabilityFlag.energy,
            ProviderCapabilityFlag.pauses,
            ProviderCapabilityFlag.speaking_rate,
            ProviderCapabilityFlag.rhythm,
            ProviderCapabilityFlag.stress,
            ProviderCapabilityFlag.intonation,
        }
    ),
}


@dataclass(frozen=True, slots=True)
class ProviderCapabilityDescriptor:
    """What one provider instance declares it can produce."""

    provider_name: str
    capabilities: frozenset[ProviderCapabilityFlag]
    model_name: str = ""
    provider_version: str = ""

    def supports(self, flag: ProviderCapabilityFlag) -> bool:
        return flag in self.capabilities

    def supports_any(self, flags: frozenset[ProviderCapabilityFlag]) -> bool:
        return bool(self.capabilities & flags)

    def to_persistence_dict(self) -> dict[str, object]:
        return {
            "provider_name": self.provider_name,
            "capabilities": sorted(c.value for c in self.capabilities),
            "model_name": self.model_name,
            "provider_version": self.provider_version,
        }


def compute_evidence_availability(
    descriptors: tuple[ProviderCapabilityDescriptor, ...],
) -> dict[SpeakingEvidenceFamily, bool]:
    """Return which evidence families are available given provider capabilities.

    Missing capability is explicit — returns False, never fakes availability.
    """
    union: frozenset[ProviderCapabilityFlag] = frozenset()
    for desc in descriptors:
        union = union | desc.capabilities

    return {
        family: bool(union & required)
        for family, required in EVIDENCE_FAMILY_REQUIRED_CAPABILITIES.items()
    }
