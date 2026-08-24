"""Infrastructure: async PyMuPDF PDF text extractor.

Runs fitz (PyMuPDF) in a thread-pool executor so the event loop is never
blocked during CPU-bound page rendering. Handles both text-layer and
multi-column layout via block sorting by (y0, x0).
"""
from __future__ import annotations

import asyncio
import functools
import base64
import os
import re
from concurrent.futures import ThreadPoolExecutor

import fitz  # PyMuPDF
import httpx
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

        # Scanned PDF / empty text layer fallback to Groq Vision OCR
        # Skip this fallback if running in pytest to avoid executing network calls
        if (not text or len(text.strip()) < 50) and "PYTEST_CURRENT_TEST" not in os.environ:
            logger.info("pymupdf_empty_or_low_text_layer_falling_back_to_groq_ocr")
            ocr_text = await self._ocr_scanned_pdf(pdf_bytes)
            if ocr_text.strip():
                text = ocr_text

        logger.debug("pdf_extracted", chars=len(text))
        return text

    async def _ocr_scanned_pdf(self, pdf_bytes: bytes) -> str:
        try:
            # 1. Open PDF and render pages to base64 images
            loop = asyncio.get_running_loop()
            
            def render_pdf_to_images(data):
                doc = fitz.open(stream=data, filetype="pdf")
                images = []
                # Limit to first 5 pages to avoid large payloads / API limits
                for page_num in range(min(doc.page_count, 5)):
                    page = doc.load_page(page_num)
                    # Use a moderate resolution matrix for clear text without huge files
                    zoom = 1.5
                    mat = fitz.Matrix(zoom, zoom)
                    pix = page.get_pixmap(matrix=mat)
                    png_bytes = pix.tobytes("png")
                    images.append(base64.b64encode(png_bytes).decode("utf-8"))
                doc.close()
                return images

            base64_images = await loop.run_in_executor(
                _EXECUTOR,
                functools.partial(render_pdf_to_images, pdf_bytes),
            )

            if not base64_images:
                return ""

            # 2. Call Groq for each page in parallel
            groq_key = os.environ.get("GROQ_API_KEY", "").strip()
            if not groq_key:
                logger.warning("groq_ocr_skipped_key_missing")
                return ""

            async def ocr_page(client: httpx.AsyncClient, b64_img: str, idx: int) -> str:
                url = "https://api.groq.com/openai/v1/chat/completions"
                headers = {
                    "Authorization": f"Bearer {groq_key}",
                    "Content-Type": "application/json"
                }
                payload = {
                    "model": "qwen/qwen3.6-27b",
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text", 
                                    "text": "Extract all text from this scanned resume page verbatim. Do not add any conversational text. Return only the text content."
                                },
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/png;base64,{b64_img}"
                                    }
                                }
                            ]
                        }
                    ],
                    "temperature": 0.1,
                    "max_tokens": 1500
                }
                
                try:
                    response = await client.post(url, headers=headers, json=payload, timeout=60.0)
                    if response.status_code == 200:
                        res_json = response.json()
                        content = res_json["choices"][0]["message"]["content"]
                        # Clean up thinking block if present
                        content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()
                        return content
                    else:
                        logger.warning("groq_ocr_page_error", page=idx, status=response.status_code, error=response.text)
                        return ""
                except Exception as e:
                    logger.warning("groq_ocr_page_exception", page=idx, error=str(e))
                    return ""

            async with httpx.AsyncClient() as client:
                tasks = [ocr_page(client, img, i) for i, img in enumerate(base64_images)]
                page_texts = await asyncio.gather(*tasks)

            # Filter out empty pages and join
            valid_texts = [text for text in page_texts if text]
            return "\n\n".join(valid_texts)

        except Exception as e:
            logger.error("groq_ocr_pipeline_failed", error=str(e))
            return ""

