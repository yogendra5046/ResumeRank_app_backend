"""Domain service: Section-wise resume scorer."""
from __future__ import annotations

import re
import asyncio
import numpy as np
from typing import Dict

from src.domain.ports.embedder import EmbedderPort

class SectionScorer:
    """Splits resume into sections and scores each against the JD."""

    def __init__(self, embedder: EmbedderPort) -> None:
        self._embedder = embedder
        # Matches common section headers
        self._section_pattern = re.compile(
            r"\b(experience|skills|education|projects|summary|professional experience|work history|technical skills|academic background)\b",
            re.IGNORECASE
        )

    async def score(self, resume_text: str, jd_embedding: np.ndarray) -> Dict[str, float]:
        """Calculates cosine similarity for each detected section.
        
        Args:
            resume_text: Full text of the resume.
            jd_embedding: Precomputed normalized embedding of the JD.
            
        Returns:
            Dict mapping section name to its match score (0-100).
        """
        sections = self._split_sections(resume_text)
        if not sections:
            return {}

        results = {}
        # Parallelize embedding of sections
        section_names = list(sections.keys())
        section_texts = list(sections.values())
        
        embeddings = await asyncio.gather(
            *[self._embedder.embed(text[:2000]) for text in section_texts],
            return_exceptions=True
        )

        for name, embedding in zip(section_names, embeddings):
            if isinstance(embedding, Exception):
                results[name] = 0.0
                continue
            
            # Since embeddings are L2-normalized, dot product is cosine similarity
            similarity = np.dot(embedding, jd_embedding)
            results[name] = round(float(max(0.0, similarity) * 100), 1)

        return results

    def _split_sections(self, text: str) -> Dict[str, str]:
        """Heuristic splitting of text into sections based on headers."""
        lines = text.splitlines()
        sections = {}
        current_section = "general"
        current_content = []

        for line in lines:
            clean_line = line.strip()
            if not clean_line:
                continue
            
            # Check if line looks like a header
            match = self._section_pattern.search(clean_line)
            if match and len(clean_line) < 30: # Heuristic: headers are short
                # Save previous section
                if current_content:
                    sections[current_section] = "\n".join(current_content)
                
                # Normalize section name
                found = match.group(1).lower()
                if "experience" in found:
                    current_section = "experience"
                elif "skill" in found:
                    current_section = "skills"
                elif "education" in found or "academic" in found:
                    current_section = "education"
                elif "project" in found:
                    current_section = "projects"
                elif "summary" in found:
                    current_section = "summary"
                else:
                    current_section = found
                
                current_content = []
            else:
                current_content.append(line)

        if current_content:
            sections[current_section] = "\n".join(current_content)
            
        return sections
