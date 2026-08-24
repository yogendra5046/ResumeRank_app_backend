"""Tests: domain ScoringService correctness."""
from __future__ import annotations

import numpy as np
import pytest

from src.domain.entities.score_result import ScoreResult
from src.domain.ports.skill_graph import SkillMatchResult
from src.domain.services.scoring_service import CosineSimilarityInput, ScoringService


@pytest.fixture
def service() -> ScoringService:
    return ScoringService()


def _unit_vec(dim: int = 384) -> np.ndarray:  # type: ignore[type-arg]
    v = np.ones(dim, dtype=np.float32)
    return (v / np.linalg.norm(v)).astype(np.float32)


@pytest.mark.unit
def test_identical_vectors_cosine_score_100(service: ScoringService) -> None:
    """Identical resume and JD vectors must yield cosine_score = 100."""
    v = _unit_vec()
    result = service.score(
        resume_text="Python SQL FastAPI",
        jd_text="Python SQL FastAPI",
        cosine_input=CosineSimilarityInput(resume_vector=v, jd_vector=v),
        skill_result=SkillMatchResult(matched=(), missing=(), graph_weight=1.0),
        resume_sha256="a" * 64,
        jd_sha256="b" * 64,
        model_version="test",
    )
    assert result.cosine_score == pytest.approx(100.0, abs=0.1)


@pytest.mark.unit
def test_orthogonal_vectors_cosine_score_0(service: ScoringService) -> None:
    """Orthogonal vectors must yield cosine_score = 0 (clamped)."""
    v1 = np.zeros(384, dtype=np.float32)
    v1[0] = 1.0
    v2 = np.zeros(384, dtype=np.float32)
    v2[1] = 1.0
    result = service.score(
        resume_text="",
        jd_text="",
        cosine_input=CosineSimilarityInput(resume_vector=v1, jd_vector=v2),
        skill_result=SkillMatchResult(matched=(), missing=(), graph_weight=0.0),
        resume_sha256="a" * 64,
        jd_sha256="b" * 64,
        model_version="test",
    )
    assert result.cosine_score == pytest.approx(0.0, abs=0.1)


@pytest.mark.unit
def test_impact_verbs_detected_with_numbers(service: ScoringService) -> None:
    """Impact verbs followed by quantifiers must award +2 points each."""
    text = (
        "Increased API throughput by 40%. "
        "Reduced deployment time by 60%. "
        "Led team of 12 engineers."
    )
    verbs, score = service._impact_score(text)
    with_number = [v for v in verbs if v.has_number]
    assert len(with_number) >= 2
    assert score > 0


@pytest.mark.unit
def test_impact_verb_without_number_gives_zero_points(service: ScoringService) -> None:
    """Impact verb without quantifier must award 0 points."""
    text = "Led team. Built product. Designed system."
    verbs, score = service._impact_score(text)
    assert all(v.points == 0.0 for v in verbs)


@pytest.mark.unit
def test_format_score_all_sections_present(service: ScoringService) -> None:
    """All 5 sections detected → format_score = 100."""
    text = "experience education skills contact summary"
    issues, score = service._format_score(text)
    assert score == pytest.approx(100.0)
    assert issues == []


@pytest.mark.unit
def test_format_score_missing_sections_deduct(service: ScoringService) -> None:
    """Missing sections must reduce score and appear in issues list."""
    text = "experience skills"  # missing: education, contact, summary
    issues, score = service._format_score(text)
    assert score == pytest.approx(40.0)
    assert len(issues) == 3


@pytest.mark.unit
def test_final_score_formula_correct(service: ScoringService) -> None:
    """final = 0.5*cosine + 0.3*skill + 0.1*impact + 0.1*format."""
    v = _unit_vec()
    result = service.score(
        resume_text="experience education skills contact summary increased throughput by 30%",
        jd_text="experience education skills contact summary",
        cosine_input=CosineSimilarityInput(resume_vector=v, jd_vector=v),
        skill_result=SkillMatchResult(matched=(), missing=(), graph_weight=0.8),
        resume_sha256="a" * 64,
        jd_sha256="b" * 64,
        model_version="test",
    )
    expected = 0.5 * result.cosine_score + 0.3 * result.skill_score + \
               0.1 * result.impact_score + 0.1 * result.format_score
    assert result.final_score == pytest.approx(expected, abs=0.1)


@pytest.mark.unit
def test_score_result_grade_a_above_80(service: ScoringService) -> None:
    """Score ≥ 80 must yield grade A."""
    v = _unit_vec()
    result = service.score(
        resume_text="experience education skills contact summary " + "increased revenue by 50%. " * 5,
        jd_text="experience",
        cosine_input=CosineSimilarityInput(resume_vector=v, jd_vector=v),
        skill_result=SkillMatchResult(matched=(), missing=(), graph_weight=1.0),
        resume_sha256="a" * 64,
        jd_sha256="b" * 64,
        model_version="test",
    )
    if result.final_score >= 80:
        assert result.grade == "A"


@pytest.mark.unit
def test_invalid_sub_score_raises() -> None:
    """Sub-scores outside [0,100] must raise ValueError at entity construction."""
    with pytest.raises(ValueError):
        ScoreResult(
            cosine_score=150.0,  # invalid
            skill_score=50.0,
            impact_score=50.0,
            format_score=50.0,
            matched_skills=(),
            missing_skills=(),
            impact_verbs=(),
            format_issues=(),
            resume_sha256="a" * 64,
            jd_sha256="b" * 64,
            model_version="test",
        )
