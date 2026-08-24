"""Application use case: GetJobStatusUseCase."""
from __future__ import annotations

import structlog

from src.application.dto.score_response import JobStatusResponse
from src.infrastructure.jobs.job_store import JobStore, JobStatus

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)


class GetJobStatusUseCase:
    """Poll the status of an async analysis job."""

    def __init__(self, job_store: JobStore) -> None:
        self._job_store = job_store

    async def execute(self, job_id: str) -> JobStatusResponse:
        log = logger.bind(job_id=job_id)
        status = await self._job_store.get_status(job_id)

        if status is None:
            log.warning("job_not_found")
            return JobStatusResponse(
                job_id=job_id,
                status="failed",
                error="Job not found or expired",
            )

        log.info("job_status_polled", status=status.state)
        return JobStatusResponse(
            job_id=job_id,
            status=status.state,  # type: ignore[arg-type]
            result=status.result,
            error=status.error,
        )
