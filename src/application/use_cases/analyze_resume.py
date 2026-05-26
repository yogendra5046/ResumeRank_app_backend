import asyncio
import hashlib
import structlog
import orjson
from typing import Optional

from src.application.dto.score_response import AsyncJobAccepted, ScoreResponse

from src.domain.ports.cache_repository import CacheRepositoryPort
from src.domain.ports.pdf_extractor import PdfExtractorPort
from src.infrastructure.jobs.job_store import JobStore

logger = structlog.get_logger(__name__)

_REQUEST_TIMEOUT_S = 10.0

class AnalyzeResumeUseCase:
    def __init__(
        self,
        cache: CacheRepositoryPort,
        job_store: JobStore,
        extractor: PdfExtractorPort,
        **kwargs
    ):
        self._cache = cache
        self._job_store = job_store
        self._extractor = extractor
        
        # New dependencies for advanced analysis
        self._scanner = kwargs.get("scanner")
        self._embedder = kwargs.get("embedder")
        self._section_scorer = kwargs.get("section_scorer")
        self._tone_analyzer = kwargs.get("tone_analyzer")
        self._resume_validator = kwargs.get("resume_validator")
        self._salary_estimator = kwargs.get("salary_estimator")
        self._persona_analyzer = kwargs.get("persona_analyzer")



    async def execute(
        self,
        pdf_bytes: bytes,
        filename: str,
        raw_jd: str,
        trace_id: str,
        base_url: str,
    ) -> ScoreResponse | AsyncJobAccepted:
        log = logger.bind(trace_id=trace_id, pdf_size=len(pdf_bytes))

        try:
            result = await asyncio.wait_for(
                self._pipeline(pdf_bytes, filename, raw_jd, log),
                timeout=_REQUEST_TIMEOUT_S,
            )
            return result
        except asyncio.TimeoutError:
            log.warning("pipeline_timeout", timeout_s=_REQUEST_TIMEOUT_S)
            job_id = await self._job_store.enqueue(
                pdf_bytes=pdf_bytes,
                filename=filename,
                raw_jd=raw_jd,
                trace_id=trace_id,
            )
            return AsyncJobAccepted(
                job_id=job_id,
                poll_url=f"{base_url}/status/{job_id}",
            )

    async def _pipeline(
        self,
        pdf_bytes: bytes,
        filename: str,
        raw_jd: str,
        log: structlog.stdlib.BoundLogger,
    ) -> ScoreResponse:
        # 0. Malware check
        if self._scanner:
            scan_res = await self._scanner.scan(pdf_bytes, filename)
            if not scan_res.is_clean:
                raise ValueError(f"malware detected: {scan_res.threat_name}")

        # 1. Caching
        resume_sha = hashlib.sha256(pdf_bytes).hexdigest()
        jd_sha = hashlib.sha256(raw_jd.encode()).hexdigest()
        cache_key = hashlib.sha256(f"{resume_sha}:{jd_sha}".encode()).hexdigest()
        
        cached = await self._cache.get(cache_key)
        if cached is not None:
            log.info("cache_hit", cache_key=cache_key[:16])
            result_dict = orjson.loads(cached)
            result_dict["from_cache"] = True
            return ScoreResponse(**result_dict)

        log.info("cache_miss", cache_key=cache_key[:16])

        # 2. Extract Text
        resume_text = await self._extractor.extract(pdf_bytes)
        if not resume_text or not resume_text.strip():
            raise ValueError("No text extracted from PDF.")
        log.info("pdf_text_extracted", chars=len(resume_text))

        # 2.1 Validate if it's actually a resume
        if self._resume_validator:
            validation = self._resume_validator.validate(resume_text)
            if not validation["is_resume"]:
                log.warning("unrelated_pdf_detected", reasons=validation["reasons"])
                from fastapi import HTTPException
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid Document: This doesn't look like a resume. {'. '.join(validation['reasons'])}"
                )


        # 3. Advanced Local Analysis (Non-AI)
        tone_results = {}
        semantic_score = 0.0
        semantic_skill_matches = []
        salary_data = {}
        persona_data = {}
        
        # Parallelize independent analysis tasks
        async def get_semantic_match():
            if self._embedder:
                try:
                    r_vec = await self._embedder.embed(resume_text[:10000])
                    j_vec = await self._embedder.embed(raw_jd[:10000])
                    import numpy as np
                    return float(np.dot(r_vec, j_vec)) * 100
                except Exception:
                    return 0.0
            return 0.0

        async def get_granular_matches():
            """New: Hybrid Semantic Skill Bridging"""
            if not self._embedder:
                return []
            try:
                # 1. Extract potential skills from JD
                from src.domain.services.ats_scorer import ats_scorer
                jd_keywords = ats_scorer._extract_hard_skills(raw_jd)
                if not jd_keywords: return []
                
                # 2. Extract noun chunks from resume
                import spacy
                nlp = spacy.load("en_core_web_sm")
                doc = nlp(resume_text.lower()[:4000])
                resume_chunks = list(set([chunk.text for chunk in doc.noun_chunks if len(chunk.text) > 3]))
                
                # 3. Semantic comparison (limited to top 5 JD skills for speed)
                matches = []
                for skill in jd_keywords[:8]:
                    s_vec = await self._embedder.embed(skill)
                    for chunk in resume_chunks[:20]: # Check most relevant chunks
                        c_vec = await self._embedder.embed(chunk)
                        import numpy as np
                        sim = float(np.dot(s_vec, c_vec))
                        if sim > 0.82: # High semantic similarity threshold
                            matches.append({"skill": skill, "matched_as": chunk, "similarity": sim})
                            break
                return matches
            except Exception as e:
                log.error("granular_match_failed", error=str(e))
                return []

        tasks = [
            self._tone_analyzer.analyze(resume_text) if self._tone_analyzer else asyncio.sleep(0, {}),
            get_semantic_match(),
            get_granular_matches()
        ]
        
        tone_results, semantic_score, semantic_skill_matches = await asyncio.gather(*tasks)

        # Run synchronous analysis
        if self._salary_estimator:
            # We'll pass an empty skill list for now, it will be refined in the unified scorer
            salary_data = self._salary_estimator.estimate(resume_text, [])
            
        if self._persona_analyzer:
            persona_data = self._persona_analyzer.analyze(resume_text)

        # 4. Run unified ATS Scorer
        from src.domain.services.scoring import analyze_resume_full
        loop = asyncio.get_running_loop()
        try:
            score_dict = await loop.run_in_executor(
                None, 
                analyze_resume_full, 
                resume_text, 
                raw_jd, 
                pdf_bytes,
                tone_results,
                semantic_score,
                salary_data,
                persona_data,
                semantic_skill_matches
            )
        except Exception as e:
            log.error("core_scorer_failed", error=str(e))
            # Critical Fallback: Return a baseline score if the advanced engine crashes
            score_dict = {
                "overall_score": 50,
                "score": 50,
                "grade": "C",
                "suggestions": ["The analysis engine encountered a complex formatting issue. Please try a simpler PDF layout."],
                "matched_skills": [],
                "missing_skills": [],
                "raw_resume_text": resume_text,
                "raw_jd_text": raw_jd
            }
        
        response = ScoreResponse(**score_dict)

        # 3. Cache store (fire-and-forget)
        asyncio.ensure_future(
            self._cache.set(cache_key, orjson.dumps(response.model_dump()))
        )

        log.info(
            "pipeline_complete",
            overall_score=response.overall_score,
            from_cache=False,
        )
        return response
