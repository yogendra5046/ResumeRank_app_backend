import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

def test_rewrite():
    url = "https://resumerankappbackend-production.up.railway.app/v1/rewrite"
    headers = {
        "X-API-Key": "resumerank-pro-2026",
        "Content-Type": "application/json"
    }
    payload = {
        "resume_text": "Software Engineer with Python experience.",
        "jd_text": "Looking for a Senior Python Developer with Kubernetes skills.",
        "missing_skills": ["Kubernetes", "Docker"],
        "weak_sections": ["Experience"]
    }
    
    print(f"Testing rewrite at {url}...")
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
    except Exception as e:
        print(f"Error: {e}")
        if hasattr(e, 'response') and e.response is not None:
             print(e.response.text)

if __name__ == "__main__":
    test_rewrite()
