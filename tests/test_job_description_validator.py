import pytest
from src.domain.services.job_description_validator import JobDescriptionValidator

def test_valid_job_description():
    validator = JobDescriptionValidator()
    valid_jd = (
        "We are looking for a Senior Python Developer to join our team. "
        "Key Responsibilities:\n"
        "- Build, scale and optimize REST APIs using FastAPI and Django.\n"
        "- Work closely with product managers and frontend teams.\n"
        "Requirements:\n"
        "- 5+ years of experience in Software Development.\n"
        "- Strong understanding of PostgreSQL and AWS."
    )
    result = validator.validate(valid_jd)
    assert result["is_jd"] is True
    assert result["confidence_score"] >= 30
    assert len(result["reasons"]) == 0

def test_too_short_job_description():
    validator = JobDescriptionValidator()
    short_jd = "Python engineer wanted. Call me."
    result = validator.validate(short_jd)
    assert result["is_jd"] is False
    assert "too short" in result["reasons"][0]

def test_empty_job_description():
    validator = JobDescriptionValidator()
    result = validator.validate("")
    assert result["is_jd"] is False
    assert "Empty" in result["reasons"][0]

def test_gated_url_job_description():
    validator = JobDescriptionValidator()
    gated_jd = "https://www.linkedin.com/jobs/view/12345678"
    result = validator.validate(gated_jd)
    assert result["is_jd"] is False
    assert "auth-gated" in result["reasons"][0]

def test_nongated_url_job_description():
    validator = JobDescriptionValidator()
    nongated_jd = "https://careers.google.com/jobs/results/12345"
    result = validator.validate(nongated_jd)
    assert result["is_jd"] is False
    assert "could not be scraped" in result["reasons"][0]

def test_cover_letter():
    validator = JobDescriptionValidator()
    cover_letter = (
        "Dear Hiring Manager,\n"
        "I am writing to apply for the Software Engineer position. "
        "I have 5 years of experience in Python and Java. My name is John Doe "
        "and I am very excited about this role. Please review my attached resume."
    )
    result = validator.validate(cover_letter)
    assert result["is_jd"] is False
    assert "resume, cover letter, or personal biography" in result["reasons"][0]

def test_default_fallback():
    validator = JobDescriptionValidator()
    result = validator.validate("Software Engineer Python Java SQL AWS")
    assert result["is_jd"] is True
    assert len(result["reasons"]) == 0
