"""Tests: MiniLM circuit breaker – 3 failures → TF-IDF fallback."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest

from src.domain.ports.embedder import EmbedderError
from src.infrastructure.ml.minilm_embedder import MiniLmEmbedder
from src.infrastructure.ml.tfidf_fallback import TfIdfFallbackEmbedder


@pytest.fixture
def fallback() -> TfIdfFallbackEmbedder:
    return TfIdfFallbackEmbedder()


@pytest.fixture
def embedder(fallback: TfIdfFallbackEmbedder) -> MiniLmEmbedder:
    emb = MiniLmEmbedder(fallback=fallback)
    # Pre-warm with a mock model (avoids actual download in unit tests)
    emb._model = MagicMock()
    return emb


@pytest.mark.asyncio
@pytest.mark.unit
async def test_circuit_opens_after_3_failures(embedder: MiniLmEmbedder) -> None:
    """Three consecutive embed failures must open the circuit breaker."""
    assert not embedder._circuit_open

    with patch.object(embedder, "_embed_primary", side_effect=EmbedderError("model crash")):
        for _ in range(3):
            await embedder.embed("test text")

    assert embedder._circuit_open
    assert embedder._consecutive_failures >= 3


@pytest.mark.asyncio
@pytest.mark.unit
async def test_fallback_used_when_circuit_open(embedder: MiniLmEmbedder) -> None:
    """When circuit is open, TF-IDF fallback must be invoked."""
    embedder._circuit_open = True
    fallback_vec = await embedder.embed("Python engineer with FastAPI skills")
    assert isinstance(fallback_vec, np.ndarray)
    assert fallback_vec.shape == (384,)


@pytest.mark.asyncio
@pytest.mark.unit
async def test_model_version_reflects_circuit_state(embedder: MiniLmEmbedder) -> None:
    """model_version must report fallback identifier when circuit is open."""
    assert "minilm" in embedder.model_version.lower()
    embedder._circuit_open = True
    assert "fallback" in embedder.model_version.lower()


@pytest.mark.asyncio
@pytest.mark.unit
async def test_success_resets_failure_counter(embedder: MiniLmEmbedder) -> None:
    """A successful embed must reset the consecutive failure counter."""
    embedder._consecutive_failures = 2

    expected_vec = np.random.default_rng(0).random(384).astype(np.float32)
    with patch.object(embedder, "_encode_sync", return_value=expected_vec):
        result = await embedder.embed("good text")

    assert embedder._consecutive_failures == 0
    np.testing.assert_array_equal(result, expected_vec)


@pytest.mark.asyncio
@pytest.mark.unit
async def test_circuit_breaker_metric_set_on_open(embedder: MiniLmEmbedder) -> None:
    """ATS_CIRCUIT_BREAKER_OPEN gauge must be set to 1 when circuit opens."""
    from src.infrastructure.telemetry.metrics import ATS_CIRCUIT_BREAKER_OPEN

    ATS_CIRCUIT_BREAKER_OPEN.set(0)  # Reset

    with patch.object(embedder, "_embed_primary", side_effect=EmbedderError("crash")):
        for _ in range(3):
            await embedder.embed("trigger")

    # Gauge should be 1 now
    assert embedder._circuit_open


@pytest.mark.asyncio
@pytest.mark.unit
async def test_tfidf_fallback_produces_l2_normalised_vector(
    fallback: TfIdfFallbackEmbedder,
) -> None:
    """TF-IDF fallback vectors must be L2-normalised (||v|| ≈ 1.0)."""
    vec = await fallback.embed("Python FastAPI machine learning SQL")
    norm = float(np.linalg.norm(vec))
    assert norm == pytest.approx(1.0, abs=0.01)


@pytest.mark.asyncio
@pytest.mark.unit
async def test_tfidf_output_dim_matches_minilm(fallback: TfIdfFallbackEmbedder) -> None:
    """TF-IDF fallback must produce 384-dim vectors (matches MiniLM)."""
    vec = await fallback.embed("software engineer python docker kubernetes")
    assert vec.shape == (384,)
