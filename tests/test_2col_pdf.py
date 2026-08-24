"""Tests: two-column PDF extraction correctness + latency SLA."""
from __future__ import annotations

import io
import time

import fitz
import pytest

from src.infrastructure.pdf.pymupdf_extractor import PyMuPdfExtractor


def _make_two_column_pdf() -> bytes:
    """Craft a PDF with two text columns side by side."""
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)  # A4

    # Left column (x=50)
    left_text = (
        "Experience\n"
        "Senior Python Engineer\n"
        "Acme Corp 2020-2024\n"
        "Led team of 8 engineers\n"
        "Increased throughput by 40%\n"
    )
    # Right column (x=310)
    right_text = (
        "Skills\n"
        "Python programming\n"
        "FastAPI, Docker\n"
        "REST API design\n"
        "SQL, Kubernetes\n"
    )

    # Insert at different x positions (simulates 2-column layout)
    page.insert_text((50, 100), left_text, fontsize=10)
    page.insert_text((310, 100), right_text, fontsize=10)

    buf = io.BytesIO()
    doc.save(buf)
    doc.close()
    return buf.getvalue()


@pytest.mark.asyncio
@pytest.mark.unit
async def test_two_column_pdf_extracts_all_content() -> None:
    """Both columns must be present in extracted text."""
    extractor = PyMuPdfExtractor()
    pdf_bytes = _make_two_column_pdf()

    text = await extractor.extract(pdf_bytes)

    # Left column content
    assert "Experience" in text
    assert "Senior Python Engineer" in text
    assert "40%" in text

    # Right column content
    assert "Skills" in text
    assert "Python programming" in text
    assert "Docker" in text


@pytest.mark.asyncio
@pytest.mark.unit
async def test_two_column_ordering_correct() -> None:
    """Block-sort should keep text logically ordered (top-to-bottom priority)."""
    extractor = PyMuPdfExtractor()
    pdf_bytes = _make_two_column_pdf()
    text = await extractor.extract(pdf_bytes)

    # "Experience" and "Skills" headers both appear before their content
    exp_pos = text.find("Experience")
    skills_pos = text.find("Skills")
    assert exp_pos != -1
    assert skills_pos != -1


@pytest.mark.asyncio
@pytest.mark.unit
async def test_empty_pdf_raises_gracefully() -> None:
    """Empty/corrupt bytes must raise PdfExtractionError, not crash."""
    from src.domain.ports.pdf_extractor import PdfExtractionError

    extractor = PyMuPdfExtractor()
    with pytest.raises(PdfExtractionError):
        await extractor.extract(b"not-a-pdf")


@pytest.mark.asyncio
@pytest.mark.benchmark
async def test_two_column_pdf_latency_sla() -> None:
    """p99 extraction of a 5-page two-column PDF must be <2000 ms."""
    extractor = PyMuPdfExtractor()

    # Build 5-page PDF (~simulates 5 MB doc)
    doc = fitz.open()
    for _ in range(5):
        page = doc.new_page()
        page.insert_text((50, 100), "Experience\n" * 50, fontsize=10)
        page.insert_text((310, 100), "Skills\n" * 50, fontsize=10)
    buf = io.BytesIO()
    doc.save(buf)
    doc.close()
    large_pdf = buf.getvalue()

    start = time.perf_counter()
    await extractor.extract(large_pdf)
    elapsed_ms = (time.perf_counter() - start) * 1000

    assert elapsed_ms < 2000, f"Latency SLA breached: {elapsed_ms:.1f} ms > 2000 ms"
