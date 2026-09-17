"""Phase 12 — tiny in-memory TTL cache for hot, slow-changing reads.

Single-process (swap for Redis at multi-instance scale). Used for derived data that is expensive to
recompute every request but changes slowly (e.g. the difficulty profile), with a short TTL so
staleness stays bounded. `now` is injectable for deterministic tests.
"""

from __future__ import annotations

import time
from typing import Any, Hashable


class TTLCache:
    def __init__(self) -> None:
        self._store: dict[Hashable, tuple[float, Any]] = {}

    def get(self, key: Hashable, *, now: float | None = None) -> Any | None:
        now = time.time() if now is None else now
        item = self._store.get(key)
        if item is None:
            return None
        expires_at, value = item
        if expires_at < now:
            self._store.pop(key, None)
            return None
        return value

    def set(self, key: Hashable, value: Any, ttl: float, *, now: float | None = None) -> None:
        now = time.time() if now is None else now
        self._store[key] = (now + ttl, value)

    def invalidate(self, key: Hashable) -> None:
        self._store.pop(key, None)

    def clear(self) -> None:
        self._store.clear()
