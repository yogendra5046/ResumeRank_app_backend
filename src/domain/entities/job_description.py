"""Domain entity: JobDescription value object."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field

_MAX_JD_CHARS: int = 50_000


@dataclass(frozen=True, slots=True)
class JobDescription:
    """Immutable value object representing a job description.

    Two JDs with the same text are considered identical regardless of
    surrounding context, which enables effective cache key construction.
    """

    text: str
    sha256: str = field(init=False)

    def __post_init__(self) -> None:
        stripped = self.text.strip()
        if not stripped:
            raise ValueError("Job description text must not be empty")
        if len(stripped) > _MAX_JD_CHARS:
            raise ValueError(
                f"Job description exceeds {_MAX_JD_CHARS} character limit"
            )
        # Store normalised text and digest
        object.__setattr__(self, "text", stripped)
        object.__setattr__(self, "sha256", hashlib.sha256(stripped.encode()).hexdigest())

    @classmethod
    def from_raw(cls, raw: str) -> "JobDescription":
        """Factory that trims and validates in one call."""
        return cls(text=raw)
