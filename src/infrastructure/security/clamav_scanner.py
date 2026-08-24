"""Infrastructure: ClamAV malware scanner adapter.

Uses clamd (Unix socket or TCP) to scan PDF bytes before any processing.
Fail-closed: if ClamAV is unreachable, the request is rejected.
"""
from __future__ import annotations

import asyncio
import functools
from concurrent.futures import ThreadPoolExecutor

import clamd
import structlog

from src.domain.ports.scanner import ScanResult, ScannerPort, ScannerUnavailableError

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)

_EXECUTOR = ThreadPoolExecutor(max_workers=2, thread_name_prefix="clamav-worker")


class ClamAvScanner(ScannerPort):
    """Async ClamAV scanner – connects via TCP to clamd daemon."""

    def __init__(self, host: str, port: int, timeout: float = 30.0) -> None:
        self._host = host
        self._port = port
        self._timeout = timeout

    def _get_client(self) -> clamd.ClamdNetworkSocket:
        return clamd.ClamdNetworkSocket(
            host=self._host,
            port=self._port,
            timeout=self._timeout,
        )

    def _scan_sync(self, data: bytes, filename: str) -> ScanResult:
        try:
            client = self._get_client()
            result = client.instream(iter([data]))
            # result = {'stream': ('OK', None)} or {'stream': ('FOUND', 'Eicar-Signature')}
            status, threat = result.get("stream", ("ERROR", "no-response"))
        except clamd.ConnectionError as exc:
            raise ScannerUnavailableError(
                f"ClamAV at {self._host}:{self._port} is unreachable: {exc}"
            ) from exc
        except Exception as exc:
            raise ScannerUnavailableError(f"ClamAV unexpected error: {exc}") from exc

        is_clean = status == "OK"
        if not is_clean:
            logger.warning(
                "clamav_threat_found",
                filename=filename,
                threat=threat,
                status=status,
            )
        return ScanResult(is_clean=is_clean, threat_name=threat if not is_clean else None)

    async def scan(self, data: bytes, filename: str) -> ScanResult:
        loop = asyncio.get_running_loop()
        result: ScanResult = await loop.run_in_executor(
            _EXECUTOR,
            functools.partial(self._scan_sync, data, filename),
        )
        return result
