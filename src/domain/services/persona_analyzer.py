from typing import Dict, List, Any

class PersonaAnalyzer:
    """Classifies professional persona based on linguistic patterns and clusters."""
    
    def __init__(self):
        self.personas = {
            "Leader/Strategist": {
                "keywords": {"led", "managed", "strategic", "vision", "roadmap", "orchestrated", "executive", "budget", "mentored", "pioneered", "transformation", "stakeholder", "kpi", "roi"},
                "description": "High-level strategic focus. Best suited for Management or Lead roles."
            },
            "Technical Specialist": {
                "keywords": {"implemented", "optimized", "code", "debugged", "engineered", "refactored", "unit testing", "stack", "deployment", "scripts", "integration", "rest api", "backend"},
                "description": "Deep execution focus. Best suited for Senior Engineering or Specialist roles."
            },
            "Architect/Visionary": {
                "keywords": {"designed", "architected", "scalability", "infrastructure", "system", "performance", "high-availability", "microservices", "patterns", "distributed", "security", "modeling"},
                "description": "System-wide architectural focus. Best suited for Architect or Staff Engineer roles."
            },
            "Collaborator/Support": {
                "keywords": {"collaborated", "assisted", "communicated", "team", "stakeholders", "support", "resolved", "feedback", "agile", "documentation", "mentorship", "partnership"},
                "description": "People and process focus. Best suited for Scrum Master, Support, or Team Lead roles."
            },
            "Data/Analytical": {
                "keywords": {"analyzed", "insights", "metrics", "pipeline", "dashboard", "modeling", "sql", "regression", "prediction", "data-driven", "visualization", "warehouse"},
                "description": "Heavy data focus. Best suited for Data Science or Analyst roles."
            }
        }

    def analyze(self, text: str) -> Dict[str, Any]:
        import re
        text_lower = text.lower()
        
        scores = {}
        for persona, data in self.personas.items():
            # Count unique keyword hits
            score = sum(2 for kw in data["keywords"] if re.search(r'\b' + re.escape(kw) + r'\b', text_lower))
            scores[persona] = score
            
        # Determine Primary Persona
        primary = max(scores, key=scores.get)
        if scores[primary] < 4:
            primary = "General Professional"
            
        return {
            "primary_persona": primary,
            "persona_breakdown": scores,
            "description": self.personas.get(primary, {}).get("description", "A balanced professional profile."),
            "top_traits": sorted([kw.capitalize() for kw in self.personas.get(primary, {}).get("keywords", []) if kw in text_lower], key=len, reverse=True)[:5]
        }

