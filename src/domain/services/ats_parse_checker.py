"""Domain service: ATS parseability checker."""
from __future__ import annotations

import io
import asyncio
import functools
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Any

import pdfplumber

# Shared executor for CPU-bound PDF parsing
_EXECUTOR = ThreadPoolExecutor(max_workers=2, thread_name_prefix="ats-checker")

class AtsParseChecker:
    """Checks PDF for common ATS parsing issues (tables, images, columns)."""

    async def check(self, pdf_bytes: bytes) -> Dict[str, Any]:
        """Runs checks in a thread pool to avoid blocking the event loop."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            _EXECUTOR,
            functools.partial(self._check_sync, pdf_bytes)
        )

    def _check_sync(self, pdf_bytes: bytes) -> Dict[str, Any]:
        """Synchronous check implementation using pdfplumber."""
        score = 100
        issues = []
        
        try:
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    # 1. Check for tables
                    tables = page.find_tables()
                    if tables:
                        msg = f"Table detected on page {page_num} - some ATS may fail to parse correctly"
                        if msg not in issues:
                            issues.append(msg)
                            score -= 15

                    # 2. Check for images
                    if page.images:
                        msg = f"Image detected on page {page_num} - text inside images is often not readable"
                        if msg not in issues:
                            issues.append(msg)
                            score -= 10

                    # 3. Check for multi-column layout
                    if self._is_multi_column(page):
                        msg = f"Multi-column layout detected on page {page_num} - can cause incorrect reading order"
                        if msg not in issues:
                            issues.append(msg)
                            score -= 10
                            
        except Exception as exc:
            return {"score": 0, "issues": [f"Failed to analyze PDF structure: {str(exc)}"]}

        return {
            "score": max(0, score),
            "issues": issues
        }

    def _is_multi_column(self, page: pdfplumber.page.Page) -> bool:
        """Heuristic to detect multi-column layout via character x-coordinates."""
        words = page.extract_words()
        if not words:
            return False
        
        # Look for large horizontal gaps between words on the same vertical line
        # This is a simplified heuristic
        x_coords = sorted([w['x0'] for w in words])
        # If we have distinct clusters of x0 coordinates, it might be multi-column
        if len(x_coords) < 20:
            return False
            
        mid_point = (page.width) / 2
        left_count = sum(1 for x in x_coords if x < mid_point - 50)
        right_count = sum(1 for x in x_coords if x > mid_point + 50)
        
        # If both sides have significant amount of text, likely multi-column
        return left_count > 10 and right_count > 10
