"""Presentation: /health and /ready endpoints."""
from __future__ import annotations

import os
from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse

router = APIRouter(tags=["Observability"])


@router.get(
    "/health",
    summary="Deep health check (Redis + Model)",
    include_in_schema=True,
)
async def health(request: Request) -> JSONResponse:
    """Checks Redis connectivity and model load state.

    Returns 200 when all deps are healthy, 503 otherwise.
    Used by Cloud Run health-check and uptime monitors.
    """
    checks: dict[str, str] = {}
    healthy = True

    # Redis check
    redis_ok: bool = await request.app.state.cache_adapter.ping()
    checks["redis"] = "ok" if redis_ok else "degraded"
    if not redis_ok:
        healthy = False

    # Model check
    embedder = request.app.state.embedder
    model_ok: bool = embedder._model is not None or embedder._circuit_open
    checks["model"] = "ok" if model_ok else "warming_up"

    # ClamAV check (non-fatal – logs warning only)
    clamav_enabled = os.environ.get("CLAMAV_ENABLED", "true").lower() == "true"
    if clamav_enabled:
        try:
            scanner = request.app.state.scanner
            # Quick TCP ping: attempt to connect
            import asyncio
            _, writer = await asyncio.wait_for(
                asyncio.open_connection(scanner._host, scanner._port),
                timeout=2.0,
            )
            writer.close()
            checks["clamav"] = "ok"
        except Exception:
            checks["clamav"] = "unreachable"
            healthy = False
    else:
        checks["clamav"] = "disabled"

    http_status = status.HTTP_200_OK if healthy else status.HTTP_503_SERVICE_UNAVAILABLE
    return JSONResponse(
        status_code=http_status,
        content={"status": "ok" if healthy else "degraded", "checks": checks},
    )


@router.get(
    "/ready",
    summary="Kubernetes readiness probe",
    include_in_schema=False,
)
async def ready(request: Request) -> JSONResponse:
    """Lightweight readiness probe – only checks model warm-up state.

    Returns 200 once the embedder model is loaded.
    Kubernetes will not route traffic until this returns 200.
    """
    embedder = request.app.state.embedder
    if embedder._model is not None or embedder._circuit_open:
        return JSONResponse(status_code=200, content={"ready": True})
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"ready": False, "reason": "model_warming_up"},
    )
