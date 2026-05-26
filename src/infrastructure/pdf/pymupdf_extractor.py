"""Infrastructure: async PyMuPDF PDF text extractor.

Runs fitz (PyMuPDF) in a thread-pool executor so the event loop is never
blocked during CPU-bound page rendering. Handles both text-layer and
multi-column layout via block sorting by (y0, x0).
"""
from __future__ import annotations

import asyncio
import functools
from concurrent.futures import ThreadPoolExecutor

import fitz  # PyMuPDF

import structlog

from src.domain.ports.pdf_extractor import PdfExtractionError, PdfExtractorPort

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)

# One executor shared across all requests; sized to CPU count
_EXECUTOR = ThreadPoolExecutor(max_workers=4, thread_name_prefix="pdf-worker")


def _extract_sync(pdf_bytes: bytes) -> str:
    """Synchronous extraction – runs in thread pool, never on event loop."""
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")  # type: ignore[call-arg]
    except Exception as exc:
        raise PdfExtractionError(f"Cannot open PDF: {exc}") from exc

    pages: list[str] = []
    for page_num in range(doc.page_count):
        page = doc.load_page(page_num)
        # get_text("blocks") → list[(x0,y0,x1,y1,text,block_no,block_type)]
        blocks = page.get_text("blocks")  # type: ignore[call-arg]
        # Sort top-to-bottom then left-to-right (handles 2-column layouts)
        blocks_sorted = sorted(blocks, key=lambda b: (round(b[1] / 12), b[0]))
        page_text = "\n".join(b[4].strip() for b in blocks_sorted if b[6] == 0)
        pages.append(page_text)

    doc.close()
    return "\n\n".join(pages)


class PyMuPdfExtractor(PdfExtractorPort):
    """Async adapter around PyMuPDF – implements PdfExtractorPort."""

    async def extract(self, pdf_bytes: bytes) -> str:
        loop = asyncio.get_running_loop()
        try:
            text: str = await loop.run_in_executor(
                _EXECUTOR,
                functools.partial(_extract_sync, pdf_bytes),
            )
        except PdfExtractionError:
            raise
        except Exception as exc:
            logger.error("pymupdf_unexpected_error", error=str(exc))
            raise PdfExtractionError(f"Unexpected extraction error: {exc}") from exc

        logger.debug("pdf_extracted", chars=len(text))
        return text
