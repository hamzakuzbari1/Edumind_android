"""Real Hume EVI live conversation provider (S7.5).

Uses raw WebSocket to wss://api.hume.ai/v0/evi/chat — NOT the discontinued Batch API.
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
from typing import Any

from app.core.config import get_settings
from app.services.language_speaking_providers.live_provider_errors import (
    ProviderLiveConnectionClosedError,
    ProviderLiveConnectionFailedError,
    ProviderLiveProtocolError,
    ProviderLiveUnavailableError,
)
from app.services.language_speaking_providers.capabilities import LiveConversationCapabilities
from app.services.language_speaking_providers.providers import LiveConversationProvider

logger = logging.getLogger(__name__)
settings = get_settings()

_EVI_WS_URL = "wss://api.hume.ai/v0/evi/chat"


class HumeEviLiveConversationProvider(LiveConversationProvider):
    def __init__(self) -> None:
        self._ws: Any = None
        self._queue: asyncio.Queue[dict[str, object]] = asyncio.Queue()
        self._reader_task: asyncio.Task | None = None
        self._closed = False

    def capabilities(self) -> LiveConversationCapabilities:
        return LiveConversationCapabilities(
            supports_barge_in=True,
            supports_expression_measures=True,
            supports_custom_llm=True,
            supports_streaming_audio=True,
            provider_name="hume_evi",
        )

    async def connect(
        self,
        *,
        config_id: str,
        access_token: str = "",
        api_key: str = "",
        session_settings: dict[str, object] | None = None,
    ) -> None:
        try:
            import websockets
        except ImportError as exc:
            raise ProviderLiveUnavailableError("websockets package not installed", detail=str(exc)) from exc

        params: list[str] = []
        if access_token:
            params.append(f"access_token={access_token}")
        elif api_key:
            params.append(f"api_key={api_key}")
        else:
            raise ProviderLiveConnectionFailedError("EVI connect requires access_token or api_key")
        if config_id:
            params.append(f"config_id={config_id}")
        url = f"{_EVI_WS_URL}?{'&'.join(params)}"

        try:
            self._ws = await asyncio.wait_for(
                websockets.connect(url, max_size=6 * 1024 * 1024),
                timeout=float(settings.SPEAKING_EVI_TIMEOUT_SECONDS or 60),
            )
        except Exception as exc:
            raise ProviderLiveConnectionFailedError("EVI WebSocket connection failed", detail=str(exc)) from exc

        if session_settings:
            await self._ws.send(json.dumps(session_settings))

        self._closed = False
        self._reader_task = asyncio.create_task(self._read_loop())

    async def _read_loop(self) -> None:
        assert self._ws is not None
        try:
            async for message in self._ws:
                try:
                    data = json.loads(message)
                except json.JSONDecodeError:
                    data = {"type": "protocol_error", "raw": str(message)[:500]}
                if isinstance(data, dict):
                    await self._queue.put(data)
        except asyncio.CancelledError:
            return
        except Exception as exc:
            if not self._closed:
                await self._queue.put({"type": "error", "message": str(exc), "slug": "connection_closed"})
        finally:
            self._closed = True

    async def send_audio_chunk(self, *, pcm_bytes: bytes) -> None:
        if self._closed or self._ws is None:
            raise ProviderLiveConnectionClosedError("EVI session is closed")
        payload = {"type": "audio_input", "data": base64.b64encode(pcm_bytes).decode("ascii")}
        await self._ws.send(json.dumps(payload))

    async def receive_event(self) -> dict[str, object]:
        if self._closed and self._queue.empty():
            raise ProviderLiveConnectionClosedError("EVI session closed with no pending events")
        try:
            return await asyncio.wait_for(
                self._queue.get(),
                timeout=float(settings.SPEAKING_EVI_TIMEOUT_SECONDS or 60),
            )
        except asyncio.TimeoutError as exc:
            raise ProviderLiveProtocolError("Timed out waiting for EVI event") from exc

    async def close(self) -> None:
        self._closed = True
        if self._reader_task:
            self._reader_task.cancel()
            try:
                await self._reader_task
            except asyncio.CancelledError:
                pass
        if self._ws is not None:
            try:
                await self._ws.close()
            except Exception:
                logger.debug("EVI ws close ignored", exc_info=True)
            self._ws = None

    async def send_tool_response(
        self,
        *,
        tool_call_id: str,
        content: str,
        tool_name: str | None = None,
    ) -> None:
        if self._closed or self._ws is None:
            raise ProviderLiveConnectionClosedError("EVI session is closed")
        payload: dict[str, object] = {
            "type": "tool_response",
            "tool_call_id": tool_call_id,
            "content": content,
        }
        if tool_name:
            payload["tool_name"] = tool_name
            payload["tool_type"] = "function"
        await self._ws.send(json.dumps(payload))

    async def send_tool_error(
        self,
        *,
        tool_call_id: str,
        error: str,
        content: str = "",
    ) -> None:
        if self._closed or self._ws is None:
            raise ProviderLiveConnectionClosedError("EVI session is closed")
        payload: dict[str, object] = {
            "type": "tool_error",
            "tool_call_id": tool_call_id,
            "error": error,
            "level": "warn",
        }
        if content:
            payload["content"] = content
        await self._ws.send(json.dumps(payload))

    async def send_user_input(self, *, text: str) -> None:
        """Send text user_input to elicit tool use (real acceptance only)."""
        if self._closed or self._ws is None:
            raise ProviderLiveConnectionClosedError("EVI session is closed")
        await self._ws.send(json.dumps({"type": "user_input", "text": text}))
