"""Infrastructure: In-memory cache adapter (fallback)."""
from __future__ import annotations

import time
from typing import Optional

from src.domain.ports.cache_repository import CacheRepositoryPort


class InMemoryCacheAdapter(CacheRepositoryPort):
    """Simple in-memory cache – implements CacheRepositoryPort."""

    def __init__(self) -> None:
        self._data: dict[str, tuple[bytes, float]] = {}

    async def get(self, key: str) -> Optional[bytes]:
        if key not in self._data:
            return None
        
        value, expiry = self._data[key]
        if time.time() > expiry:
            del self._data[key]
            return None
            
        return value

    async def set(self, key: str, value: bytes) -> None:
        # Default TTL 7 days as per port spec
        expiry = time.time() + (7 * 24 * 3600)
        self._data[key] = (value, expiry)

    async def delete(self, key: str) -> None:
        self._data.pop(key, None)

    async def ping(self) -> bool:
        return True
