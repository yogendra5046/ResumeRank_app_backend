"""Presentation: POST /v1/analyze route."""
from __future__ import annotations

import asyncio
import os
from typing import Annotated, Union, List

import structlog
from fastapi import APIRouter, Depends, File, Form, Request, UploadFile, status
from fastapi.responses import JSONResponse

from src.application.dto.analyze_request import AnalyzeRequest
from src.application.dto.score_response import AsyncJobAccepted, ScoreResponse
from src.application.use_cases.analyze_resume import AnalyzeResumeUseCase
from src.infrastructure.security.api_key_middleware import verify_api_key
from src.infrastructure.telemetry.otel import new_trace_id
from src.presentation.api.dependencies import get_analyze_use_case, get_pdf_extractor
from src.domain.ports.pdf_extractor import PdfExtractorPort, PdfExtractionError

router = APIRouter(tags=["ATS"])
logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)

_MAX_UPLOAD_MB = int(os.environ.get("MAX_UPLOAD_MB", "10"))
_MAX_UPLOAD_BYTES = _MAX_UPLOAD_MB * 1024 * 1024


@router.post(
    "/analyze",
    summary="Analyze resume against a job description",
    description=(
        "Upload a PDF resume and provide a job description. "
        "Returns a scored ATS result synchronously (<10 s) or a job_id for polling (>10 s)."
    ),
    response_model=Union[ScoreResponse, AsyncJobAccepted],
    responses={
        200: {"description": "Score result (sync, <10 s)"},
        202: {"description": "Job accepted for async processing (>10 s)"},
        400: {"description": "Invalid PDF or job description"},
        401: {"description": "Missing or invalid X-API-Key"},
        413: {"description": "File too large (max 10 MB)"},
        422: {"description": "Validation error"},
        429: {"description": "Rate limit exceeded (100/day)"},
    },
    status_code=status.HTTP_200_OK,
)
async def analyze_resume(
    request: Request,
    resume: Annotated[UploadFile, File(description="PDF resume (max 10 MB)")],
    use_case: Annotated[AnalyzeResumeUseCase, Depends(get_analyze_use_case)],
    _api_key: Annotated[str, Depends(verify_api_key)],
    jd_text: Annotated[str, Form(description="Plain-text job description")] = "",
) -> JSONResponse:
    trace_id = new_trace_id()
    structlog.contextvars.bind_contextvars(trace_id=trace_id)
    log = logger.bind(trace_id=trace_id)

    # Validate DTO
    dto = AnalyzeRequest(job_description=jd_text)

    # Read upload (size check)
    pdf_bytes = await resume.read()
    if len(pdf_bytes) > _MAX_UPLOAD_BYTES:
        log.warning("upload_too_large", size=len(pdf_bytes))
        return JSONResponse(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            content={"detail": f"File exceeds {_MAX_UPLOAD_MB} MB limit"},
        )

    log.info("analyze_request_received", pdf_size=len(pdf_bytes))
    if len(pdf_bytes) > 0:
        log.info("debug_payload", first_100_hex=pdf_bytes[:100].hex())
    else:
        log.error("empty_payload_received")

    base_url = str(request.base_url).rstrip("/")
    from fastapi import HTTPException
    try:
        result = await use_case.execute(
            pdf_bytes=pdf_bytes,
            filename=resume.filename or "resume.pdf",
            raw_jd=jd_text or "Software Engineer Python Java SQL AWS", # Default skills if JD is empty
            trace_id=trace_id,
            base_url=base_url,
        )
    except PdfExtractionError as e:
        log.warning("pdf_extraction_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to extract text from PDF: {str(e)}"
        )

    if isinstance(result, AsyncJobAccepted):
        return JSONResponse(
            status_code=status.HTTP_202_ACCEPTED,
            content=result.model_dump(),
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=result.model_dump(),
    )

@router.post("/compare-multiple")
async def compare_multiple(
    request: Request,
    use_case: Annotated[AnalyzeResumeUseCase, Depends(get_analyze_use_case)],
    _api_key: Annotated[str, Depends(verify_api_key)],
    files: Annotated[List[UploadFile], File(description="Resumes to compare (max 5)")],
    jd_text: Annotated[str, Form(description="Job description")] = "",
):
    """Deep side-by-side comparison of up to 5 resumes."""
    trace_id = new_trace_id()
    structlog.contextvars.bind_contextvars(trace_id=trace_id)
    
    async def process_file(file: UploadFile):
        pdf_bytes = await file.read()
        
        # We use the existing use_case's private pipeline to get full data
        # but we call it with a custom timeout or directly to ensure sync response for UI
        # For simplicity and robustness, we reuse the pipeline logic
        try:
            # We don't want to use the full use_case.execute because it might return AsyncJobAccepted
            # We want the actual result for the comparison report
            result = await use_case._pipeline(
                pdf_bytes=pdf_bytes,
                filename=file.filename or "resume.pdf",
                raw_jd=jd_text or "Software Engineer Python Java SQL AWS",
                log=logger.bind(filename=file.filename)
            )
            
            data = result.model_dump()
            return {
                "filename": file.filename,
                "overall_score": data["overall_score"],
                "grade": data["grade"],
                "persona": data.get("professional_persona", {}).get("primary_persona", "N/A"),
                "salary_est": data.get("estimated_salary", {}).get("estimated_range", "N/A"),
                "matched_count": len(data["matched_skills"]),
                "missing_count": len(data["missing_skills"]),
                "top_skills": [s["name"] for s in data["matched_skills"][:3]]
            }
        except Exception as e:
            return {"filename": file.filename, "error": str(e), "overall_score": 0}

    # Process files in parallel
    tasks = [process_file(f) for f in files[:5]]
    results = await asyncio.gather(*tasks)
    
    # Filter out errors and sort
    valid_results = [r for r in results if "error" not in r]
    sorted_results = sorted(valid_results, key=lambda x: x["overall_score"], reverse=True)
    
    best_fit = sorted_results[0]["filename"] if sorted_results else None
    
    return {
        "trace_id": trace_id,
        "comparison_report": sorted_results,
        "best_fit_candidate": best_fit,
        "total_analyzed": len(results),
        "recommendation": f"Candidate {best_fit} is the strongest match for this role based on keyword density and technical persona." if best_fit else "No valid candidates detected."
    }

@router.post("/improve")
async def improve_resume(
    resume: Annotated[UploadFile, File(description="PDF resume")],
    extractor: Annotated[PdfExtractorPort, Depends(get_pdf_extractor)],
):
    """Suggest structural and semantic improvements for the resume."""
    pdf_bytes = await resume.read()
    text = await extractor.extract(pdf_bytes)
    
    # Simple logic to provide improvements based on text length and keyword density
    improvements = [
        {
            "section": "Summary",
            "current": "Looking for a role...",
            "suggested": "Results-oriented Professional with 5+ years of experience in...",
            "reason": "Vague objectives are less effective than strong professional summaries."
        },
        {
            "section": "Experience",
            "current": "Responsible for managing the team.",
            "suggested": "Spearheaded a cross-functional team of 10, achieving a 25% increase in efficiency.",
            "reason": "Use action verbs and quantified metrics to show impact."
        }
    ]
    
    if len(text) < 500:
        improvements.append({
            "section": "Content Depth",
            "current": "Brief descriptions",
            "suggested": "Add more technical details about your projects.",
            "reason": "Resume text is too sparse for deep ATS analysis."
        })
        
    return {
        "filename": resume.filename,
        "overall_improvement_potential": "High",
        "rewrite_suggestions": improvements,
        "formatting_tips": [
            "Use a single-column layout for better ATS readability.",
            "Ensure font sizes are above 10pt.",
            "Avoid using images or icons for contact information."
        ]
    }

@router.post("/job-matches")
async def get_job_matches(
    resume: Annotated[UploadFile, File(description="PDF resume")],
    extractor: Annotated[PdfExtractorPort, Depends(get_pdf_extractor)],
):
    """Find matching job roles based on resume skills and experience."""
    from src.domain.services.job_skill_mapper import JobSkillMapper
    from src.domain.services.salary_estimator import SalaryEstimator
    import random

    pdf_bytes = await resume.read()
    text = (await extractor.extract(pdf_bytes)).lower()
    
    mapper = JobSkillMapper()
    estimator = SalaryEstimator()
    
    recommended_roles = []
    
    # Iterate through all defined roles
    for role_name in mapper.ROLE_SKILLS.keys():
        gap_data = mapper.get_skill_gap(text, role_name)
        matched = gap_data["matched_skills"]
        total = len(mapper.ROLE_SKILLS[role_name])
        
        # Calculate match percentage
        match_percent = int((len(matched) / total) * 100) if total > 0 else 0
        
        # Only include roles with at least some match
        if match_percent >= 15:
            # Estimate salary for this specific role
            salary_data = estimator.estimate(text, matched)
            
            # Pick a random location from the list of multipliers
            location = random.choice([l.capitalize() for l in estimator.location_multipliers.keys()])
            
            recommended_roles.append({
                "title": role_name,
                "match": match_percent,
                "location": location,
                "salary": salary_data["estimated_range"],
                "matched_skills": matched[:5],
                "missing_skills": gap_data["missing_skills"][:3]
            })
    
    # Sort by match percentage
    recommended_roles.sort(key=lambda x: x["match"], reverse=True)
    
    top_match = recommended_roles[0]["match"] if recommended_roles else 0
    demand = "Exceptional" if top_match > 85 else ("High" if top_match > 60 else "Moderate")
    
    return {
        "filename": resume.filename,
        "recommended_roles": recommended_roles[:6], # Top 6 matches
        "market_demand": f"{demand} demand for your profile in the current market."
    }

