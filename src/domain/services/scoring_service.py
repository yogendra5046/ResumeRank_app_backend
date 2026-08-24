"""Domain service: pure scoring logic.

No I/O here. All inputs are pre-computed values passed by the use case.
Formula: final = 0.5*cosine + 0.3*skill_graph + 0.1*impact + 0.1*format
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Final

import numpy as np
import numpy.typing as npt

from src.domain.entities.score_result import ImpactVerb, ScoreResult, SkillMatch
from src.domain.ports.skill_graph import SkillMatchResult

# ── Impact verb patterns ───────────────────────────────────────────────────────
# Must be accompanied by a number or percentage within 60 chars to score +2
_IMPACT_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"\b(increased|decreased|reduced|improved|led|built|designed|delivered|"
    r"launched|optimised|optimized|automated|accelerated|scaled|saved|"
    r"generated|achieved|grew|cut|doubled|tripled)\b",
    re.IGNORECASE,
)
_QUANTIFIER_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"\b\d+[\d,]*\s*(?:%|percent|x|times|k|m|billion|million|users|ms|seconds)(?!\w)",
    re.IGNORECASE,
)
_IMPACT_POINTS: Final[float] = 2.0
_IMPACT_MAX: Final[float] = 20.0  # cap at 10 verbs * 2 pts = 20 raw, normalised to 100

# ── Format heuristics ─────────────────────────────────────────────────────────
_SECTION_KEYWORDS: Final[list[str]] = [
    "experience",
    "education",
    "skills",
    "contact",
    "summary",
]
_FORMAT_SCORE_PER_SECTION: Final[float] = 20.0  # 5 sections * 20 = 100 max


@dataclass(frozen=True, slots=True)
class CosineSimilarityInput:
    """Pre-computed embeddings handed to the scoring service."""

    resume_vector: npt.NDArray[np.float32]
    jd_vector: npt.NDArray[np.float32]


class ScoringService:
    """Pure domain service – all scoring math lives here.

    Stateless; can be called concurrently without locking.
    """

    def score(
        self,
        *,
        resume_text: str,
        jd_text: str,
        cosine_input: CosineSimilarityInput,
        skill_result: SkillMatchResult,
        resume_sha256: str,
        jd_sha256: str,
        model_version: str,
        from_cache: bool = False,
        keyword_analysis: dict[str, dict] | None = None,
        section_scores: dict[str, float] | None = None,
        ats_parse_check: dict | None = None,
        tone: dict | None = None,
    ) -> ScoreResult:
        """Compute final ATS score from pre-computed sub-signals.

        Args:
            resume_text: Extracted plain text from the resume.
            jd_text: Plain text of the job description.
            cosine_input: L2-normalised embedding vectors.
            skill_result: Output of SkillGraphPort.match().
            resume_sha256: PDF content digest (for audit trail).
            jd_sha256: JD content digest.
            model_version: Embedder model identifier.
            from_cache: Whether result is served from Redis cache.
            keyword_analysis: Density gap analysis per skill.
            section_scores: Cosine similarity per resume section.
            ats_parse_check: PDF structural issues affecting ATS.
            tone: Professionalism and readability metrics.

        Returns:
            Fully populated ScoreResult with sub-scores and explanations.
        """
        cosine_score = self._cosine_score(cosine_input)
        skill_score = self._skill_score(skill_result)
        impact_verbs, impact_score = self._impact_score(resume_text)
        format_issues, format_score = self._format_score(resume_text)

        matched_skills = tuple(
            SkillMatch(
                skill_id=label,
                label=label,
                graph_weight=skill_result.graph_weight,
                matched_in_resume=True,
                matched_in_jd=True,
            )
            for label in skill_result.matched
        )

        return ScoreResult(
            cosine_score=cosine_score,
            skill_score=skill_score,
            impact_score=impact_score,
            format_score=format_score,
            matched_skills=matched_skills,
            missing_skills=skill_result.missing,
            impact_verbs=tuple(impact_verbs),
            format_issues=tuple(format_issues),
            resume_sha256=resume_sha256,
            jd_sha256=jd_sha256,
            model_version=model_version,
            from_cache=from_cache,
            raw_resume_text=resume_text,
            raw_jd_text=jd_text,
            keyword_analysis=keyword_analysis,
            section_scores=section_scores,
            ats_parse_check=ats_parse_check,
            tone=tone,
        )

    # ── Sub-score helpers ─────────────────────────────────────────────────────

    @staticmethod
    def _cosine_score(inp: CosineSimilarityInput) -> float:
        """Dot product of two L2-normalised vectors gives cosine similarity."""
        similarity = float(np.dot(inp.resume_vector, inp.jd_vector))
        # Clamp to [0, 1] then scale to [0, 100]
        return round(max(0.0, min(1.0, similarity)) * 100.0, 4)

    @staticmethod
    def _skill_score(result: SkillMatchResult) -> float:
        return round(result.graph_weight * 100.0, 4)

    @staticmethod
    def _impact_score(text: str) -> tuple[list[ImpactVerb], float]:
        verbs: list[ImpactVerb] = []
        for match in _IMPACT_PATTERN.finditer(text):
            start = max(0, match.start() - 60)
            end = min(len(text), match.end() + 60)
            context = text[start:end]
            has_number = bool(_QUANTIFIER_PATTERN.search(context))
            verbs.append(
                ImpactVerb(
                    verb=match.group().lower(),
                    context=context.strip(),
                    has_number=has_number,
                    points=_IMPACT_POINTS if has_number else 0.0,
                )
            )
        raw = sum(v.points for v in verbs)
        score = round(min(raw / _IMPACT_MAX, 1.0) * 100.0, 4)
        return verbs, score

    @staticmethod
    def _format_score(text: str) -> tuple[list[str], float]:
        lower = text.lower()
        issues: list[str] = []
        found = 0
        for section in _SECTION_KEYWORDS:
            if section in lower:
                found += 1
            else:
                issues.append(f"Missing section: '{section}'")
        score = round((found / len(_SECTION_KEYWORDS)) * 100.0, 4)
        return issues, score
