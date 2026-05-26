"""Infrastructure: Redis cache adapter.

Key schema:  sha256(pdf_sha256 + ":" + jd_sha256) → msgpack(ScoreResponse)
TTL: 7 days (604800 seconds)
Cache-hit target: <50 ms (enforced by hiredis parser + local Redis)

GDPR: delete() does a hard DEL, honouring right-to-erasure.
"""
from __future__ import annotations

from typing import Optional

import redis.asyncio as aioredis
import structlog

from src.domain.ports.cache_repository import CacheRepositoryPort

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)

_TTL_SECONDS: int = 7 * 24 * 3600  # 7 days


class RedisCacheAdapter(CacheRepositoryPort):
    """Async Redis cache – implements CacheRepositoryPort."""

    def __init__(self, redis_client: aioredis.Redis) -> None:  # type: ignore[type-arg]
        self._redis = redis_client

    async def get(self, key: str) -> Optional[bytes]:
        value: bytes | None = await self._redis.get(key)
        if value is None:
            logger.debug("cache_miss", key=key[:16])
        return value

    async def set(self, key: str, value: bytes) -> None:
        await self._redis.setex(name=key, time=_TTL_SECONDS, value=value)
        logger.debug("cache_set", key=key[:16], ttl=_TTL_SECONDS)

    async def delete(self, key: str) -> None:
        deleted = await self._redis.delete(key)
        logger.info("cache_delete", key=key[:16], deleted=deleted)

    async def ping(self) -> bool:
        try:
            return bool(await self._redis.ping())
        except Exception as exc:
            logger.warning("redis_ping_failed", error=str(exc))
            return False


def build_redis_client(redis_url: str) -> aioredis.Redis:  # type: ignore[type-arg]
    """Factory: creates a connection pool-backed async Redis client."""
    return aioredis.from_url(
        redis_url,
        encoding="utf-8",
        decode_responses=False,  # we store raw bytes
        max_connections=20,
        socket_timeout=2.0,
        socket_connect_timeout=2.0,
        retry_on_timeout=True,
    )
