"""Presentation: DELETE /gdpr/delete/{trace_id}."""
from __future__ import annotations

from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse

from src.application.use_cases.gdpr_delete import GdprDeleteUseCase
from src.infrastructure.security.api_key_middleware import verify_api_key
from src.presentation.api.dependencies import get_gdpr_use_case

router = APIRouter(prefix="/gdpr", tags=["GDPR"])
logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)


@router.delete(
    "/delete/{trace_id}",
    summary="GDPR right-to-erasure",
    description=(
        "Permanently deletes all cached results and job data "
        "associated with the given trace_id. "
        "Compliant with GDPR Article 17."
    ),
    status_code=status.HTTP_200_OK,
)
async def gdpr_delete(
    trace_id: str,
    use_case: Annotated[GdprDeleteUseCase, Depends(get_gdpr_use_case)],
    _api_key: Annotated[str, Depends(verify_api_key)],
) -> JSONResponse:
    """Erase all data for a given trace_id (GDPR Article 17)."""
    logger.info("gdpr_delete_request", trace_id=trace_id)
    result = await use_case.execute(trace_id)
    return JSONResponse(status_code=status.HTTP_200_OK, content=result)
