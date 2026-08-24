from src.domain.services.scoring import calculate_impact_score

def test_impact_score_requirements():
    resume_text = "Led team, increased revenue 40%"
    result = calculate_impact_score(resume_text)
    
    # "Led" is an action verb -> +4 pts
    # "increased" is an action verb -> +4 pts
    # "40%" is a metric -> +8 pts
    # Total = 16 pts? Wait, prompt says: "If resume has 'Led team, increased 40%' score must be 90+"
    # But my formula is strictly max 60 for verbs, max 40 for metrics.
    # Ah! The user requested:
    # "Return {"score": 0-100, "details": ...}
    # If text has "Led team, increased revenue 40%" score must be 90+"
    # If the exact words give only 16 pts, how can it be 90+?
    assert result["score"] >= 90
