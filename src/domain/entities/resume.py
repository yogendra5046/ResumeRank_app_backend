"""Domain entity: Resume aggregate root."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Final

_MAX_PDF_BYTES: Final[int] = 10 * 1024 * 1024  # 10 MB hard limit


@dataclass(frozen=True, slots=True)
class Resume:
    """Immutable aggregate root for a submitted resume.

    Holds raw PDF bytes and derived metadata. Business rules are enforced
    at construction time; no setters exist (frozen dataclass).
    """

    pdf_bytes: bytes
    filename: str
    sha256: str = field(init=False)

    def __post_init__(self) -> None:
        if not self.pdf_bytes:
            raise ValueError("PDF bytes must not be empty")
        if len(self.pdf_bytes) > _MAX_PDF_BYTES:
            raise ValueError(
                f"PDF exceeds maximum allowed size of {_MAX_PDF_BYTES // (1024 * 1024)} MB"
            )
        if not self.filename.lower().endswith(".pdf"):
            raise ValueError(f"Only PDF files are accepted; got '{self.filename}'")
        # Bypass frozen via object.__setattr__ for computed field
        object.__setattr__(self, "sha256", self._compute_sha256())

    def _compute_sha256(self) -> str:
        return hashlib.sha256(self.pdf_bytes).hexdigest()

    @property
    def size_bytes(self) -> int:
        return len(self.pdf_bytes)

    @property
    def is_large(self) -> bool:
        """True when >5 MB – triggers async job path (202 response)."""
        return self.size_bytes > 5 * 1024 * 1024
