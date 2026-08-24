"""Application DTOs: inbound request shapes."""
from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class AnalyzeRequest(BaseModel):
    """Validated inbound DTO for the /v1/analyze endpoint.

    The PDF bytes arrive separately via multipart/form-data upload;
    this DTO carries only the text payload validated by Pydantic.
    """

    model_config = {"frozen": True, "str_strip_whitespace": True}

    job_description: str = Field(
        ...,
        min_length=50,
        max_length=50_000,
        description="Plain-text job description to score against.",
        examples=["We are looking for a Senior Python Engineer with 5+ years…"],
    )

    @field_validator("job_description")
    @classmethod
    def no_html_injection(cls, v: str) -> str:
        """Reject payloads with embedded HTML/script tags (XSS guard)."""
        import html

        decoded = html.unescape(v)
        if "<script" in decoded.lower() or "javascript:" in decoded.lower():
            raise ValueError("HTML/script content is not allowed in job description")
        return v
