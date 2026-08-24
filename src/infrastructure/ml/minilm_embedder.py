"""Infrastructure: INT8-quantized MiniLM embedder with circuit breaker.

Primary embedder: sentence-transformers/all-MiniLM-L6-v2 quantized to INT8
via torch.quantization.quantize_dynamic (CPU-friendly, ~4× memory reduction).

Circuit breaker (tenacity):
  - 3 consecutive failures → OPEN state
  - Falls back to TfIdfFallbackEmbedder
  - Logs CRITICAL on first fallback activation
"""
from __future__ import annotations

import asyncio
import functools
import logging
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import numpy.typing as npt
import structlog
import torch
from sentence_transformers import SentenceTransformer
from tenacity import (
    RetryCallState,
    RetryError,
    Retrying,
    stop_after_attempt,
    wait_exponential,
)

from src.domain.ports.embedder import EmbedderError, EmbedderPort
from src.infrastructure.ml.tfidf_fallback import TfIdfFallbackEmbedder
from src.infrastructure.telemetry.metrics import ATS_CIRCUIT_BREAKER_OPEN

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)

_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
_EXECUTOR = ThreadPoolExecutor(max_workers=2, thread_name_prefix="ml-worker")
_FAILURE_THRESHOLD = 3


def _build_quantized_model() -> SentenceTransformer:
    """Load and INT8-quantize the MiniLM model at startup."""
    model = SentenceTransformer(_MODEL_NAME)
    # Quantize all Linear layers to INT8 (dynamic quantization – CPU only)
    model[0].auto_model = torch.quantization.quantize_dynamic(  # type: ignore[attr-defined]
        model[0].auto_model,
        {torch.nn.Linear},
        dtype=torch.qint8,
    )
    model.eval()
    return model


class MiniLmEmbedder(EmbedderPort):
    """Production INT8-quantized MiniLM embedder with circuit breaker."""

    def __init__(self, fallback: TfIdfFallbackEmbedder) -> None:
        self._fallback = fallback
        self._model: SentenceTransformer | None = None
        self._consecutive_failures: int = 0
        self._circuit_open: bool = False

    async def warm_up(self) -> None:
        """Load model eagerly at app startup (not on first request)."""
        loop = asyncio.get_running_loop()
        self._model = await loop.run_in_executor(_EXECUTOR, _build_quantized_model)
        logger.info("minilm_loaded", model=_MODEL_NAME, quantized=True)

    @property
    def model_version(self) -> str:
        if self._circuit_open:
            return self._fallback.model_version
        return f"{_MODEL_NAME}-int8"

    async def embed(self, text: str) -> npt.NDArray[np.float32]:
        if self._circuit_open:
            return await self._fallback.embed(text)

        try:
            return await self._embed_primary(text)
        except EmbedderError:
            self._consecutive_failures += 1
            if self._consecutive_failures >= _FAILURE_THRESHOLD:
                self._circuit_open = True
                ATS_CIRCUIT_BREAKER_OPEN.set(1)
                logger.critical(
                    "circuit_breaker_opened",
                    failures=self._consecutive_failures,
                    fallback=self._fallback.model_version,
                )
            return await self._fallback.embed(text)

    async def _embed_primary(self, text: str) -> npt.NDArray[np.float32]:
        if self._model is None:
            await self.warm_up()

        loop = asyncio.get_running_loop()
        try:
            vec: npt.NDArray[np.float32] = await loop.run_in_executor(
                _EXECUTOR,
                functools.partial(self._encode_sync, text),
            )
        except Exception as exc:
            logger.error("minilm_embed_failed", error=str(exc))
            raise EmbedderError(str(exc)) from exc

        self._consecutive_failures = 0  # Reset on success
        return vec

    def _encode_sync(self, text: str) -> npt.NDArray[np.float32]:
        assert self._model is not None  # noqa: S101
        with torch.no_grad():
            vec = self._model.encode(
                text,
                normalize_embeddings=True,
                convert_to_numpy=True,
                show_progress_bar=False,
            )
        return vec.astype(np.float32)  # type: ignore[return-value]
