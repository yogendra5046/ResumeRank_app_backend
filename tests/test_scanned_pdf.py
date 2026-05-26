"""Tests: scanned/image-only PDF handling."""
from __future__ import annotations

import io

import fitz
import pytest

from src.application.use_cases.analyze_resume import AnalyzeResumeUseCase
from src.domain.services.scoring_service import ScoringService
from src.infrastructure.jobs.job_store import JobStore
from src.infrastructure.pdf.pymupdf_extractor import PyMuPdfExtractor


def _make_image_only_pdf() -> bytes:
    """Create a PDF with only a rendered image (no text layer)."""
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    # Draw a rectangle to simulate scanned content (no searchable text)
    page.draw_rect(fitz.Rect(50, 50, 545, 792), color=(0, 0, 0), fill=(0.95, 0.95, 0.95))
    buf = io.BytesIO()
    doc.save(buf)
    doc.close()
    return buf.getvalue()


@pytest.mark.asyncio
@pytest.mark.unit
async def test_image_only_pdf_extracts_empty_text() -> None:
    """Image-only PDFs produce empty text (no crash)."""
    extractor = PyMuPdfExtractor()
    pdf_bytes = _make_image_only_pdf()
    text = await extractor.extract(pdf_bytes)
    # May be empty or contain minimal whitespace
    assert isinstance(text, str)


@pytest.mark.asyncio
@pytest.mark.unit
async def test_scanned_pdf_rejected_by_pipeline(
    mock_scanner: object,
    mock_cache: object,
    mock_embedder: object,
    mock_skill_graph: object,
    mock_job_store: JobStore,
    scoring_service: ScoringService,
) -> None:
    """A scanned PDF with no extractable text must raise ValueError in pipeline."""
    from unittest.mock import AsyncMock

    extractor = AsyncMock(spec=PyMuPdfExtractor)
    extractor.extract.return_value = "   "  # whitespace only

    use_case = AnalyzeResumeUseCase(
        scanner=mock_scanner,  # type: ignore[arg-type]
        extractor=extractor,
        embedder=mock_embedder,  # type: ignore[arg-type]
        cache=mock_cache,  # type: ignore[arg-type]
        skill_graph=mock_skill_graph,  # type: ignore[arg-type]
        job_store=mock_job_store,
        scoring_service=scoring_service,
    )

    with pytest.raises(ValueError, match="No text extracted"):
        await use_case.execute(
            pdf_bytes=_make_image_only_pdf(),
            filename="scanned.pdf",
            raw_jd="We need a Python engineer with 5 years experience in FastAPI and SQL.",
            trace_id="test-trace-scanned",
            base_url="http://localhost",
        )


@pytest.mark.asyncio
@pytest.mark.unit
async def test_malware_pdf_rejected(
    mock_cache: object,
    mock_embedder: object,
    mock_skill_graph: object,
    mock_job_store: JobStore,
    scoring_service: ScoringService,
) -> None:
    """ClamAV-detected threat must raise ValueError before any processing."""
    from unittest.mock import AsyncMock

    from src.domain.ports.scanner import ScanResult, ScannerPort

    infected_scanner = AsyncMock(spec=ScannerPort)
    infected_scanner.scan.return_value = ScanResult(
        is_clean=False, threat_name="Eicar-Signature"
    )

    use_case = AnalyzeResumeUseCase(
        scanner=infected_scanner,
        extractor=PyMuPdfExtractor(),
        embedder=mock_embedder,  # type: ignore[arg-type]
        cache=mock_cache,  # type: ignore[arg-type]
        skill_graph=mock_skill_graph,  # type: ignore[arg-type]
        job_store=mock_job_store,
        scoring_service=scoring_service,
    )

    with pytest.raises(ValueError, match="malware detected"):
        await use_case.execute(
            pdf_bytes=b"%PDF-1.4 fake",
            filename="evil.pdf",
            raw_jd="Senior Python engineer needed.",
            trace_id="test-trace-malware",
            base_url="http://localhost",
        )
