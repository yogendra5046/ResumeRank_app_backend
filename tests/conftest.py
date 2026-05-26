"""Shared pytest fixtures for the full test suite."""
from __future__ import annotations

import gzip
import io
import json
from pathlib import Path
from typing import AsyncIterator
from unittest.mock import AsyncMock, MagicMock

import fitz
import numpy as np
import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

from src.domain.ports.cache_repository import CacheRepositoryPort
from src.domain.ports.embedder import EmbedderPort
from src.domain.ports.pdf_extractor import PdfExtractorPort
from src.domain.ports.scanner import ScanResult, ScannerPort
from src.domain.ports.skill_graph import SkillGraphPort, SkillMatchResult
from src.domain.services.scoring_service import ScoringService
from src.infrastructure.jobs.job_store import JobStore
from src.infrastructure.ml.tfidf_fallback import TfIdfFallbackEmbedder
from src.infrastructure.skills.esco_loader import EscoSkill, EscoTaxonomy
from src.presentation.app import create_app

# ── Tiny ESCO fixture ──────────────────────────────────────────────────────────
_ESCO_SKILLS = [
    {
        "uri": f"http://data.europa.eu/esco/skill/{i:04d}",
        "preferredLabel": {"en": label},
        "altLabels": {"en": [label.lower()]},
        "broaderUri": [],
    }
    for i, label in enumerate(
        [
            "Python programming", "Java programming", "SQL", "machine learning",
            "data analysis", "communication", "project management", "leadership",
            "JavaScript", "TypeScript", "Docker", "Kubernetes", "FastAPI",
            "REST API design", "agile methodology", "cloud computing",
            "AWS", "GCP", "Azure", "CI/CD pipelines",
        ]
        * 160  # 3200 total to satisfy ≥3000 requirement
    )
]


@pytest.fixture(scope="session")
def esco_taxonomy() -> EscoTaxonomy:
    taxonomy = EscoTaxonomy()
    for entry in _ESCO_SKILLS:
        uri = entry["uri"]
        label = entry["preferredLabel"]["en"]
        skill = EscoSkill(
            uri=uri,
            preferred_label=label,
            alt_labels=frozenset(a.lower() for a in entry["altLabels"]["en"]),
            broader_uris=(),
        )
        taxonomy.skills_by_uri[uri] = skill
        taxonomy.label_to_uri[label.lower()] = uri
    return taxonomy


@pytest.fixture
def clean_scan_result() -> ScanResult:
    return ScanResult(is_clean=True, threat_name=None)


@pytest.fixture
def mock_scanner(clean_scan_result: ScanResult) -> ScannerPort:
    scanner = AsyncMock(spec=ScannerPort)
    scanner.scan.return_value = clean_scan_result
    return scanner


@pytest.fixture
def mock_cache() -> CacheRepositoryPort:
    cache = AsyncMock(spec=CacheRepositoryPort)
    cache.get.return_value = None  # default: cache miss
    cache.set.return_value = None
    cache.delete.return_value = None
    cache.ping.return_value = True
    return cache


@pytest.fixture
def mock_embedder() -> EmbedderPort:
    embedder = AsyncMock(spec=EmbedderPort)
    embedder.embed.return_value = np.random.default_rng(42).random(384).astype(np.float32)
    embedder.model_version = "test-minilm-int8"
    return embedder


@pytest.fixture
def mock_skill_graph() -> SkillGraphPort:
    graph = AsyncMock(spec=SkillGraphPort)
    graph.match.return_value = SkillMatchResult(
        matched=("Python programming", "SQL"),
        missing=("Kubernetes",),
        graph_weight=0.75,
    )
    graph.skill_count = 3200
    return graph


@pytest.fixture
def mock_job_store() -> JobStore:
    store = AsyncMock(spec=JobStore)
    store.enqueue.return_value = "01HX1234567890ABCDEFGHIJKL"
    return store


@pytest.fixture
def scoring_service() -> ScoringService:
    return ScoringService()


def _make_single_page_pdf(text: str) -> bytes:
    """Create an in-memory single-page PDF containing *text*."""
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), text, fontsize=11)
    buf = io.BytesIO()
    doc.save(buf)
    doc.close()
    return buf.getvalue()


@pytest.fixture
def simple_resume_pdf() -> bytes:
    return _make_single_page_pdf(
        "John Doe\njohn@example.com\n+1-555-0100\n\n"
        "Experience\nSenior Python Engineer at Acme Corp 2020-2024\n"
        "Increased API throughput by 40%. Led team of 8 engineers.\n"
        "Built CI/CD pipelines on GCP. Reduced deploy time by 60%.\n\n"
        "Skills\nPython programming, SQL, FastAPI, Docker, REST API design\n\n"
        "Education\nB.Sc. Computer Science, MIT 2019\n\n"
        "Contact\njohn@example.com\n\n"
        "Summary\nProduction-grade backend engineer with 5 years experience."
    )


@pytest.fixture
def sample_jd() -> str:
    return (
        "We are looking for a Senior Python Engineer with experience in "
        "FastAPI, SQL, Docker, Kubernetes, and REST API design. "
        "Must have strong communication and project management skills. "
        "GCP cloud computing experience preferred. Minimum 5 years experience."
    )


# ── App + async HTTP client ────────────────────────────────────────────────────

@pytest.fixture
def app_with_mocks(
    mock_scanner: ScannerPort,
    mock_cache: CacheRepositoryPort,
    mock_embedder: EmbedderPort,
    mock_skill_graph: SkillGraphPort,
    mock_job_store: JobStore,
    esco_taxonomy: EscoTaxonomy,
) -> object:
    """Create FastAPI app with all infrastructure replaced by mocks."""
    from src.infrastructure.cache.redis_cache import RedisCacheAdapter
    from src.infrastructure.ml.minilm_embedder import MiniLmEmbedder

    app = create_app.__wrapped__() if hasattr(create_app, "__wrapped__") else create_app()

    # Override app.state directly (no lifespan in test)
    app.state.redis = MagicMock()
    app.state.cache_adapter = mock_cache
    app.state.taxonomy = esco_taxonomy
    app.state.scanner = mock_scanner
    app.state.embedder = mock_embedder
    app.state.job_store = mock_job_store

    return app


@pytest_asyncio.fixture
async def async_client(app_with_mocks: object) -> AsyncIterator[AsyncClient]:
    async with AsyncClient(
        transport=ASGITransport(app=app_with_mocks),  # type: ignore[arg-type]
        base_url="http://test",
        headers={"X-API-Key": "test-key-12345"},
    ) as client:
        yield client
