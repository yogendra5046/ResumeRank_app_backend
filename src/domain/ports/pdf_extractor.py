"""Domain port: PDF text extraction abstraction."""
from __future__ import annotations

from abc import ABC, abstractmethod


class PdfExtractorPort(ABC):
    """Hexagonal port – extract plain text from PDF bytes.

    Implementations live in infrastructure/pdf/.
    The domain layer depends only on this ABC; never on fitz/pdfplumber.
    """

    @abstractmethod
    async def extract(self, pdf_bytes: bytes) -> str:
        """Extract all text from *pdf_bytes*.

        Args:
            pdf_bytes: Raw bytes of a PDF file.

        Returns:
            Plain-text content. May be empty for scanned/image-only PDFs.

        Raises:
            PdfExtractionError: When the PDF is corrupt or unreadable.
        """


class PdfExtractionError(Exception):
    """Raised when text extraction fails for any reason."""
