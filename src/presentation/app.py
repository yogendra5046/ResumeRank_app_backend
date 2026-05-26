"""Presentation: FastAPI application factory.

Wires all infrastructure at startup via lifespan context manager.
No business logic here – only composition root.
"""
from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app

from src.infrastructure.cache.redis_cache import RedisCacheAdapter, build_redis_client
from src.infrastructure.ml.minilm_embedder import MiniLmEmbedder
from src.infrastructure.ml.tfidf_fallback import TfIdfFallbackEmbedder
from src.infrastructure.security.clamav_scanner import ClamAvScanner
from src.infrastructure.skills.esco_loader import load_esco_taxonomy
from src.infrastructure.telemetry.otel import (
    configure_logging,
    configure_tracing,
    instrument_app,
)
from src.presentation.api.v1 import analyze, gdpr, health, status as status_route, skills as skills_route, rewrite, insights, auth


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Startup: warm up models and connections. Shutdown: close cleanly."""
    # Database Initialization
    from src.infrastructure.database import engine, Base
    from src.domain.models.user import User # Ensure model is registered
    Base.metadata.create_all(bind=engine)

    # Redis / Cache / JobStore
    redis_enabled = os.environ.get("REDIS_ENABLED", "false").lower() == "true"
    if redis_enabled:
        redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
        redis_client = build_redis_client(redis_url)
        app.state.redis = redis_client
        app.state.cache_adapter = RedisCacheAdapter(redis_client)
        from src.infrastructure.jobs.job_store import JobStore
        app.state.job_store = JobStore(redis_client)
    else:
        from src.infrastructure.cache.memory_cache import InMemoryCacheAdapter
        from src.infrastructure.jobs.memory_job_store import InMemoryJobStore
        app.state.redis = None
        app.state.cache_adapter = InMemoryCacheAdapter()
        app.state.job_store = InMemoryJobStore()

    # ESCO taxonomy + skill graph
    app.state.taxonomy = load_esco_taxonomy()

    # ClamAV
    clamav_enabled = os.environ.get("CLAMAV_ENABLED", "false").lower() == "true"
    if clamav_enabled:
        app.state.scanner = ClamAvScanner(
            host=os.environ.get("CLAMAV_HOST", "localhost"),
            port=int(os.environ.get("CLAMAV_PORT", "3310")),
        )
    else:
        from src.infrastructure.security.noop_scanner import NoOpScanner
        app.state.scanner = NoOpScanner()

    # ML Models + Services Preloading (spaCy + Sentence Transformers)
    from src.infrastructure.di import preload_models
    await preload_models(app.state)

    yield  # ── application running ──────────────────────────────────────────

    # Shutdown: close Redis connection pool
    if redis_enabled and app.state.redis:
        await app.state.redis.aclose()


def create_app() -> FastAPI:
    """Application factory – call this from Dockerfile CMD / tests."""
    configure_logging()
    configure_tracing(
        service_name="resumerank-backend",
        otlp_endpoint=os.environ.get("OTLP_ENDPOINT"),
    )

    app = FastAPI(
        title="ResumeRank Pro",
        description="Production ATS scoring API – Hexagonal Architecture",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # CORS – Allow mobile devices on local network
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

    # Routes
    app.include_router(analyze.router, prefix="/v1")
    app.include_router(status_route.router, prefix="/v1")
    app.include_router(health.router, prefix="/v1")
    app.include_router(gdpr.router, prefix="/v1")
    app.include_router(skills_route.router, prefix="/v1")
    app.include_router(rewrite.router, prefix="/v1")
    app.include_router(insights.router, prefix="/v1")
    app.include_router(auth.router, prefix="/v1")

    # Prometheus metrics endpoint (separate port in K8s is best practice;
    # here we mount at /metrics for Cloud Run simplicity)
    metrics_app = make_asgi_app()
    app.mount("/metrics", metrics_app)

    instrument_app(app)

    return app


# Entrypoint for uvicorn
app = create_app()
