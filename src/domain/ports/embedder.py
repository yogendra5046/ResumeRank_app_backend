"""Domain port: text embedding abstraction."""
from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np
import numpy.typing as npt


class EmbedderPort(ABC):
    """Hexagonal port – produce dense vector embeddings from text.

    Implementations: MiniLM INT8 (primary), TF-IDF (circuit-breaker fallback).
    """

    @abstractmethod
    async def embed(self, text: str) -> npt.NDArray[np.float32]:
        """Return a normalised L2 embedding for *text*.

        Shape: (embedding_dim,)  — typically (384,) for MiniLM-L6.
        Vector is always L2-normalised so dot-product == cosine similarity.

        Raises:
            EmbedderError: On model failure (triggers circuit breaker).
        """

    @property
    @abstractmethod
    def model_version(self) -> str:
        """Human-readable model identifier for audit logs."""


class EmbedderError(Exception):
    """Raised when embedding fails; triggers circuit-breaker logic."""
