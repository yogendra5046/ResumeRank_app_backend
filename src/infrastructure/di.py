"""Infrastructure: Dependency Injection and ML model preloading."""
from __future__ import annotations

import asyncio
import spacy
import structlog
from sentence_transformers import SentenceTransformer
from src.infrastructure.ml.minilm_embedder import MiniLmEmbedder
from src.infrastructure.ml.tfidf_fallback import TfIdfFallbackEmbedder
from src.domain.services.tone_analyzer import ToneAnalyzer

logger = structlog.get_logger(__name__)

async def preload_models(app_state: any) -> None:
    """Preload all heavy ML models to avoid timeout on first request."""
    logger.info("ml_models_preloading_start")
    
    # 1. Use TF-IDF Embedder (Saves ~300MB RAM vs MiniLM for free tier)
    embedder = TfIdfFallbackEmbedder()
    app_state.embedder = embedder
    
    # 2. Preload spaCy (for ToneAnalyzer)
    loop = asyncio.get_running_loop()
    nlp = None
    try:
        logger.info("spacy_preloading", model="en_core_web_sm")
        nlp = await loop.run_in_executor(None, lambda: spacy.load("en_core_web_sm", disable=["ner", "lemmatizer"]))
        logger.info("spacy_preloading_success")
    except Exception as e:
        logger.error("spacy_preloading_failed", error=str(e))

    # 3. Initialize Services with preloaded components
    from src.domain.services.keyword_analyzer import KeywordAnalyzer
    from src.domain.services.section_scorer import SectionScorer
    from src.domain.services.ats_parse_checker import AtsParseChecker
    from src.domain.services.resume_validator import ResumeValidator
    from src.domain.services.salary_estimator import SalaryEstimator
    from src.domain.services.persona_analyzer import PersonaAnalyzer
    
    app_state.keyword_analyzer = KeywordAnalyzer()
    app_state.section_scorer = SectionScorer(embedder)
    app_state.ats_checker = AtsParseChecker()
    app_state.tone_analyzer = ToneAnalyzer(nlp=nlp)
    app_state.resume_validator = ResumeValidator()
    app_state.salary_estimator = SalaryEstimator()
    app_state.persona_analyzer = PersonaAnalyzer()
    
    from src.domain.services.job_skill_mapper import JobSkillMapper
    app_state.skill_mapper = JobSkillMapper()


    
    logger.info("ml_models_preloading_complete")
