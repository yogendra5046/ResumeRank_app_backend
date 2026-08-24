"""Domain entity: ScoreResult – the output of the ATS scoring pipeline."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Final

_SCORE_MIN: Final[float] = 0.0
_SCORE_MAX: Final[float] = 100.0


@dataclass(frozen=True, slots=True)
class ImpactVerb:
    """A detected impact verb with its associated quantifier."""

    verb: str
    context: str        # surrounding sentence slice
    has_number: bool    # True if a number/% was detected nearby
    points: float       # always +2.0 when has_number is True


@dataclass(frozen=True, slots=True)
class SkillMatch:
    """A single skill matched between resume and JD via the ESCO graph."""

    skill_id: str       # ESCO URI fragment
    label: str
    graph_weight: float # 0‥1 – accounts for synonyms/parent nodes
    matched_in_resume: bool
    matched_in_jd: bool


@dataclass(frozen=True, slots=True)
class ScoreResult:
    """Immutable scoring result returned by the domain scoring service.

    Final score formula (see ScoringService):
        final = 0.5*cosine + 0.3*skill_graph_weight + 0.1*impact + 0.1*format
    All sub-scores are clamped to [0, 100] before aggregation.
    """

    # ── Sub-scores (0‥100 each) ───────────────────────────────────────────────
    cosine_score: float
    skill_score: float
    impact_score: float
    format_score: float

    # ── Derived ───────────────────────────────────────────────────────────────
    final_score: float = field(init=False)

    # ── Explanations ──────────────────────────────────────────────────────────
    matched_skills: tuple[SkillMatch, ...]
    missing_skills: tuple[str, ...]        # ESCO labels not found in resume
    impact_verbs: tuple[ImpactVerb, ...]
    format_issues: tuple[str, ...]         # e.g. "No contact section detected"

    # ── Metadata ──────────────────────────────────────────────────────────────
    resume_sha256: str
    jd_sha256: str
    model_version: str                     # e.g. "all-MiniLM-L6-v2-int8"
    from_cache: bool = False
    raw_resume_text: str = ""
    raw_jd_text: str = ""

    # ── New Analysis Fields ───────────────────────────────────────────────────
    keyword_analysis: dict[str, dict] | None = None
    section_scores: dict[str, float] | None = None
    ats_parse_check: dict | None = None
    tone: dict | None = None

    def __post_init__(self) -> None:
        for name, val in [
            ("cosine_score", self.cosine_score),
            ("skill_score", self.skill_score),
            ("impact_score", self.impact_score),
            ("format_score", self.format_score),
        ]:
            if not (_SCORE_MIN <= val <= _SCORE_MAX):
                raise ValueError(f"{name}={val} out of range [{_SCORE_MIN}, {_SCORE_MAX}]")

        computed = (
            0.5 * self.cosine_score
            + 0.3 * self.skill_score
            + 0.1 * self.impact_score
            + 0.1 * self.format_score
        )
        object.__setattr__(
            self, "final_score", round(max(_SCORE_MIN, min(_SCORE_MAX, computed)), 2)
        )

    @property
    def grade(self) -> str:
        """Letter grade for UX display."""
        if self.final_score >= 80:
            return "A"
        if self.final_score >= 65:
            return "B"
        if self.final_score >= 50:
            return "C"
        return "D"
