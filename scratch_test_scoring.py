import asyncio
from src.domain.services.scoring import analyze_resume_full

async def test_scoring():
    resume_text = "Experienced Software Engineer. Built an app using Python. Good team player. Responsible for fixing bugs."
    jd_text = "Looking for a Python developer with AWS and Docker experience. Must be a strong leader."
    
    result = analyze_resume_full(
        resume_text=resume_text,
        jd_text=jd_text
    )
    
    print("Section Audit:", result.get("ats_parse", {}).get("section_audit"))
    print("Format Warnings:", result.get("ats_parse", {}).get("format_warnings"))
    print("Verb Stats:", result.get("verb_analysis"))

if __name__ == "__main__":
    asyncio.run(test_scoring())
