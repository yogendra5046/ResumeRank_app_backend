"""Infrastructure: Dependency Injection and ML model preloading."""
from __future__ import annotations
import asyncio
import structlog
from src.infrastructure.ml.tfidf_fallback import TfIdfFallbackEmbedder
from src.domain.services.tone_analyzer import ToneAnalyzer

logger = structlog.get_logger(__name__)

async def preload_models(app_state: any) -> None:
    """Preload all heavy ML models to avoid timeout on first request."""
    logger.info("ml_models_preloading_start")
    import os
    use_advanced_ml = os.getenv("USE_ADVANCED_ML", "false").lower() == "true"
    
    if use_advanced_ml:
        logger.info("loading_advanced_ml_models (PyTorch/spaCy)")
        from src.infrastructure.ml.minilm_embedder import MiniLmEmbedder
        embedder = MiniLmEmbedder()
        import spacy
        try:
            nlp = spacy.load("en_core_web_sm")
        except OSError:
            import spacy.cli
            spacy.cli.download("en_core_web_sm")
            nlp = spacy.load("en_core_web_sm")
    else:
        logger.info("loading_lightweight_ml_models (TF-IDF/Regex)")
        embedder = TfIdfFallbackEmbedder()
        nlp = None
    
    app_state.embedder = embedder

    # 3. Initialize Services with preloaded components
    from src.domain.services.keyword_analyzer import KeywordAnalyzer
    from src.domain.services.section_scorer import SectionScorer
    from src.domain.services.ats_parse_checker import AtsParseChecker
    from src.domain.services.resume_validator import ResumeValidator
    from src.domain.services.job_description_validator import JobDescriptionValidator
    from src.domain.services.salary_estimator import SalaryEstimator
    from src.domain.services.persona_analyzer import PersonaAnalyzer
    
    app_state.keyword_analyzer = KeywordAnalyzer()
    app_state.section_scorer = SectionScorer(embedder)
    app_state.ats_checker = AtsParseChecker()
    app_state.tone_analyzer = ToneAnalyzer(nlp=nlp)
    app_state.resume_validator = ResumeValidator()
    app_state.job_description_validator = JobDescriptionValidator()
    app_state.salary_estimator = SalaryEstimator()
    app_state.persona_analyzer = PersonaAnalyzer()
    
    from src.domain.services.job_skill_mapper import JobSkillMapper
    app_state.skill_mapper = JobSkillMapper()


    
    logger.info("ml_models_preloading_complete")
