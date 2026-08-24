import asyncio
import os
from src.presentation.api.v1.rewrite import rewrite_resume, RewriteRequest
from fastapi import HTTPException
from dotenv import load_dotenv

load_dotenv()

async def test_direct():
    request = RewriteRequest(
        resume_text="Software Engineer with Python experience.",
        jd_text="Looking for a Senior Python Developer with Kubernetes skills.",
        missing_skills=["Kubernetes", "Docker"],
        weak_sections=["Experience"]
    )
    try:
        response = await rewrite_resume(request, "dummy_api_key")
        print("Success!")
        print(response.json(indent=2))
    except HTTPException as e:
        print(f"HTTP Exception: {e.status_code} - {e.detail}")
    except Exception as e:
        print(f"Other Exception: {e}")

if __name__ == "__main__":
    asyncio.run(test_direct())
