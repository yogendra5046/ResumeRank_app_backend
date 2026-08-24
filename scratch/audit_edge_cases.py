import sys
import os
from typing import List, Dict

# Add project root to path
sys.path.append(os.getcwd())

from src.domain.services.ats_scorer import AtsScorer
from src.domain.services.scoring import analyze_resume_full
from src.domain.services.job_skill_mapper import JobSkillMapper

def run_audit():
    print("=== STARTING COMPREHENSIVE NLP AUDIT ===\n")
    scorer = AtsScorer()
    mapper = JobSkillMapper()
    
    # CASE 1: The "Non-Tech" Resume
    print("--- CASE 1: Non-Tech Resume (Chef) ---")
    chef_resume = "Executive Chef with 10 years experience in Italian cuisine. Managed a team of 20. Expert in menu planning and food safety."
    jd_tech = "Backend Developer with Python and SQL experience."
    result1 = analyze_resume_full(chef_resume, jd_tech)
    print(f"Score: {result1['overall_score']}")
    print(f"Identified Role: {result1['professional_persona']['primary_persona']}")
    print(f"Next Move: {result1['career_guidance']['next_best_move']}")
    print("-" * 30 + "\n")

    # CASE 2: The "Keyword Stuffer"
    print("--- CASE 2: Keyword Stuffer ---")
    stuffer_resume = "Python Python Python Python Python Python Python Python Python Python SQL SQL SQL SQL SQL"
    result2 = analyze_resume_full(stuffer_resume, jd_tech)
    print(f"Score: {result2['overall_score']}")
    print(f"Details: {result2['impact']['details']}")
    print("-" * 30 + "\n")

    # CASE 3: Semantic Trap (Java vs Javascript)
    print("--- CASE 3: Semantic Trap (Java vs JavaScript) ---")
    # This tests if our MiniLM threshold is too loose
    # Note: In a real test we'd need the embedder, here we test the logic flow
    js_resume = "Expert in JavaScript, React, and Node.js."
    java_jd = "Java Developer with Spring Boot experience."
    result3 = analyze_resume_full(js_resume, java_jd)
    print(f"Score: {result3['overall_score']}")
    print(f"Matched Skills: {[s['name'] for s in result3['matched_skills']]}")
    print("-" * 30 + "\n")

    # CASE 4: The "Student" Pivot
    print("--- CASE 4: Career Guidance Pivot ---")
    student_resume = "Computer Science student. Skilled in Python, C++, and Algorithms. Looking for first internship."
    result4 = analyze_resume_full(student_resume, "Junior Developer")
    print(f"Current Role: {result4['career_guidance']['current_role']}")
    print(f"Predicted Path: {result4['career_guidance']['next_best_move']}")
    print(f"Roadmap: {[r['skill'] for r in result4['career_guidance']['learning_roadmap']]}")
    print("-" * 30 + "\n")

if __name__ == "__main__":
    run_audit()
