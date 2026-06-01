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
                    "description": f"We are looking for a highly skilled {query} Engineer to join our core backend team. Requirements: 3+ years of experience building scalable applications. Strong proficiency in Python, Java, or Node.js. Experience with Cloud platforms (AWS/GCP), microservices architecture, and SQL/NoSQL databases. You will be responsible for designing APIs, optimizing performance, and working closely with product managers.",
                    "posted": "2 days ago",
                },
                {
                    "title": f"Senior {query} Developer",
                    "company": "Infosys Limited",
                    "location": "Hyderabad, India",
                    "salary": "₹15L – ₹30L / year",
                    "url": f"https://www.naukri.com/jobs-in-india?q={query}",
                    "description": f"Senior-level role for a {query} Developer. Must have 5+ years of experience in software development. Strong background in React, Angular, or Vue for frontend, and solid understanding of CI/CD pipelines (Jenkins, GitHub Actions). Experience with Kubernetes and Docker is a huge plus. Expect to mentor junior developers and lead technical architectural decisions.",
                    "posted": "1 day ago",
                },
                {
                    "title": f"Lead {query} Architect",
                    "company": "Wipro Technologies",
                    "location": "Pune, India",
                    "salary": "₹25L – ₹45L / year",
                    "url": f"https://www.indeed.co.in/jobs?q={query}",
                    "description": f"Leadership position driving technical strategy for our {query} domain. Requirements: 8+ years of industry experience. Deep expertise in Distributed Systems, System Design, and highly available architectures. Proficiency with Kafka, Redis, and Elasticsearch. Must have excellent communication skills and a proven track record of scaling platforms to millions of users.",
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
                    "sort_by": "date",
                    "max_days_old": 30,
                    "content-type": "application/json",
                },
            )
            resp.raise_for_status()
            data = resp.json()

            currency_symbols = {
                "in": "₹",
                "us": "$",
                "gb": "£",
                "au": "$",
                "ca": "$",
            }
            currency = currency_symbols.get(country, "$")

            jobs = []
            for item in data.get("results", []):
                salary_min = item.get("salary_min")
                salary_max = item.get("salary_max")
                salary_str = "Salary not disclosed"
                if salary_min and salary_max:
                    salary_str = f"{currency}{int(salary_min):,} – {currency}{int(salary_max):,}"
                elif salary_min:
                    salary_str = f"From {currency}{int(salary_min):,}"

                # Extract YYYY-MM-DD from ISO timestamp
                created_date = item.get("created", "")
                posted_str = created_date.split("T")[0] if "T" in created_date else created_date

                jobs.append({
                    "title": item.get("title", ""),
                    "company": item.get("company", {}).get("display_name", ""),
                    "location": item.get("location", {}).get("display_name", ""),
                    "salary": salary_str,
                    "url": item.get("redirect_url", ""),
                    "description": item.get("description", ""),
                    "posted": posted_str,
                })

            return {"source": "adzuna", "total": data.get("count", 0), "jobs": jobs}

    except Exception as e:
        return {"source": "error", "message": str(e), "jobs": []}
