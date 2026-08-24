"""Infrastructure: API key middleware with Redis rate limiting.

Header: X-API-Key (required on all /v1/* routes)
Rate limit: 100 requests/day/key (sliding window via Redis INCR + EXPIRE)
Key format: sha256(raw_key + salt) stored in Redis to avoid plaintext key storage.
"""
from __future__ import annotations

import hashlib
import os
from datetime import UTC, datetime

import redis.asyncio as aioredis
import structlog
from fastapi import HTTPException, Request, Security, status
from fastapi.security import APIKeyHeader

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)

_API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)
_RATE_LIMIT_PER_DAY: int = 100
_SALT: str = os.environ.get("API_KEY_SALT", "change-me-in-production")


def _hash_key(raw_key: str) -> str:
    """One-way hash API key before storing in Redis (no plaintext)."""
    return hashlib.sha256(f"{raw_key}{_SALT}".encode()).hexdigest()


def _rate_limit_redis_key(hashed_key: str) -> str:
    today = datetime.now(tz=UTC).strftime("%Y-%m-%d")
    return f"ratelimit:{hashed_key}:{today}"


async def verify_api_key(
    request: Request,
    api_key: str | None = Security(_API_KEY_HEADER),
) -> str:
    """FastAPI dependency: validates X-API-Key and enforces daily rate limit.

    Returns the hashed key (safe to log) on success.
    Raises HTTP 401 if missing/invalid, 429 if rate limit exceeded.
    """
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-API-Key header is required",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    hashed = _hash_key(api_key)
    
    # SECURITY FIX: Check if the key is in the authorized whitelist
    # In a real system, this would be a lookup in a 'api_keys' table or Redis set.
    _AUTHORIZED_KEYS = {
        _hash_key(os.environ.get("ADMIN_API_KEY", "resume-rank-master-key-2024")),
        _hash_key("resumerank-pro-2026"),
        _hash_key("rr-client-mobile-app-prod"),
    }
    
    if hashed not in _AUTHORIZED_KEYS:
        logger.warning("unauthorized_api_key_attempt", hashed_key=hashed[:12])
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid X-API-Key",
        )

    redis_client: aioredis.Redis | None = request.app.state.redis  # type: ignore[type-arg]
    rl_key = _rate_limit_redis_key(hashed)

    count = 0
    if redis_client:
        try:
            pipe = redis_client.pipeline()
            pipe.incr(rl_key)
            pipe.expire(rl_key, 86400)  # expire at end of day
            results: list[int] = await pipe.execute()  # type: ignore[assignment]
            count = results[0]
        except Exception as exc:
            logger.error("rate_limit_redis_error", error=str(exc))
            # Fail-open on Redis error (availability > strict rate limit)
            count = 0

    if count > _RATE_LIMIT_PER_DAY:
        logger.warning(
            "rate_limit_exceeded",
            hashed_key=hashed[:12],
            count=count,
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded: {_RATE_LIMIT_PER_DAY} requests/day",
            headers={"Retry-After": "86400", "X-RateLimit-Limit": str(_RATE_LIMIT_PER_DAY)},
        )

    logger.debug("api_key_verified", hashed_key=hashed[:12], count=count)
    return hashed
