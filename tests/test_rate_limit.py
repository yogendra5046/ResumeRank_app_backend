"""Tests: Redis rate limiting – 100/day/key enforcement."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from src.infrastructure.security.api_key_middleware import verify_api_key


def _make_mock_request(redis_count: int) -> MagicMock:
    """Build a fake FastAPI Request with a mock Redis pipeline."""
    pipe = AsyncMock()
    pipe.incr = AsyncMock()
    pipe.expire = AsyncMock()
    pipe.execute = AsyncMock(return_value=[redis_count, True])

    redis_mock = MagicMock()
    redis_mock.pipeline.return_value = pipe

    request = MagicMock()
    request.app.state.redis = redis_mock
    return request


@pytest.mark.asyncio
@pytest.mark.unit
async def test_first_request_allowed() -> None:
    """First request of the day (count=1) must pass."""
    request = _make_mock_request(redis_count=1)
    result = await verify_api_key(request=request, api_key="resumerank-pro-2026")
    assert isinstance(result, str)
    assert len(result) == 64  # SHA-256 hex digest


@pytest.mark.asyncio
@pytest.mark.unit
async def test_exactly_100_requests_allowed() -> None:
    """The 100th request must be allowed (boundary condition)."""
    request = _make_mock_request(redis_count=100)
    result = await verify_api_key(request=request, api_key="resumerank-pro-2026")
    assert result  # no exception raised


@pytest.mark.asyncio
@pytest.mark.unit
async def test_101st_request_rejected() -> None:
    """The 101st request must be rejected with HTTP 429."""
    request = _make_mock_request(redis_count=101)
    with pytest.raises(HTTPException) as exc_info:
        await verify_api_key(request=request, api_key="resumerank-pro-2026")
    assert exc_info.value.status_code == 429
    assert "Rate limit exceeded" in exc_info.value.detail
    assert "Retry-After" in exc_info.value.headers


@pytest.mark.asyncio
@pytest.mark.unit
async def test_missing_api_key_returns_401() -> None:
    """Absent X-API-Key header must return HTTP 401."""
    request = MagicMock()
    with pytest.raises(HTTPException) as exc_info:
        await verify_api_key(request=request, api_key=None)
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
@pytest.mark.unit
async def test_different_keys_have_independent_limits() -> None:
    """Two distinct API keys must have independent rate-limit counters."""
    # Both at count=50 – both should pass
    request_a = _make_mock_request(redis_count=50)
    request_b = _make_mock_request(redis_count=50)

    result_a = await verify_api_key(request=request_a, api_key="resumerank-pro-2026")
    result_b = await verify_api_key(request=request_b, api_key="rr-client-mobile-app-prod")

    # Different hashes (different keys)
    assert result_a != result_b


@pytest.mark.asyncio
@pytest.mark.unit
async def test_redis_error_fails_open() -> None:
    """Redis errors must fail-open (allow request) to preserve availability."""
    pipe = AsyncMock()
    pipe.execute = AsyncMock(side_effect=ConnectionError("Redis down"))
    redis_mock = AsyncMock()
    redis_mock.pipeline.return_value = pipe

    request = MagicMock()
    request.app.state.redis = redis_mock

    # Should NOT raise – fails open
    result = await verify_api_key(request=request, api_key="resumerank-pro-2026")
    assert result  # returns hashed key


@pytest.mark.asyncio
@pytest.mark.unit
async def test_api_key_is_hashed_before_storage() -> None:
    """Raw API key must never appear in Redis key (security requirement)."""
    raw_key = "resumerank-pro-2026"
    captured_keys: list[str] = []

    pipe = AsyncMock()

    async def fake_execute() -> list[int]:
        return [1, True]

    pipe.execute = fake_execute
    redis_mock = AsyncMock()
    redis_mock.pipeline.return_value = pipe

    request = MagicMock()
    request.app.state.redis = redis_mock

    await verify_api_key(request=request, api_key=raw_key)

    # Verify the raw key was never passed to Redis incr
    call_args = str(pipe.incr.call_args_list)
    assert raw_key not in call_args
