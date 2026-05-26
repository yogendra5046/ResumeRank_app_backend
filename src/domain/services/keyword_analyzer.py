"""Domain service: Keyword density analyzer."""
from __future__ import annotations

import re
from typing import Dict

class KeywordAnalyzer:
    """Analyzes keyword density and gaps between resume and JD."""

    async def analyze(
        self, 
        resume_text: str, 
        jd_text: str, 
        skills: list[str]
    ) -> Dict[str, dict]:
        """Calculates density gap for each skill.
        
        Args:
            resume_text: Extracted text from resume.
            jd_text: Job description text.
            skills: List of skills to analyze.
            
        Returns:
            Dict mapping skill name to its stats.
        """
        analysis = {}
        for skill in skills:
            # Escape skill for regex and check for word boundaries
            pattern = re.compile(rf"\b{re.escape(skill)}\b", re.IGNORECASE)
            
            resume_count = len(pattern.findall(resume_text))
            jd_count = len(pattern.findall(jd_text))
            
            if jd_count > 0:
                density_gap = ((resume_count - jd_count) / jd_count) * 100
            else:
                density_gap = 100.0 if resume_count > 0 else 0.0
                
            analysis[skill] = {
                "resume_count": resume_count,
                "jd_count": jd_count,
                "density_gap": round(density_gap, 1)
            }
            
        return analysis
