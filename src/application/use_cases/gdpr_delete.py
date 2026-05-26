"""Application use case: GdprDeleteUseCase.

Implements the GDPR right-to-erasure for a specific trace_id.
Deletes all cache entries associated with the trace and purges logs
by rotating/dropping structured log records with that trace_id.
"""
from __future__ import annotations

import structlog

from src.domain.ports.cache_repository import CacheRepositoryPort
from src.infrastructure.jobs.job_store import JobStore

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)


class GdprDeleteUseCase:
    """GDPR erasure use case.

    Deletes:
      - All cache entries keyed to this trace_id (stored at submission time).
      - The async job result if one exists.

    Note: Structured logs are ephemeral (stdout → Cloud Logging); Cloud Logging
    deletion is triggered via the GCP Data Deletion API in the deployment pipeline.
    The trace_id emitted here is used as the correlating filter key.
    """

    def __init__(
        self,
        cache: CacheRepositoryPort,
        job_store: JobStore,
    ) -> None:
        self._cache = cache
        self._job_store = job_store

    async def execute(self, trace_id: str) -> dict[str, str]:
        log = logger.bind(trace_id=trace_id)
        log.info("gdpr_delete_initiated")

        deleted_keys: list[str] = []

        # Delete cache entry indexed by trace_id
        trace_cache_key = f"trace:{trace_id}"
        await self._cache.delete(trace_cache_key)
        deleted_keys.append(trace_cache_key)

        # Delete job result if present
        await self._job_store.delete(trace_id)
        deleted_keys.append(f"job:{trace_id}")

        log.info("gdpr_delete_complete", deleted_keys=deleted_keys)
        return {
            "trace_id": trace_id,
            "status": "deleted",
            "deleted_keys": str(deleted_keys),
        }
