import re
from typing import Dict, Any

class ResumeValidator:
    """Validates if a document is likely a resume or unrelated content."""
    
    def __init__(self):
        self.resume_headers = {
            "experience", "education", "skills", "projects", "summary", 
            "objective", "work history", "academic", "technical skills",
            "professional experience", "certifications", "interests"
        }
        self.email_pattern = re.compile(r'[\w\.-]+@[\w\.-]+')
        self.phone_pattern = re.compile(r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}')

    def validate(self, text: str) -> Dict[str, Any]:
        """Checks for resume markers and returns validity status."""
        text_lower = text.lower()
        
        # 1. Count Headers
        found_headers = []
        for header in self.resume_headers:
            if re.search(r'\b' + re.escape(header) + r'\b', text_lower):
                found_headers.append(header)
        
        # 2. Check Contact Info
        has_email = bool(self.email_pattern.search(text_lower))
        has_phone = bool(self.phone_pattern.search(text_lower))
        
        # 3. Specific Resume Keywords
        is_cv_labeled = any(kw in text_lower for kw in ["curriculum vitae", "resume", "cv"])
        
        # 4. Final Decision Logic
        # A valid resume usually has:
        # - At least 2 major headers (e.g. Experience + Education)
        # - OR a specific label (CV/Resume) + 1 header + contact info
        
        score = 0
        if len(found_headers) >= 3: score += 60
        elif len(found_headers) >= 1: score += 30
        
        if has_email: score += 20
        if has_phone: score += 10
        if is_cv_labeled: score += 20
        
        is_resume = score >= 50
        
        reasons = []
        if not is_resume:
            if len(found_headers) < 2: reasons.append("Missing standard resume sections (Experience, Education, etc.)")
            if not has_email: reasons.append("Contact information (email) not detected")
            if score < 30: reasons.append("Content does not follow a typical resume structure")

        return {
            "is_resume": is_resume,
            "confidence_score": score,
            "found_headers": found_headers,
            "has_contact_info": has_email or has_phone,
            "reasons": reasons
        }
