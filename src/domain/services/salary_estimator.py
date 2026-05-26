import re
from typing import Dict, List, Any

class SalaryEstimator:
    """Estimates market value in INR (LPA) based on skills, experience and role."""
    
    def __init__(self):
        # Base salaries in INR (LPA - Lakhs Per Annum) for a entry-level role (0-2 years)
        # Based on 2024-2025 market trends
        self.base_lpa = {
            "software": 6.5,
            "data": 7.5,
            "design": 5.5,
            "product": 10.0,
            "marketing": 4.5,
            "cloud": 8.0,
            "devops": 7.5,
            "cybersecurity": 8.5,
            "general": 4.0
        }
        
        # Skill Bonuses in LPA (Add-ons for specialized skills)
        self.skill_bonuses = {
            # AI / ML (High Premium)
            "machine learning": 5.0, "nlp": 4.5, "generative ai": 6.0, "pytorch": 3.5, "tensorflow": 3.0, "llm": 5.5,
            # Backend / Languages
            "rust": 4.5, "golang": 3.5, "python": 1.5, "java": 1.2, "distributed systems": 4.0, "system design": 3.0,
            # Infrastructure / DevOps
            "kubernetes": 3.0, "terraform": 2.5, "aws": 1.8, "azure": 1.5, "gcp": 1.5, "docker": 1.0,
            # Frontend / Mobile
            "react": 1.2, "flutter": 1.5, "swift": 2.0, "kotlin": 1.8,
            # Emerging
            "solidity": 5.5, "blockchain": 4.0
        }
        
        # Role Multipliers (Career progression scaling)
        self.role_multipliers = {
            "senior": 1.8, "lead": 2.2, "architect": 2.8, "principal": 3.5,
            "manager": 2.0, "vp": 4.5, "director": 4.0, "head": 3.8,
            "junior": 0.8, "entry": 0.7, "intern": 0.4, "fresher": 0.6,
            "consultant": 1.5, "specialist": 1.4
        }

        # Location Multipliers
        self.location_multipliers = {
            "bangalore": 1.25, "bengaluru": 1.25,
            "hyderabad": 1.15,
            "mumbai": 1.20,
            "pune": 1.10,
            "gurgaon": 1.18, "ncr": 1.15, "delhi": 1.10,
            "chennai": 1.05,
            "remote": 1.10
        }

        # Tier 1 Institution Boost (IIT, NIT, BITS, etc.)
        self.tier1_keywords = ["iit", "nit", "bits", "iiit", "iim", "isb", "stanford", "mit", "harvard"]
        
        # High-Value Company Boost (MAANG, Top Product Firms)
        self.top_firm_keywords = ["google", "amazon", "microsoft", "meta", "netflix", "apple", "uber", "goldman", "atlassian", "salesforce"]

    def estimate(self, text: str, matched_skills: List[str]) -> Dict[str, Any]:
        text_lower = text.lower()
        
        # 1. Detect Category
        category = "general"
        if any(kw in text_lower for kw in ["software", "developer", "engineer", "fullstack", "backend"]):
            category = "software"
        elif any(kw in text_lower for kw in ["data", "ml", "ai", "scientist", "analyst", "vision", "learning"]):
            category = "data"
        elif any(kw in text_lower for kw in ["product manager", "pm", "product owner", "scrum"]):
            category = "product"
        elif any(kw in text_lower for kw in ["ux", "ui", "designer", "graphic", "figma"]):
            category = "design"
        elif any(kw in text_lower for kw in ["devops", "sre", "infrastructure", "terraform", "kubernetes"]):
            category = "devops"
        elif any(kw in text_lower for kw in ["cloud", "aws", "azure", "gcp"]):
            category = "cloud"
        elif any(kw in text_lower for kw in ["cyber", "security", "infosec", "penetration"]):
            category = "cybersecurity"
            
        base = self.base_lpa.get(category, 4.0)
        
        # 2. Skill Bonuses (Capped at 70% of base)
        skill_bonus = sum(self.skill_bonuses.get(s.lower(), 0) for s in matched_skills)
        skill_bonus = min(skill_bonus, base * 0.7)
        
        # 3. Detect Experience (FIX: Use word boundaries and limit digits to prevent matching years)
        # Matches "X+ years", "X years", "X yrs" but NOT "2024 years"
        # We look for 1 or 2 digits followed by experience keywords
        exp_matches = re.findall(r'\b(\d{1,2})\b[\+]?\s*(?:year|yr|exp)', text_lower)
        years = max([int(n) for n in exp_matches]) if exp_matches else 0
        
        # Hard cap at 40 years to prevent unrealistic data
        years = min(years, 40)
        
        # Experience multiplier: 
        # 0-2y: ~0.8-1.2x
        # 3-6y: ~1.5-2.5x
        # 7-10y: ~2.5-4.0x
        # 10y+: ~4.0x + 0.15 per year
        if years <= 2:
            exp_mult = 0.8 + (years * 0.2)
        elif years <= 6:
            exp_mult = 1.2 + ((years - 2) * 0.35)
        elif years <= 10:
            exp_mult = 2.6 + ((years - 6) * 0.45)
        else:
            exp_mult = 4.4 + ((years - 10) * 0.2)
            
        # 4. Role Seniority
        seniority_mult = 1.0
        detected_role = "Mid Level"
        for role, mult in self.role_multipliers.items():
            if re.search(r'\b' + re.escape(role) + r'\b', text_lower):
                if mult > seniority_mult:
                    seniority_mult = mult
                    detected_role = role.capitalize()

        # 5. Location Boost
        location_mult = 1.0
        for loc, mult in self.location_multipliers.items():
            if re.search(r'\b' + re.escape(loc) + r'\b', text_lower):
                location_mult = max(location_mult, mult)

        # 6. Institution & Company Tier Boost
        tier_boost = 1.0
        if any(re.search(r'\b' + re.escape(k) + r'\b', text_lower) for k in self.tier1_keywords):
            tier_boost += 0.25 # 25% boost for Tier 1
        if any(re.search(r'\b' + re.escape(k) + r'\b', text_lower) for k in self.top_firm_keywords):
            tier_boost += 0.20 # 20% boost for Top Firms

        # Final Calculation
        # Formula: (Base + SkillBonus) * ExpMult * Seniority * Location * Tier
        lpa_total = (base + skill_bonus) * exp_mult * seniority_mult * location_mult * tier_boost
        
        # Realistic Ceiling for India (Capping at 250 LPA for now, which is extremely high but possible for CXO/MAANG)
        lpa_total = min(lpa_total, 250.0)
            
        return {
            "category": category.capitalize(),
            "estimated_range": f"₹{round(lpa_total * 0.85, 1)} - {round(lpa_total * 1.15, 1)} LPA",
            "raw_lpa": round(lpa_total, 2),
            "currency": "INR",
            "experience_detected": f"{years}+ Years",
            "seniority": detected_role,
            "top_valuable_skills": sorted([s for s in matched_skills if s.lower() in self.skill_bonuses], 
                                         key=lambda s: self.skill_bonuses.get(s.lower(), 0), reverse=True)[:3]
        }

