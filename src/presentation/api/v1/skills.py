"""Presentation: Skill suggestion route."""
from __future__ import annotations

from typing import List, Dict
from fastapi import APIRouter, Query

router = APIRouter(tags=["Skills"])

# Static course mapping for v1
COURSE_MAP = {
    "Python": "https://coursera.org/specializations/python",
    "AWS": "https://www.coursera.org/specializations/aws-fundamentals",
    "Docker": "https://www.coursera.org/learn/docker-certified-associate",
    "Kubernetes": "https://www.coursera.org/learn/google-kubernetes-engine",
    "Java": "https://www.coursera.org/specializations/java-programming",
    "React": "https://www.coursera.org/specializations/react",
    "SQL": "https://www.coursera.org/learn/sql-for-data-science",
    "Machine Learning": "https://www.coursera.org/specializations/machine-learning",
    "Cybersecurity": "https://www.coursera.org/specializations/cybersecurity",
    "Data Science": "https://www.coursera.org/specializations/data-science-foundations-r"
}

@router.get(
    "/skills/suggest",
    summary="Suggest learning resources for specific skills",
    description="Returns a mapping of skills to educational URLs."
)
async def suggest_skills(
    skills: List[str] = Query(..., description="List of skills to get suggestions for")
) -> Dict[str, str]:
    """Returns matching courses for requested skills."""
    suggestions = {}
    for skill in skills:
        # Case-insensitive lookup
        match = next((v for k, v in COURSE_MAP.items() if k.lower() == skill.lower()), None)
        if match:
            suggestions[skill] = match
        else:
            # Default to general Coursera search for unknown skills
            suggestions[skill] = f"https://www.coursera.org/search?query={skill}"
            
    return suggestions
