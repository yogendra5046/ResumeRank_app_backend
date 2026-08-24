import pytest
import fitz
from src.domain.services.ats_scorer import ats_scorer

def test_impact_score_action_verbs():
    text = "I achieved many things. I led a team and optimized the process."
    result = ats_scorer.score_impact(text)
    # achieved, led, optimized = 3 verbs = 18 points
    assert result["score"] >= 18
    assert "achieved" in result["raw_metrics"]["verbs"]

def test_impact_score_metrics():
    text = "Increased revenue by 40% and gained 1000 users. $50M generated."
    result = ats_scorer.score_impact(text)
    # 2 verbs + 3 metrics = 12 + 45 = 57 points
    assert result["score"] > 50
    assert result["raw_metrics"]["metrics_count"] >= 3

def test_impact_score_power_words():
    text = "I was promoted and recognized as a top performer."
    result = ats_scorer.score_impact(text)
    # power words = 3 words = 15 points
    assert "promoted" in result["raw_metrics"]["power_words"]
    assert result["score"] >= 15

def test_format_score_pages():
    # Mock fitz document
    doc = fitz.open()
    p1 = doc.new_page()
    for i in range(10):
        p1.insert_text(fitz.Point(50, 50 + i * 20), "some text experience education skills projects contact summary")
    doc.new_page()
    doc.new_page() # 3 pages -> > 2 pages -> -5 penalty
    result = ats_scorer.score_format(doc)
    assert result["score"] == 95

def test_keyword_match_exact():
    resume = "I am skilled in python and react.js. " * 10
    jd = "Looking for someone with Python and React.js experience."
    result = ats_scorer.score_keyword(resume, jd)
    assert result["score"] >= 70

def test_keyword_match_synonym():
    resume = "I use python and django. " * 10
    jd = "python and django."
    result = ats_scorer.score_keyword(resume, jd)
    assert result["score"] >= 70

def test_ats_parse_extractable():
    # Empty text
    result = ats_scorer.score_ats_parse(fitz.open(), "   ")
    assert result["score"] == 0
    assert "Text extractable < 100 chars (0)" in result["details"][0]

def test_ats_parse_headers_and_contact():
    resume = "John Doe\njohn@example.com | 123-456-7890\nProfessional Experience\nEducation\nSkills\nProjects\n"
    resume += "x" * 300 # pad length > 200
    result = ats_scorer.score_ats_parse(fitz.open(), resume)
    # 20 (base) + 60 (headers) + 20 (contact) = 100
    assert result["score"] >= 80

def test_ats_parse_special_chars():
    resume = "Experience\n• Item 1\n• Item 2\n→ Something\n" + ("x" * 100)
    # >5% special chars
    resume = "•" * 20 + "x" * 100
    result = ats_scorer.score_ats_parse(fitz.open(), resume)
    # Penalty -30 applied
    assert "(-30)" in " ".join(result["details"])

def test_evaluate_overall():
    doc = fitz.open()
    page = doc.new_page()
    text = "John Doe\njohn@example.com 555-555-5555\nProfessional Experience\nAchieved 40% growth. Python and React.js.\nEducation\n" + ("x" * 400)
    page.insert_text(fitz.Point(50, 50), text)
    
    pdf_bytes = doc.write()
    jd = "Looking for Python and React.js developer."
    
    result = ats_scorer.evaluate(pdf_bytes, jd)
    assert "overall" in result
    assert "impact" in result
    assert "format" in result
    assert "keyword" in result
    assert "ats" in result
    assert result["overall"] > 0
