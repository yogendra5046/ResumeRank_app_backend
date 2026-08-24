"""Domain service: Tone and readability analyzer."""
from __future__ import annotations

import asyncio
import functools
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any

import spacy
import textstat
import structlog

logger = structlog.get_logger(__name__)

# Shared executor for CPU-bound NLP tasks
_EXECUTOR = ThreadPoolExecutor(max_workers=2, thread_name_prefix="tone-worker")

class ToneAnalyzer:
    """Analyzes resume tone, passive voice, and readability."""

    def __init__(self, nlp: Any | None = None) -> None:
        self._nlp = nlp
            
        self._weak_verbs = {"responsible", "worked", "helped", "assisted", "assigned", "handled"}
        self._strong_verbs = {"led", "built", "architected", "reduced", "increased", "developed", "managed", "orchestrated", "implemented"}

    async def analyze(self, text: str) -> Dict[str, Any]:
        """Runs NLP analysis in a thread pool."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            _EXECUTOR,
            functools.partial(self._analyze_sync, text)
        )

    def _analyze_sync(self, text: str) -> Dict[str, Any]:
        """Synchronous tone analysis using spaCy and textstat."""
        if not self._nlp:
            return self._default_response()

        doc = self._nlp(text)
        
        passive_voice_count = 0
        weak_verb_count = 0
        strong_verb_count = 0
        
        for token in doc:
            # 1. Passive voice detection (auxpass dependency)
            if token.dep_ == "auxpass":
                passive_voice_count += 1
            
            # 2. Verb strength detection
            if token.pos_ in ("VERB", "AUX"):
                text_lower = token.text.lower()
                if text_lower in self._weak_verbs:
                    weak_verb_count += 1
                elif text_lower in self._strong_verbs:
                    strong_verb_count += 1

        total_verbs = weak_verb_count + strong_verb_count
        professional_score = (strong_verb_count / total_verbs) if total_verbs > 0 else 0.5
        
        return {
            "professional": round(professional_score, 2),
            "passive_voice_count": passive_voice_count,
            "weak_verb_count": weak_verb_count,
            "strong_verb_count": strong_verb_count,
            "readability": textstat.flesch_reading_ease(text)
        }

    def _default_response(self) -> Dict[str, Any]:
        return {
            "professional": 0.0,
            "passive_voice_count": 0,
            "weak_verb_count": 0,
            "strong_verb_count": 0,
            "readability": 0.0
        }
