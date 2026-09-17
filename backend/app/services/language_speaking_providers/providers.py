"""Provider ABCs for the Speaking Audio Frontend and speech output (S0).

RESPONSIBILITY: Abstract provider interfaces only. Implementations live in
adapter modules (legacy STT, Supertonic TTS, future WhisperX/WavLM/etc.).
Educational engines must NOT import provider SDKs directly.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from app.services.language_speaking_providers.capabilities import (
    AcousticFeatureCapabilities,
    EducationalAnalyzerCapabilities,
    EmbeddingCapabilities,
    LiveConversationCapabilities,
    PhonemeAlignmentCapabilities,
    SpeechOutputCapabilities,
    TranscriptionCapabilities,
)

if TYPE_CHECKING:
    from app.services.language_speaking.types import SpeakingSpeechEvidence


class SpeechTranscriptionProvider(ABC):
    """Transcript + word timing from raw audio."""

    @abstractmethod
    def capabilities(self) -> TranscriptionCapabilities:
        ...

    @abstractmethod
    async def transcribe(
        self,
        *,
        audio_bytes: bytes,
        mime_type: str,
        language: str = "en",
        initial_prompt: str = "",
    ) -> dict[str, object]:
        """Return provider-native dict; Audio Frontend normalizes to evidence."""


class SpeechEmbeddingProvider(ABC):
    """Speech representation embeddings (WavLM/HuBERT-compatible boundary)."""

    @abstractmethod
    def capabilities(self) -> EmbeddingCapabilities:
        ...

    @abstractmethod
    async def embed(
        self,
        *,
        audio_bytes: bytes,
        mime_type: str,
    ) -> str:
        """Return opaque embedding_ref — not raw vectors in hot path."""


class PhonemeAlignmentProvider(ABC):
    """Forced / observed phoneme alignment (SpeechBrain-compatible boundary)."""

    @abstractmethod
    def capabilities(self) -> PhonemeAlignmentCapabilities:
        ...

    @abstractmethod
    async def align(
        self,
        *,
        audio_bytes: bytes,
        transcript: str,
        reference_text: str = "",
    ) -> dict[str, object]:
        """Return alignment facts; must not claim errors without evidence."""


class AcousticFeatureProvider(ABC):
    """Prosody-relevant acoustic features (OpenSMILE/Praat-compatible boundary)."""

    @abstractmethod
    def capabilities(self) -> AcousticFeatureCapabilities:
        ...

    @abstractmethod
    async def extract(
        self,
        *,
        audio_bytes: bytes,
        mime_type: str,
    ) -> dict[str, object]:
        """Return pitch/energy/rhythm features for ProsodyFeatures assembly."""


class SpeakingSpeechOutputProvider(ABC):
    """Speech synthesis — current production: Supertonic. NOT ElevenLabs."""

    @abstractmethod
    def capabilities(self) -> SpeechOutputCapabilities:
        ...

    @abstractmethod
    async def synthesize(
        self,
        *,
        text: str,
        language: str = "en",
        voice: str = "",
        speaking_rate: float | None = None,
        segments: tuple[tuple[str, str], ...] = (),
    ) -> dict[str, object]:
        """Return synthesis result (media ref, duration, status)."""


class SpeakingEducationalAnalyzerProvider(ABC):
    """Semantic / language analyzer — structured educational facts only."""

    @abstractmethod
    def capabilities(self) -> EducationalAnalyzerCapabilities:
        ...

    @abstractmethod
    async def analyze(
        self,
        *,
        transcript: str,
        evidence: "SpeakingSpeechEvidence",
        context: dict[str, object],
    ) -> dict[str, object]:
        """Return JSON-serializable educational facts — never pass/fail/promotion."""


class LiveConversationProvider(ABC):
    """Real-time speech-to-speech live conversation (Hume EVI boundary)."""

    @abstractmethod
    def capabilities(self) -> LiveConversationCapabilities:
        ...

    @abstractmethod
    async def connect(
        self,
        *,
        config_id: str,
        access_token: str = "",
        api_key: str = "",
        session_settings: dict[str, object] | None = None,
    ) -> None:
        """Open authenticated EVI WebSocket session."""

    @abstractmethod
    async def send_audio_chunk(self, *, pcm_bytes: bytes) -> None:
        """Stream base64-ready PCM chunk as audio_input."""

    @abstractmethod
    async def receive_event(self) -> dict[str, object]:
        """Return next provider-native event dict."""

    @abstractmethod
    async def close(self) -> None:
        """Close session and release resources."""

    async def send_tool_response(
        self,
        *,
        tool_call_id: str,
        content: str,
        tool_name: str | None = None,
    ) -> None:
        """Send Hume tool_response — optional for providers without tool support."""
        raise NotImplementedError("send_tool_response not implemented")

    async def send_tool_error(
        self,
        *,
        tool_call_id: str,
        error: str,
        content: str = "",
    ) -> None:
        """Send Hume tool_error — optional for providers without tool support."""
        raise NotImplementedError("send_tool_error not implemented")


__all__ = [
    "AcousticFeatureProvider",
    "LiveConversationProvider",
    "PhonemeAlignmentProvider",
    "SpeakingEducationalAnalyzerProvider",
    "SpeakingSpeechOutputProvider",
    "SpeechEmbeddingProvider",
    "SpeechTranscriptionProvider",
]
