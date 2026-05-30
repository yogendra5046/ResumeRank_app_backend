from fastapi import APIRouter, Depends, Query
from typing import Dict, Any, Optional
import os
import httpx

from src.application.use_cases.get_market_insights import GetMarketInsightsUseCase
from src.presentation.api.dependencies import get_job_store, get_skill_mapper

router = APIRouter(tags=["Insights"])

@router.get(
    "/insights/market",
    summary="Get live market trends and hot skills",
    description="Analyzes all recently processed job descriptions to provide market insights."
)
async def get_market_insights(
    job_store = Depends(get_job_store),
    skill_mapper = Depends(get_skill_mapper)
) -> Dict[str, Any]:
    use_case = GetMarketInsightsUseCase(job_store, skill_mapper)
    return await use_case.execute()

@router.get(
    "/insights/jobs",
    summary="Live job search via Adzuna API",
    description="Searches real job listings matching a query. Set ADZUNA_APP_ID and ADZUNA_APP_KEY env vars."
)
async def search_jobs(
    query: str = Query(..., description="Job title or skills to search"),
    country: str = Query("in", description="Country code: in=India, us=USA, gb=UK"),
    results: int = Query(10, le=20),
) -> Dict[str, Any]:
    app_id = os.environ.get("ADZUNA_APP_ID")
    app_key = os.environ.get("ADZUNA_APP_KEY")

    if not app_id or not app_key:
        # Return curated mock data when no API key is set
        return {
            "source": "mock",
            "message": "Set ADZUNA_APP_ID and ADZUNA_APP_KEY for live data",
            "jobs": [
                {
                    "title": f"{query} Engineer",
                    "company": "TechCorp India Pvt Ltd",
                    "location": "Bengaluru, India",
                    "salary": "₹8L – ₹18L / year",
                    "url": f"https://www.linkedin.com/jobs/search/?keywords={query}",
                    "description": "Looking for a skilled professional to join our growing team.",
                    "posted": "2 days ago",
                },
                {
                    "title": f"Senior {query} Developer",
                    "company": "Infosys Limited",
                    "location": "Hyderabad, India",
                    "salary": "₹15L – ₹30L / year",
                    "url": f"https://www.naukri.com/jobs-in-india?q={query}",
                    "description": "Senior-level role with competitive compensation and growth.",
                    "posted": "1 day ago",
                },
                {
                    "title": f"Lead {query} Architect",
                    "company": "Wipro Technologies",
                    "location": "Pune, India",
                    "salary": "₹25L – ₹45L / year",
                    "url": f"https://www.indeed.co.in/jobs?q={query}",
                    "description": "Leadership position driving technical strategy.",
                    "posted": "3 hours ago",
                },
            ],
        }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"https://api.adzuna.com/v1/api/jobs/{country}/search/1",
                params={
                    "app_id": app_id,
                    "app_key": app_key,
                    "results_per_page": results,
                    "what": query,
                    "content-type": "application/json",
                },
            )
            resp.raise_for_status()
            data = resp.json()

            jobs = []
            for item in data.get("results", []):
                jobs.append({
                    "title": item.get("title", ""),
                    "company": item.get("company", {}).get("display_name", ""),
                    "location": item.get("location", {}).get("display_name", ""),
                    "salary": (
                        f"₹{int(item['salary_min']):,} – ₹{int(item['salary_max']):,}"
                        if item.get("salary_min") else "Salary not disclosed"
                    ),
                    "url": item.get("redirect_url", ""),
                    "description": item.get("description", ""),
                    "posted": item.get("created", ""),
                })

            return {"source": "adzuna", "total": data.get("count", 0), "jobs": jobs}

    except Exception as e:
        return {"source": "error", "message": str(e), "jobs": []}
