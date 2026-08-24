"""Tests: GDPR deletion endpoint."""
from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from src.application.use_cases.gdpr_delete import GdprDeleteUseCase
from src.domain.ports.cache_repository import CacheRepositoryPort
from src.infrastructure.jobs.job_store import JobStore


@pytest.mark.asyncio
@pytest.mark.unit
async def test_gdpr_delete_removes_cache_entry() -> None:
    """GDPR delete must call cache.delete for the trace_id key."""
    cache = AsyncMock(spec=CacheRepositoryPort)
    job_store = AsyncMock(spec=JobStore)

    use_case = GdprDeleteUseCase(cache=cache, job_store=job_store)
    result = await use_case.execute("trace-abc-123")

    assert result["status"] == "deleted"
    assert result["trace_id"] == "trace-abc-123"
    cache.delete.assert_called_once_with("trace:trace-abc-123")


@pytest.mark.asyncio
@pytest.mark.unit
async def test_gdpr_delete_removes_job_entry() -> None:
    """GDPR delete must call job_store.delete for the trace_id."""
    cache = AsyncMock(spec=CacheRepositoryPort)
    job_store = AsyncMock(spec=JobStore)

    use_case = GdprDeleteUseCase(cache=cache, job_store=job_store)
    await use_case.execute("trace-job-456")

    job_store.delete.assert_called_once_with("trace-job-456")


@pytest.mark.asyncio
@pytest.mark.unit
async def test_gdpr_delete_idempotent() -> None:
    """Deleting a non-existent trace_id must not raise (idempotent)."""
    cache = AsyncMock(spec=CacheRepositoryPort)
    cache.delete.return_value = None  # Redis DEL returns 0 on missing key – no error
    job_store = AsyncMock(spec=JobStore)
    job_store.delete.return_value = None

    use_case = GdprDeleteUseCase(cache=cache, job_store=job_store)
    result = await use_case.execute("nonexistent-trace-999")
    assert result["status"] == "deleted"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_gdpr_endpoint_via_http(async_client: object) -> None:
    """DELETE /v1/gdpr/delete/{trace_id} must return 200 with deletion confirmation."""
    from httpx import AsyncClient

    client: AsyncClient = async_client  # type: ignore[assignment]
    response = await client.delete(
        "/v1/gdpr/delete/test-trace-http-001",
        headers={"X-API-Key": "resumerank-pro-2026"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["trace_id"] == "test-trace-http-001"
    assert body["status"] == "deleted"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_gdpr_delete_without_api_key_returns_401(async_client: object) -> None:
    """GDPR endpoint must be auth-protected."""
    from httpx import AsyncClient

    client: AsyncClient = async_client  # type: ignore[assignment]
    response = await client.delete(
        "/v1/gdpr/delete/some-trace",
        headers={},  # No X-API-Key
    )
    assert response.status_code == 401
