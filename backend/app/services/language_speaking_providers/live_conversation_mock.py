"""Deterministic mock EVI provider for structural QA only (S7.5/S7.6)."""

from __future__ import annotations

import asyncio
import struct

from app.services.language_speaking_providers.capabilities import LiveConversationCapabilities
from app.services.language_speaking_providers.providers import LiveConversationProvider


def _tone_pcm(*, seconds: float = 0.2, hz: int = 440, sample_rate: int = 16000) -> bytes:
    frames = int(sample_rate * seconds)
    out = bytearray()
    for i in range(frames):
        val = int(12000 * __import__("math").sin(2 * 3.14159265 * hz * (i / sample_rate)))
        out.extend(struct.pack("<h", val))
    return bytes(out)


class MockEviLiveConversationProvider(LiveConversationProvider):
    """QA-only scripted EVI session — never used in production acceptance."""

    def __init__(self, *, script_tool_call: bool = False) -> None:
        self._events: asyncio.Queue[dict[str, object]] = asyncio.Queue()
        self._connected = False
        self._chunks_seen = 0
        self._script_tool_call = script_tool_call
        self.tool_responses_sent: list[dict[str, object]] = []
        self.tool_errors_sent: list[dict[str, object]] = []

    def capabilities(self) -> LiveConversationCapabilities:
        return LiveConversationCapabilities(provider_name="mock_evi")

    async def connect(
        self,
        *,
        config_id: str,
        access_token: str = "",
        api_key: str = "",
        session_settings: dict[str, object] | None = None,
    ) -> None:
        self._connected = True
        await self._events.put(
            {
                "type": "chat_metadata",
                "chat_id": "mock-chat-1",
                "chat_group_id": "mock-group-1",
            }
        )
        if self._script_tool_call:
            await self._events.put(
                {
                    "type": "tool_call",
                    "name": "get_student_speaking_context",
                    "parameters": "{}",
                    "response_required": True,
                    "tool_call_id": "mock-tool-call-1",
                    "tool_type": "function",
                }
            )

    async def send_audio_chunk(self, *, pcm_bytes: bytes) -> None:
        if not self._connected:
            raise RuntimeError("mock not connected")
        self._chunks_seen += 1
        if self._chunks_seen >= 2:
            await self._events.put(
                {
                    "type": "user_message",
                    "interim": False,
                    "from_text": False,
                    "message": {"role": "user", "content": "Hello, this is a mock student turn."},
                    "models": {"prosody": {"scores": {"Calmness": 0.42, "Interest": 0.55}}},
                    "time": {"begin": 0, "end": 1200},
                }
            )
            assistant_pcm = _tone_pcm()
            await self._events.put(
                {
                    "type": "assistant_message",
                    "message": {"role": "assistant", "content": "Mock assistant reply."},
                }
            )
            await self._events.put(
                {
                    "type": "audio_output",
                    "data": __import__("base64").b64encode(assistant_pcm).decode("ascii"),
                }
            )
            await self._events.put({"type": "assistant_end"})

    async def receive_event(self) -> dict[str, object]:
        return await asyncio.wait_for(self._events.get(), timeout=5.0)

    async def send_tool_response(
        self,
        *,
        tool_call_id: str,
        content: str,
        tool_name: str | None = None,
    ) -> None:
        payload = {
            "type": "tool_response",
            "tool_call_id": tool_call_id,
            "content": content,
            "tool_name": tool_name,
        }
        self.tool_responses_sent.append(payload)

    async def send_tool_error(
        self,
        *,
        tool_call_id: str,
        error: str,
        content: str = "",
    ) -> None:
        payload = {
            "type": "tool_error",
            "tool_call_id": tool_call_id,
            "error": error,
            "content": content,
        }
        self.tool_errors_sent.append(payload)

    async def close(self) -> None:
        self._connected = False
        while not self._events.empty():
            try:
                self._events.get_nowait()
            except asyncio.QueueEmpty:
                break
