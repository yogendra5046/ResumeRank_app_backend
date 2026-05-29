import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

from domain.services.job_skill_mapper import JobSkillMapper
from domain.services.persona_analyzer import PersonaAnalyzer

mapper = JobSkillMapper()
persona_analyzer = PersonaAnalyzer()

def test_resume(name, text):
    print(f"--- Testing Resume: {name} ---")
    
    # Test Job Skill Mapper (Detected Career Track)
    role = mapper.identify_role(text)
    print(f"Detected Career Track: {role}")
    
    # Test Persona Analyzer (Workplace Persona)
    persona_data = persona_analyzer.analyze(text)
    print(f"Dominant Persona: {persona_data['primary_persona']}")
    print(f"Persona Breakdown: {persona_data['persona_breakdown']}")
    print(f"Top Traits: {persona_data['top_traits']}\n")

# Resume 1: A senior backend engineer with an old internship
r1 = """
Senior Software Engineer
Experience: 5 years
Skills: Python, Django, FastAPI, SQL, PostgreSQL, Docker, AWS, Kubernetes, Microservices
I engineered and optimized high-throughput backend APIs and orchestrated containerized deployments.
Previously worked as a student intern in 2019 where I assisted the team.
"""
test_resume("Senior Backend Dev (with 'intern' keyword)", r1)

# Resume 2: A junior frontend developer
r2 = """
Frontend Developer Intern
Skills: HTML, CSS, JavaScript, React, Tailwind, Git
I assisted the senior developers in building responsive UI components and collaborated with designers.
A passionate computer science student looking for entry level opportunities.
"""
test_resume("Junior Frontend Dev", r2)

# Resume 3: A management/leadership profile
r3 = """
Director of Engineering
I led cross-functional teams, managed a $5M budget, and spearheaded the strategic vision for the company's tech roadmap.
I mentored senior engineers and pioneered new agile processes.
Skills: Leadership, Agile, System Design, Communication
"""
test_resume("Director of Engineering", r3)
