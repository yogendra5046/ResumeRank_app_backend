"""Domain port: result cache abstraction."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional


class CacheRepositoryPort(ABC):
    """Hexagonal port – get/set scored results by composite cache key.

    Key construction (enforced by infrastructure impl):
        sha256(pdf_bytes + jd_text) → hex string
    TTL: 7 days (infrastructure concern).
    Cache hit must return in <50 ms.
    """

    @abstractmethod
    async def get(self, key: str) -> Optional[bytes]:
        """Return cached bytes or None on miss."""

    @abstractmethod
    async def set(self, key: str, value: bytes) -> None:
        """Store *value* under *key* with the configured TTL."""

    @abstractmethod
    async def delete(self, key: str) -> None:
        """Hard-delete a cache entry (GDPR erasure)."""

    @abstractmethod
    async def ping(self) -> bool:
        """Health-check; True if the backing store is reachable."""
