import os
import requests
from dotenv import load_dotenv

# Load env variables
load_dotenv()

def test_rewrite_e2e():
    url = "http://127.0.0.1:9000/v1/rewrite"
    headers = {
        "X-API-Key": "resumerank-pro-2026",
        "Content-Type": "application/json"
    }
    
    # Simulating what we got from OCR
    payload = {
        "resume_text": "John Doe\nSoftware Engineer\nEmail: john.doe@example.com\n\nSkills: Python, FastAPI, Docker, Kubernetes\n\nExperience:\n- Backend Engineer at TechCorp: Developed REST APIs using Python and FastAPI.",
        "jd_text": "We are seeking a Python Backend Engineer with experience in FastAPI, Docker, and Kubernetes.",
        "missing_skills": ["CI/CD pipelines", "AWS"],
        "weak_sections": ["Experience", "Skills"]
    }
    
    print("Sending request to /v1/rewrite...")
    response = requests.post(url, headers=headers, json=payload, timeout=60.0)
    
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        res_json = response.json()
        print("Success! Rewrite Result:")
        print("Rewritten Text length:", len(res_json.get("rewritten_text", "")))
        print("Detailed Enhancements:", res_json.get("detailed_enhancements"))
        print("Skill Route Map count:", len(res_json.get("skill_route_map", [])))
    else:
        print(f"Failed! Response: {response.text}")

if __name__ == "__main__":
    test_rewrite_e2e()
