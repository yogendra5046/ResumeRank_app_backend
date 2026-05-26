from __future__ import annotations
from typing import Literal, Any, List, Optional, Dict
from pydantic import BaseModel, Field

class ScoreDetail(BaseModel):
    score: int = Field(0, description="Component score 0-100")
    details: List[str] = Field(default_factory=list, description="Reasoning or notes for the score")
    debug_text: Optional[str] = Field(None, description="Debug text if score is 0")

class SkillGraphItem(BaseModel):
    skill: str
    status: str
    jd_count: int
    resume_count: int

class SkillGapDetail(BaseModel):
    match_percent: int
    matched_skills: List[str]
    missing_skills: List[str]
    skill_graph_data: List[SkillGraphItem]

class ScoreBreakdown(BaseModel):
    keywords: int = 0
    relevance: int = 0
    impact: int = 0
    presentation: int = 0

class WeightedSkill(BaseModel):
    name: str
    weight: int
    context: str = ""
    boost: float = 1.0
    importance: str = "Medium" # Critical, High, Medium

class SkillCategory(BaseModel):
    name: str
    category: str
    matched: int
    total: int
    percent: int
    status: str
    skills: List[str] = Field(default_factory=list)

class VerbStats(BaseModel):
    strong: int
    weak: int
    ratio: int

class EstimatedSalary(BaseModel):
    category: str = "General"
    estimated_range: str = "N/A"
    experience_detected: str = "0+ Years"
    seniority: str = "Entry"
    raw_lpa: Optional[float] = None
    currency: str = "INR"
    top_valuable_skills: List[str] = Field(default_factory=list)

class ProfessionalPersona(BaseModel):
    primary_persona: str = "Generalist"
    description: str = "A balanced professional profile."
    persona_breakdown: Dict[str, int] = Field(default_factory=dict)
    top_traits: List[str] = Field(default_factory=list)

class CriticalSkillItem(BaseModel):
    name: str
    weight: int
    jobs: str
    points: int

class JDRedFlag(BaseModel):
    flag: str
    description: str
    severity: str # High, Medium, Low

class AuthenticityCheck(BaseModel):
    score: int
    jd_similarity: float
    plagiarism_risk: str # High, Medium, Low
    details: List[str]

class ScoreResponse(BaseModel):
    overall_score: int = Field(..., description="Overall score 0-100")
    score: int = Field(..., description="Alias for overall_score")
    grade: str = Field(..., description="Letter grade A/B/C/D")
    percentile: int = Field(50, description="Simulated percentile")
    percentile_text: str = Field("", description="Comparison text for UI")
    
    score_breakdown: ScoreBreakdown
    matched_skills: List[WeightedSkill]
    missing_skills: List[WeightedSkill]
    skill_gap_chart: List[SkillCategory]
    suggestions: List[str]
    gaps: List[str]
    verb_analysis: VerbStats
    
    impact: ScoreDetail
    format: ScoreDetail
    skill_gap: SkillGapDetail
    ats_parse: ScoreDetail
    
    estimated_salary: EstimatedSalary = Field(default_factory=EstimatedSalary)
    professional_persona: ProfessionalPersona = Field(default_factory=ProfessionalPersona)
    critical_missing: List[CriticalSkillItem] = Field(default_factory=list)
    missing_keywords: List[str] = Field(default_factory=list)
    missing_skills_list: List[str] = Field(default_factory=list)
    
    from_cache: bool = Field(False)
    raw_resume_text: str = Field("")
    raw_jd_text: str = Field("")
    jd_keywords: List[str] = Field(default_factory=list)
    
    jd_red_flags: List[JDRedFlag] = Field(default_factory=list)
    authenticity_check: AuthenticityCheck = Field(default_factory=lambda: AuthenticityCheck(score=100, jd_similarity=0.0, plagiarism_risk="Low", details=[]))
    roast: List[str] = Field(default_factory=list)
    
    # Career Accelerator Features
    negotiation_scripts: List[Dict[str, str]] = Field(default_factory=list) # [{scenario: str, script: str}]
    outreach_templates: List[Dict[str, str]] = Field(default_factory=list) # [{type: str, message: str}]
    culture_bio: str = Field("")
    gap_projects: List[Dict[str, str]] = Field(default_factory=list) # [{skill: str, project: str, spec: str}]
    cover_letter: str = Field("")
    career_guidance: Dict[str, Any] = Field(default_factory=dict)

class AsyncJobAccepted(BaseModel):
    status: Literal["accepted"] = "accepted"
    job_id: str
    poll_url: str

class JobStatusResponse(BaseModel):
    job_id: str
    status: Literal["pending", "processing", "done", "failed"]
    result: ScoreResponse | None = None
    error: str | None = None
