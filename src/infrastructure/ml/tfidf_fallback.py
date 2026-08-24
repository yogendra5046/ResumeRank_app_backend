"""Infrastructure: TF-IDF fallback embedder (circuit-breaker secondary).

Activated only when MiniLM fails 3 consecutive times.
Produces L2-normalised dense vectors from TF-IDF sparse representation
projected to 384 dims via a fixed random projection matrix (seeded).
This guarantees the same output dimension as MiniLM for downstream FAISS.
"""
from __future__ import annotations

import asyncio
import functools
import hashlib
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import numpy.typing as npt
import structlog
from sklearn.feature_extraction.text import TfidfVectorizer

from src.domain.ports.embedder import EmbedderPort

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)

_TARGET_DIM = 384          # Must match MiniLM output dim
_TFIDF_MAX_FEATURES = 8192
_PROJECTION_SEED = 42
_EXECUTOR = ThreadPoolExecutor(max_workers=2, thread_name_prefix="tfidf-worker")


class TfIdfFallbackEmbedder(EmbedderPort):
    """TF-IDF → random projection fallback.

    Stateful TfidfVectorizer is fitted lazily on the first call.
    The random projection matrix R is fixed (seeded) so embeddings are
    consistent across restarts within the same process lifetime.
    """

    def __init__(self) -> None:
        self._vectorizer = TfidfVectorizer(
            max_features=_TFIDF_MAX_FEATURES,
            sublinear_tf=True,
            strip_accents="unicode",
        )
        self._rng = np.random.default_rng(_PROJECTION_SEED)
        # Lazy-initialised after first fit
        self._projection: npt.NDArray[np.float32] | None = None
        self._fitted = False
        self._corpus: list[str] = []

    @property
    def model_version(self) -> str:
        return "tfidf-random-projection-fallback"

    async def embed(self, text: str) -> npt.NDArray[np.float32]:
        loop = asyncio.get_running_loop()
        vec: npt.NDArray[np.float32] = await loop.run_in_executor(
            _EXECUTOR,
            functools.partial(self._embed_sync, text),
        )
        return vec

    def _embed_sync(self, text: str) -> npt.NDArray[np.float32]:
        if not self._fitted:
            self._corpus.append(text)
            self._vectorizer.fit(self._corpus)
            self._fitted = True
            n_features = len(self._vectorizer.vocabulary_)
            self._projection = self._rng.standard_normal(
                (n_features, _TARGET_DIM)
            ).astype(np.float32)
            logger.warning(
                "tfidf_fallback_fitted",
                vocab_size=n_features,
                target_dim=_TARGET_DIM,
            )

        sparse = self._vectorizer.transform([text])
        dense = sparse.toarray().astype(np.float32)

        assert self._projection is not None  # noqa: S101
        projected = dense @ self._projection[:dense.shape[1]]
        # L2 normalise
        norm = np.linalg.norm(projected)
        if norm > 0:
            projected = projected / norm
        return projected.squeeze().astype(np.float32)
