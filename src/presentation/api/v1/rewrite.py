import re
import os
import json
from typing import Annotated, List, Any
import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
import traceback
from groq import AsyncGroq
import httpx
from src.infrastructure.security.api_key_middleware import verify_api_key

router = APIRouter(tags=["AI"])
logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)

class RewriteRequest(BaseModel):
    resume_text: str = Field(..., description="Full resume text")
    jd_text: str = Field(..., description="Job description")
    missing_skills: List[str] = Field(default_factory=list)
    weak_sections: List[str] = Field(default_factory=list)

class SkillRoute(BaseModel):
    skill: str
    path: str
    project: str
    time: str
    url: str = "https://www.google.com/search?q=learn+"

class RewriteResponse(BaseModel):
    rewritten_text: str
    detailed_enhancements: List[str] = Field(default_factory=list, description="Specific rank boosting suggestions")
    skill_route_map: List[SkillRoute] = Field(default_factory=list, description="Learning paths for missing skills")
    tokens_used: int

from ....domain.services.ats_scorer import ats_scorer

@router.post(
    "/audit",
    summary="Rule-based Resume Audit (No API Key Required)",
)
async def resume_audit(
    request: RewriteRequest,
):
    """
    Performs a deterministic audit of keywords, sections, and verbs.
    """
    report = ats_scorer.get_audit_report(request.resume_text, request.jd_text)
    return report

@router.post(
    "/rewrite",
    summary="Detailed AI Resume Enhancement",
    response_model=RewriteResponse,
    status_code=status.HTTP_200_OK,
)
async def rewrite_resume(
    request: RewriteRequest,
    _api_key: Annotated[str, Depends(verify_api_key)],
) -> RewriteResponse:
    groq_key = os.environ.get("GROQ_API_KEY")
    if not groq_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="GROQ_API_KEY not configured on server"
        )

    from groq import Groq
    from fastapi.concurrency import run_in_threadpool
    client = Groq(api_key=groq_key)

    system_prompt = (
        "You are the world's most advanced AI Resume Ranker and Career Architect. "
        "Your goal is to transform a standard resume into a top 1% candidate profile. "
        "Analyze the provided Resume, Job Description (JD), and missing skills. "
        "You must return a JSON object with the following fields: "
        "1. 'rewritten_text': A complete, highly optimized rewrite of the ENTIRE resume. Integrate the missing skills naturally and aggressively improve the weak sections using strong action verbs and quantified metrics. Use clean Markdown formatting (e.g., ### for sections, - for bullets). "
        "   IMPORTANT: Highlight edited or newly added words/phrases using Markdown bold syntax like **this**. "
        "2. 'detailed_enhancements': A list of strings. Each string must combine what is missing and what to do, e.g., "
        "   [\"WHAT IS MISSING: [Gap]. WHAT TO DO: [Action]\", ...] "
        "3. 'skill_route_map': A list of objects for each missing skill, containing: "
        "   - 'skill': Name of the skill. "
        "   - 'path': Specific learning resource (e.g., 'Official Kubernetes Docs'). "
        "   - 'project': A specific project idea to demonstrate this skill. "
        "   - 'time': Estimated time to proficiency. "
        "   - 'url': A real, high-quality URL to a learning resource. "
        "Respond ONLY with a valid JSON object. No preamble or markdown code blocks outside the JSON."
    )
    
    user_prompt = (
        f"JD: {request.jd_text}\n"
        f"Resume: {request.resume_text}\n"
        f"Missing Skills: {', '.join(request.missing_skills)}\n"
        f"Target Sections: {', '.join(request.weak_sections)}"
    )

    primary_model = "llama-3.3-70b-versatile"
    fallback_model = "mixtral-8x7b-32768"

    import requests

    def call_groq_sync(model_name: str):
        safe_resume = request.resume_text[:4000] if len(request.resume_text) > 4000 else request.resume_text
        safe_jd = request.jd_text[:1500] if len(request.jd_text) > 1500 else request.jd_text
        
        headers = {
            "Authorization": f"Bearer {groq_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": (
                    f"JD: {safe_jd}\n"
                    f"Resume: {safe_resume}\n"
                    f"Missing Skills: {', '.join(request.missing_skills)}\n"
                    f"Target Sections: {', '.join(request.weak_sections)}"
                )},
            ],
            "temperature": 0.2,
            "max_tokens": 6000,
            "response_format": {"type": "json_object"}
        }
        
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=90.0
        )
        response.raise_for_status()
        return response.json()

    try:
        try:
            logger.info("groq_enhance_attempt", model=primary_model)
            completion_data = await run_in_threadpool(call_groq_sync, primary_model)
        except Exception as e:
            logger.warning("groq_primary_failed_trying_fallback", error=str(e), traceback=traceback.format_exc())
            completion_data = await run_in_threadpool(call_groq_sync, fallback_model)

        raw_content = completion_data["choices"][0]["message"]["content"]
        
        # Robust JSON extraction: Handle markdown code blocks
        if "```json" in raw_content:
            raw_content = re.search(r"```json\s*(.*?)\s*```", raw_content, re.DOTALL).group(1)
        elif "```" in raw_content:
            raw_content = re.search(r"```\s*(.*?)\s*```", raw_content, re.DOTALL).group(1)
            
        ai_data = json.loads(raw_content)
        
        # 1. Normalize rewritten_text (handle dict or list from AI)
        raw_rewritten = ai_data.get("rewritten_text", "Failed to rewrite sections.")
        if isinstance(raw_rewritten, dict):
            # Convert section dictionary to formatted Markdown
            rewritten_text = "\n\n".join([f"### {k}\n{v}" for k, v in raw_rewritten.items()])
        elif isinstance(raw_rewritten, list):
            rewritten_text = "\n".join([str(x) for x in raw_rewritten])
        else:
            rewritten_text = str(raw_rewritten)

        # 2. Normalize detailed_enhancements
        raw_enhancements = ai_data.get("detailed_enhancements", [])
        if not isinstance(raw_enhancements, list):
            detailed_enhancements = [str(raw_enhancements)] if raw_enhancements else []
        else:
            detailed_enhancements = [str(e) for e in raw_enhancements]

        # 3. Normalize skill_route_map
        raw_map = ai_data.get("skill_route_map", [])
        skill_route_map = []
        if isinstance(raw_map, list):
            for item in raw_map:
                if isinstance(item, dict):
                    # Ensure all fields exist for SkillRoute model
                    skill_route_map.append({
                        "skill": str(item.get("skill", "Unknown")),
                        "path": str(item.get("path", "Explore online documentation")),
                        "project": str(item.get("project", "Build a sample application")),
                        "time": str(item.get("time", "1-2 weeks")),
                        "url": str(item.get("url", "https://www.google.com/search?q=learn+skill"))
                    })

        tokens = completion_data.get("usage", {}).get("total_tokens", 0)
        
        return RewriteResponse(
            rewritten_text=rewritten_text,
            detailed_enhancements=detailed_enhancements,
            skill_route_map=skill_route_map,
            tokens_used=tokens
        )
    except Exception as e:
        logger.error("groq_enhance_failed_all_models", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"AI service error: {str(e)}"
        )

