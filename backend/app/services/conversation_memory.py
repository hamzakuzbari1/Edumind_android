"""Conversation history store for the speaking coach.

Scalable by design: uses Redis when REDIS_URL is set (so history survives across
processes / instances), and falls back to an in-process store for local dev.
History is a rolling window of the last N messages, with a TTL so stale sessions
expire automatically.
"""

from __future__ import annotations

import json
import os
import time
from collections import defaultdict, deque

MAX_MESSAGES = 16
SESSION_TTL_SECONDS = 60 * 60 * 6


class _InMemoryHistory:
    def __init__(self) -> None:
        self._store: dict[str, deque] = defaultdict(lambda: deque(maxlen=MAX_MESSAGES))
        self._touched: dict[str, float] = {}

    def _expire(self) -> None:
        cutoff = time.time() - SESSION_TTL_SECONDS
        for key in [k for k, t in self._touched.items() if t < cutoff]:
            self._store.pop(key, None)
            self._touched.pop(key, None)

    async def append(self, session_id: str, role: str, content: str) -> None:
        self._expire()
        self._store[session_id].append({"role": role, "content": content})
        self._touched[session_id] = time.time()

    async def get(self, session_id: str) -> list[dict]:
        self._expire()
        return list(self._store.get(session_id, []))

    async def clear(self, session_id: str) -> None:
        self._store.pop(session_id, None)
        self._touched.pop(session_id, None)


class _RedisHistory:
    def __init__(self, client) -> None:
        self._r = client

    @staticmethod
    def _key(session_id: str) -> str:
        return f"speaking_coach:history:{session_id}"

    async def append(self, session_id: str, role: str, content: str) -> None:
        key = self._key(session_id)
        await self._r.rpush(key, json.dumps({"role": role, "content": content}))
        await self._r.ltrim(key, -MAX_MESSAGES, -1)
        await self._r.expire(key, SESSION_TTL_SECONDS)

    async def get(self, session_id: str) -> list[dict]:
        raw = await self._r.lrange(self._key(session_id), 0, -1)
        out: list[dict] = []
        for item in raw:
            try:
                out.append(json.loads(item))
            except (json.JSONDecodeError, TypeError):
                continue
        return out

    async def clear(self, session_id: str) -> None:
        await self._r.delete(self._key(session_id))


def _build_store():
    redis_url = os.getenv("REDIS_URL", "").strip()
    if redis_url:
        try:
            import redis.asyncio as redis

            return _RedisHistory(redis.from_url(redis_url, decode_responses=True))
        except Exception:
            pass
    return _InMemoryHistory()


conversation_memory = _build_store()
