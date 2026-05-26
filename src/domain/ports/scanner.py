"""Domain port: malware scanner abstraction."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ScanResult:
    """Outcome of a ClamAV scan."""

    is_clean: bool
    threat_name: str | None  # None when clean


class ScannerPort(ABC):
    """Hexagonal port – scan raw bytes for malware before processing.

    Backed by ClamAV in infrastructure. Rejects macros and executables.
    OWASP best-practice: scan before any parsing/extraction.
    """

    @abstractmethod
    async def scan(self, data: bytes, filename: str) -> ScanResult:
        """Scan *data* bytes.

        Args:
            data: Raw file bytes.
            filename: Original filename for logging.

        Returns:
            ScanResult with is_clean=True if no threat found.

        Raises:
            ScannerUnavailableError: When ClamAV daemon is unreachable.
        """


class ScannerUnavailableError(Exception):
    """Raised when ClamAV is unreachable; request should be rejected (fail-closed)."""
