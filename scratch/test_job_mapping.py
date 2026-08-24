import asyncio
import os
import sys
import json

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.getcwd())))

from src.domain.services.scoring import analyze_resume_full

async def test_mapping():
    # Scenario 1: Python Backend Resume vs Backend JD
    resume_text = "Experienced Backend Engineer specializing in Python, FastAPI, and PostgreSQL. Familiar with Docker and Redis."
    jd_text = "We are looking for a Backend Developer who knows Python, Django, and Kubernetes."
    
    print("--- Running Test Scenario 1: Backend Mapping ---")
    result = analyze_resume_full(
        resume_text, 
        jd_text, 
        tone_results={"professional": 0.8, "readability": 70.0},
        semantic_score=80.0
    )
    
    print(f"Target Role Identified: {result['professional_persona']['description']}")
    print(f"Suggested Role: {result['professional_persona']['primary_persona']}")
    print(f"Matched Skills: {result['skill_gap']['matched_skills']}")
    print(f"Missing Skills: {result['skill_gap']['missing_skills']}")
    
    # Check if 'django' and 'kubernetes' are in missing skills (from JD)
    # Check if 'mongodb', 'microservices' etc are in missing skills (from Role Mapping)
    
    print("\n--- Running Test Scenario 2: Data Scientist Resume ---")
    resume_text_ds = "Data Scientist with expertise in Machine Learning, PyTorch, and SQL. Published papers in NLP."
    jd_text_ds = "Looking for a Data Scientist with Python and Spark experience."
    
    result_ds = analyze_resume_full(
        resume_text_ds, 
        jd_text_ds, 
        tone_results={"professional": 0.9, "readability": 60.0},
        semantic_score=85.0
    )
    
    print(f"Target Role Identified: {result_ds['professional_persona']['description']}")
    print(f"Suggested Role: {result_ds['professional_persona']['primary_persona']}")
    print(f"Missing Skills count: {len(result_ds['skill_gap']['missing_skills'])}")
    
    # Scenario 3: General JD, identifying role from resume
    print("\n--- Running Test Scenario 3: Role Suggestion ---")
    resume_text_flutter = "Flutter Developer with 2 years of experience. Built several apps using Dart and Firebase."
    jd_text_general = "Hiring software developers. Apply now."
    
    result_flutter = analyze_resume_full(
        resume_text_flutter, 
        jd_text_general, 
        tone_results={"professional": 0.8, "readability": 75.0},
        semantic_score=50.0
    )
    print(f"Suggested Role for Flutter Resume: {result_flutter['professional_persona']['primary_persona']}")

if __name__ == "__main__":
    asyncio.run(test_mapping())
