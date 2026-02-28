"""In-process TTL cache for the airgap geo API."""

from __future__ import annotations

import asyncio
from typing import Any

from cachetools import TTLCache

from airgap_geo.settings import CACHE_MAX_SIZE, CACHE_TTL_SECONDS

_lock = asyncio.Lock()

_geocode_cache: TTLCache = TTLCache(maxsize=CACHE_MAX_SIZE, ttl=CACHE_TTL_SECONDS)
_route_cache: TTLCache = TTLCache(maxsize=CACHE_MAX_SIZE, ttl=CACHE_TTL_SECONDS)
_postcode_cache: TTLCache = TTLCache(maxsize=CACHE_MAX_SIZE, ttl=CACHE_TTL_SECONDS)


async def get_cached(cache: TTLCache, key: str) -> Any | None:
    """Return a cached value, or None if not present / expired."""
    async with _lock:
        return cache.get(key)


async def set_cached(cache: TTLCache, key: str, value: Any) -> None:
    """Store a value in the given cache."""
    async with _lock:
        cache[key] = value
