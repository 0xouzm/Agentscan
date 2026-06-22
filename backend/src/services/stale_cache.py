"""Small async stale-while-revalidate cache for slow upstream reads."""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from typing import Any

import structlog

logger = structlog.get_logger()

Loader = Callable[[], Awaitable[Any]]
Validator = Callable[[Any], bool]


class StaleWhileRevalidateCache:
    """Return stale successful values immediately while refreshing in background."""

    def __init__(self, ttl: float, is_cacheable: Validator | None = None) -> None:
        self._ttl = ttl
        self._is_cacheable = is_cacheable or (lambda value: value is not None)
        self._store: dict[str, tuple[float, Any]] = {}
        self._refreshing: set[str] = set()
        self._lock = asyncio.Lock()

    async def get_or_set(self, key: str, loader: Loader, refresh_loader: Loader | None = None):
        cached = self._store.get(key)
        now = time.monotonic()
        if cached and now - cached[0] < self._ttl:
            return cached[1]
        if cached:
            await self._ensure_refresh(key, refresh_loader or loader)
            return cached[1]

        async with self._lock:
            cached = self._store.get(key)
            now = time.monotonic()
            if cached and now - cached[0] < self._ttl:
                return cached[1]
            value = await loader()
            if self._is_cacheable(value):
                self._store[key] = (time.monotonic(), value)
            return value

    async def _ensure_refresh(self, key: str, loader: Loader) -> None:
        async with self._lock:
            if key in self._refreshing:
                return
            self._refreshing.add(key)
        asyncio.create_task(self._refresh(key, loader))

    async def _refresh(self, key: str, loader: Loader) -> None:
        try:
            value = await loader()
            if self._is_cacheable(value):
                async with self._lock:
                    self._store[key] = (time.monotonic(), value)
        except Exception as exc:  # noqa: BLE001
            logger.warning("stale_cache_refresh_failed", key=key, error=str(exc))
        finally:
            async with self._lock:
                self._refreshing.discard(key)
