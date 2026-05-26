import asyncio
import sys
import os

# Add src to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from src.domain.services.scoring import analyze_resume_full
from src.domain.services.job_skill_mapper import JobSkillMapper

async def test_variety():
    resume_1 = """
    John Doe
    Senior Backend Developer
    Expert in Python, FastAPI, and Docker. 
    Led a team of 10 to architect scalable microservices.
    Optimized database queries by 40%.
    """
    
    resume_2 = """
    Jane Smith
    Junior Frontend Developer
    Skills: React, JavaScript, HTML, CSS.
    Worked on a small team to build a landing page.
    Passionate team player and hard worker.
    """
    
    jd = """
    We are looking for a Software Engineer at TechCorp.
    Must have experience with Python, React, and Kubernetes.
    We value innovation and scalable design.
    """
    
    print("=== ANALYSIS 1: SENIOR BACKEND ===")
    res1 = analyze_resume_full(resume_1, jd)
    print(f"Persona: {res1['professional_persona']['primary_persona']}")
    print(f"Percentile: {res1['percentile']}%")
    print(f"Roast: {res1['roast'][1] if len(res1['roast']) > 1 else 'N/A'}")
    print(f"Gap Project: {res1['career_guidance']['roadmap'][0]['learning_path'][0]['project']}")
    print(f"Cover Letter Preview: {res1['cover_letter'][:100]}...")
    
    print("\n=== ANALYSIS 2: JUNIOR FRONTEND ===")
    res2 = analyze_resume_full(resume_2, jd)
    print(f"Persona: {res2['professional_persona']['primary_persona']}")
    print(f"Percentile: {res2['percentile']}%")
    print(f"Roast: {res2['roast'][1] if len(res2['roast']) > 1 else 'N/A'}")
    
    resume_3 = """
    Jane Doe
    Cloud Architect & Visionary
    Expert in Python, React, and Kubernetes. 
    Designed and implemented global-scale clusters on AWS.
    Spearheaded transition to microservices, improving reliability by 99%.
    Master of System Design and Terraform.
    """
    
    print("\n=== ANALYSIS 3: ARCHITECT (HIGH SCORE) ===")
    res3 = analyze_resume_full(resume_3, jd)
    print(f"Persona: {res3['professional_persona']['primary_persona']}")
    print(f"Percentile: {res3['percentile']}%")
    print(f"Roast: {res3['roast'][1] if len(res3['roast']) > 1 else 'N/A'}")
    print(f"Company Detected: {res3['cover_letter'].split('Dear ')[1].split(' Hiring')[0]}")
    print(f"Cover Letter Preview: {res3['cover_letter'][:150]}...")

if __name__ == "__main__":
    asyncio.run(test_variety())
