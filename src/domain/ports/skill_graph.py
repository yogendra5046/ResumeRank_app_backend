"""Domain port: ESCO skill graph abstraction."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SkillMatchResult:
    """Output of graph-based skill matching."""

    matched: tuple[str, ...]   # ESCO skill labels found in both resume + JD
    missing: tuple[str, ...]   # JD skills absent from resume
    graph_weight: float        # Normalised [0, 1] score after graph traversal


class SkillGraphPort(ABC):
    """Hexagonal port – match skills via ESCO v1.1.1 taxonomy graph.

    The graph enables synonym resolution and parent-skill partial credit,
    e.g. "Python" → "scripting" partial match when JD asks for "programming".
    """

    @abstractmethod
    async def match(
        self,
        resume_text: str,
        jd_text: str,
    ) -> SkillMatchResult:
        """Extract and graph-match skills from both texts.

        Returns:
            SkillMatchResult with matched/missing labels and normalised weight.
        """

    @property
    @abstractmethod
    def skill_count(self) -> int:
        """Number of ESCO skills loaded (must be ≥ 3000)."""
