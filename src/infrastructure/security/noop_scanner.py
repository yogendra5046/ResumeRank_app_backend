"""Infrastructure: No-op scanner adapter (fallback)."""
from __future__ import annotations

from src.domain.ports.scanner import ScanResult, ScannerPort


class NoOpScanner(ScannerPort):
    """Bypasses malware scanning – always returns clean."""

    async def scan(self, data: bytes, filename: str) -> ScanResult:
        return ScanResult(is_clean=True, threat_name=None)
