import asyncio
import os
import sys
import json

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.getcwd())))

from src.domain.services.scoring import analyze_resume_full

async def test():
    resume_text = "I am a Python Developer with 5 years of experience in FastAPI and Machine Learning. I know NLP and Tools."
    jd_text = "Looking for a Python Developer with experience in FastAPI, Docker, and Kubernetes. Must know NLP."
    
    # Mock data
    tone_results = {"professional": 0.8, "readability": 65.0}
    semantic_score = 75.0
    salary_data = {
        "category": "Software",
        "estimated_range": "₹15.0 - 20.0 LPA",
        "raw_lpa": 17.5,
        "currency": "INR",
        "experience_detected": "5+ Years",
        "seniority": "Senior"
    }
    persona_data = {"primary_persona": "Specialist"}
    
    result = analyze_resume_full(
        resume_text, 
        jd_text, 
        tone_results=tone_results,
        semantic_score=semantic_score,
        salary_data=salary_data,
        persona_data=persona_data
    )
    
    print(f"Overall Score: {result.get('overall_score')}")
    print(f"Score: {result.get('score')}")
    print(f"Grade: {result.get('grade')}")
    print(f"Salary Data: {result.get('estimated_salary')}")
    print(f"Persona Data: {result.get('professional_persona')}")
    print(f"Missing Keywords: {result.get('missing_keywords')}") # Check if this exists
    print(f"JD Keywords: {result.get('jd_keywords')}")
    print(f"Matched Skills count: {len(result.get('matched_skills', []))}")
    print(f"Missing Skills count: {len(result.get('missing_skills', []))}")
    print(f"Skill Gap Chart count: {len(result.get('skill_gap_chart', []))}")

if __name__ == "__main__":
    asyncio.run(test())
