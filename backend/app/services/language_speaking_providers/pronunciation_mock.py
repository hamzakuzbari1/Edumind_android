"""Mock PhonemeAlignmentProvider — deterministic QA only (S5)."""

from __future__ import annotations

from app.services.language_speaking_providers.capabilities import PhonemeAlignmentCapabilities
from app.services.language_speaking_providers.providers import PhonemeAlignmentProvider


class MockPronunciationProvider(PhonemeAlignmentProvider):
    """Returns fixed phoneme alignment facts for structural verification."""

    def capabilities(self) -> PhonemeAlignmentCapabilities:
        return PhonemeAlignmentCapabilities(
            supports_forced_alignment=True,
            supports_phoneme_confidence=True,
            min_audio_duration_sec=0.1,
            provider_name="mock",
        )

    async def align(
        self,
        *,
        audio_bytes: bytes,
        transcript: str,
        reference_text: str = "",
    ) -> dict[str, object]:
        ref = (reference_text or transcript or "think").strip().lower()
        word = ref.split()[0] if ref else "think"
        if word == "think":
            expected = ["θ", "ɪ", "ŋ", "k"]
            observed = ["θ", "ɪ", "ŋ", "k"]
            ops = ["match"] * 4
        elif word == "sink":
            expected = ["s", "ɪ", "ŋ", "k"]
            observed = ["s", "ɪ", "ŋ", "k"]
            ops = ["match"] * 4
        else:
            expected = ["t", "ɛ", "s", "t"]
            observed = ["t", "ɛ", "s", "t"]
            ops = ["match"] * 4

        phoneme_obs = []
        t = 0.0
        for i, (exp, obs, op) in enumerate(zip(expected, observed, ops)):
            phoneme_obs.append(
                {
                    "expected_phoneme": exp,
                    "observed_phoneme": obs,
                    "start_sec": t,
                    "end_sec": t + 0.08,
                    "alignment_confidence": 0.92,
                    "operation": op,
                    "word_reference": word,
                    "position": i,
                }
            )
            t += 0.08

        return {
            "provider_name": "mock",
            "model": "mock-pronunciation-v1",
            "provider_version": "mock",
            "processing_version": "s5_mock",
            "reference_text": ref,
            "phoneme_observations": phoneme_obs,
            "word_observations": [
                {
                    "word": word,
                    "start_sec": 0.0,
                    "end_sec": t,
                    "expected_phonemes": expected,
                    "observed_phonemes": observed,
                    "word_confidence": 0.92,
                    "issue_tags": [],
                }
            ],
            "evidence_coverage": 1.0,
            "evidence_reliability": 0.92,
            "unavailable_evidence": [],
            "processing_warnings": [],
        }
