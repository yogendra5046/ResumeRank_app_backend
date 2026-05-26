"""Presentation: FastAPI dependency injection container.

All application-layer dependencies are wired here.
FastAPI routes import only from this module — never directly from infrastructure.
"""

from functools import lru_cache
from typing import Annotated

import redis.asyncio as aioredis
from fastapi import Depends, Request

from src.application.use_cases.analyze_resume import AnalyzeResumeUseCase
from src.application.use_cases.gdpr_delete import GdprDeleteUseCase
from src.application.use_cases.get_job_status import GetJobStatusUseCase
from src.domain.services.scoring_service import ScoringService
from src.infrastructure.cache.redis_cache import RedisCacheAdapter
from src.infrastructure.jobs.job_store import JobStore
from src.infrastructure.ml.minilm_embedder import MiniLmEmbedder
from src.infrastructure.ml.tfidf_fallback import TfIdfFallbackEmbedder
from src.infrastructure.pdf.pymupdf_extractor import PyMuPdfExtractor
from src.infrastructure.security.clamav_scanner import ClamAvScanner
from src.domain.ports.cache_repository import CacheRepositoryPort
from src.domain.ports.scanner import ScannerPort
from src.domain.ports.embedder import EmbedderPort
from src.infrastructure.skills.esco_loader import EscoTaxonomy
from src.infrastructure.skills.networkx_graph import NetworkXSkillGraph
from src.domain.services.keyword_analyzer import KeywordAnalyzer
from src.domain.services.section_scorer import SectionScorer
from src.domain.services.ats_parse_checker import AtsParseChecker
from src.domain.services.tone_analyzer import ToneAnalyzer
from src.domain.services.resume_validator import ResumeValidator
from src.domain.services.salary_estimator import SalaryEstimator
from src.domain.services.persona_analyzer import PersonaAnalyzer
from src.domain.services.job_skill_mapper import JobSkillMapper


# ── Primitive adapters (no request scope – singletons via app.state) ──────────

def get_redis(request: Request) -> aioredis.Redis:  # type: ignore[type-arg]
    return request.app.state.redis  # type: ignore[no-any-return]


def get_taxonomy(request: Request) -> EscoTaxonomy:
    return request.app.state.taxonomy  # type: ignore[no-any-return]


def get_embedder(request: Request) -> EmbedderPort:
    return request.app.state.embedder  # type: ignore[no-any-return]


# ── Adapters assembled per-request (cheap, stateless) ─────────────────────────

def get_cache_adapter(request: Request) -> CacheRepositoryPort:
    return request.app.state.cache_adapter  # type: ignore[no-any-return]


def get_job_store(request: Request) -> JobStore:
    return request.app.state.job_store  # type: ignore[no-any-return]


def get_scanner(request: Request) -> ScannerPort:
    return request.app.state.scanner  # type: ignore[no-any-return]


def get_skill_graph(
    taxonomy: Annotated[EscoTaxonomy, Depends(get_taxonomy)],
) -> NetworkXSkillGraph:
    return NetworkXSkillGraph(taxonomy)


def get_keyword_analyzer(request: Request) -> KeywordAnalyzer:
    return request.app.state.keyword_analyzer  # type: ignore[no-any-return]


def get_section_scorer(request: Request) -> SectionScorer:
    return request.app.state.section_scorer  # type: ignore[no-any-return]


def get_ats_checker(request: Request) -> AtsParseChecker:
    return request.app.state.ats_checker  # type: ignore[no-any-return]


def get_pdf_extractor() -> PyMuPdfExtractor:
    return PyMuPdfExtractor()


def get_tone_analyzer(request: Request) -> ToneAnalyzer:
    return request.app.state.tone_analyzer  # type: ignore[no-any-return]


def get_scoring_service() -> ScoringService:
    return ScoringService()


def get_resume_validator(request: Request) -> ResumeValidator:
    return request.app.state.resume_validator


def get_salary_estimator(request: Request) -> SalaryEstimator:
    return request.app.state.salary_estimator


def get_persona_analyzer(request: Request) -> PersonaAnalyzer:
    return request.app.state.persona_analyzer


def get_skill_mapper(request: Request) -> JobSkillMapper:
    return request.app.state.skill_mapper


def get_analyze_use_case(
    scanner: Annotated[ScannerPort, Depends(get_scanner)],
    embedder: Annotated[EmbedderPort, Depends(get_embedder)],
    cache: Annotated[CacheRepositoryPort, Depends(get_cache_adapter)],
    job_store: Annotated[JobStore, Depends(get_job_store)],
    skill_graph: Annotated[NetworkXSkillGraph, Depends(get_skill_graph)],
    scoring: Annotated[ScoringService, Depends(get_scoring_service)],
    extractor: Annotated[PyMuPdfExtractor, Depends(get_pdf_extractor)],
    keyword_analyzer: Annotated[KeywordAnalyzer, Depends(get_keyword_analyzer)],
    section_scorer: Annotated[SectionScorer, Depends(get_section_scorer)],
    ats_checker: Annotated[AtsParseChecker, Depends(get_ats_checker)],
    tone_analyzer: Annotated[ToneAnalyzer, Depends(get_tone_analyzer)],
    resume_validator: Annotated[ResumeValidator, Depends(get_resume_validator)],
    salary_estimator: Annotated[SalaryEstimator, Depends(get_salary_estimator)],
    persona_analyzer: Annotated[PersonaAnalyzer, Depends(get_persona_analyzer)],
) -> AnalyzeResumeUseCase:
    return AnalyzeResumeUseCase(
        scanner=scanner,
        extractor=extractor,
        embedder=embedder,
        cache=cache,
        skill_graph=skill_graph,
        job_store=job_store,
        scoring_service=scoring,
        keyword_analyzer=keyword_analyzer,
        section_scorer=section_scorer,
        ats_checker=ats_checker,
        tone_analyzer=tone_analyzer,
        resume_validator=resume_validator,
        salary_estimator=salary_estimator,
        persona_analyzer=persona_analyzer,
    )




def get_status_use_case(
    job_store: Annotated[JobStore, Depends(get_job_store)],
) -> GetJobStatusUseCase:
    return GetJobStatusUseCase(job_store)


from fastapi.security import OAuth2PasswordBearer
from src.infrastructure.security.auth_service import AuthService
from src.domain.models.user import User
from src.infrastructure.database import get_db
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/v1/auth/login")

def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[Session, Depends(get_db)]
) -> User:
    payload = AuthService.decode_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    email: str = payload.get("sub")
    if email is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    return user

def get_gdpr_use_case(
    cache: Annotated[CacheRepositoryPort, Depends(get_cache_adapter)],
    job_store: Annotated[JobStore, Depends(get_job_store)],
) -> GdprDeleteUseCase:
    return GdprDeleteUseCase(cache=cache, job_store=job_store)
