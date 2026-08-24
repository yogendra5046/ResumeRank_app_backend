"""Presentation: GET /status/{job_id} and /health + /ready routes."""
from __future__ import annotations

from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status

from src.application.dto.score_response import JobStatusResponse
from src.application.use_cases.get_job_status import GetJobStatusUseCase
from src.infrastructure.security.api_key_middleware import verify_api_key
from src.presentation.api.dependencies import get_status_use_case

router = APIRouter(tags=["Jobs"])
logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)


@router.get(
    "/status/{job_id}",
    summary="Poll async job status",
    response_model=JobStatusResponse,
)
async def get_job_status(
    job_id: str,
    use_case: Annotated[GetJobStatusUseCase, Depends(get_status_use_case)],
    _api_key: Annotated[str, Depends(verify_api_key)],
) -> JobStatusResponse:
    """Poll for the result of an async analysis job (202 response path)."""
    result = await use_case.execute(job_id)
    if result.status == "failed" and result.error == "Job not found or expired":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job '{job_id}' not found or expired",
        )
    return result
