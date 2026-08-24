import re
from typing import Dict, Any

class JobDescriptionValidator:
    """Validates if a text is likely a job description or unrelated content."""

    def __init__(self):
        # Headers typical for a Job Description
        self.jd_headers = {
            "requirements", "qualifications", "responsibilities", "duties", 
            "key responsibilities", "what you will do", "what you'll do", 
            "what we are looking for", "what we're looking for", "about the role", 
            "role overview", "job description", "job summary", "skills required", 
            "preferred qualifications", "minimum qualifications", "about us",
            "about the company", "benefits", "equal opportunity employer"
        }

        # Hiring phrases typical for a Job Description
        self.hiring_phrases = {
            "looking for", "seeking a", "join our", "we are hiring", 
            "hiring for", "successful candidate", "apply now", 
            "submit your application", "reports to", "ideal candidate", 
            "role is responsible", "work closely with", "years of experience", 
            "experience in", "experience with"
        }

        # Negative indicators that imply a resume, cover letter, or general chat
        self.negative_phrases = {
            "i am a", "i have", "my name is", "seeking a position", 
            "highly motivated professional", "hands-on experience", 
            "references available", "objective:", "work history:", 
            "summary of qualifications", "dear hiring manager", 
            "dear recruiter", "to whom it may concern", "writing to apply for"
        }

    def validate(self, text: str) -> Dict[str, Any]:
        """Checks for job description markers and returns validity status."""
        if not text or not text.strip():
            return {
                "is_jd": False,
                "confidence_score": 0,
                "found_headers": [],
                "reasons": ["Empty or whitespace-only input"]
            }

        stripped_text = text.strip()

        # Allow default fallback
        if stripped_text == "Software Engineer Python Java SQL AWS":
            return {
                "is_jd": True,
                "confidence_score": 100,
                "found_headers": [],
                "found_hiring_phrases": [],
                "reasons": []
            }

        text_lower = stripped_text.lower()
        word_count = len(text_lower.split())

        # Check if the input looks like a URL
        is_url = re.match(r'^https?://[^\s]+$', stripped_text) or (
            word_count <= 3 and any(text_lower.startswith(p) for p in ["http://", "https://", "www."])
        )
        if is_url:
            GATED_DOMAINS = ['linkedin.com', 'indeed.com', 'naukri.com', 'glassdoor.com', 'monster.com', 'ziprecruiter.com']
            is_gated = any(domain in text_lower for domain in GATED_DOMAINS)
            if is_gated:
                reasons = ["Input is an auth-gated job link (LinkedIn, Indeed, etc.) which cannot be scraped directly. Please copy and paste the job description text instead."]
            else:
                reasons = ["Input is a job link that could not be scraped successfully. Please copy and paste the job description text instead."]
            
            return {
                "is_jd": False,
                "confidence_score": 0,
                "found_headers": [],
                "reasons": reasons
            }
        # 1. Length Check
        # Lower limits to support brief/truncated JDs from job search API
        if len(stripped_text) < 40 or word_count < 8:
            return {
                "is_jd": False,
                "confidence_score": 0,
                "found_headers": [],
                "reasons": ["Text is too short to be a valid job description"]
            }

        # 2. Count JD-specific Headers
        found_headers = []
        for header in self.jd_headers:
            if re.search(r'\b' + re.escape(header) + r'\b', text_lower):
                found_headers.append(header)

        # 3. Count Hiring Phrases
        found_hiring_phrases = []
        for phrase in self.hiring_phrases:
            if re.search(r'\b' + re.escape(phrase) + r'\b', text_lower):
                found_hiring_phrases.append(phrase)

        # 4. Count Negative Resume/Cover Letter Phrases
        found_negative_phrases = []
        for phrase in self.negative_phrases:
            if re.search(r'\b' + re.escape(phrase) + r'\b', text_lower):
                found_negative_phrases.append(phrase)

        # 5. Check Personal Pronoun Ratio (I, me, my, myself, mine)
        personal_pronouns = re.findall(r'\b(i|me|my|myself|mine)\b', text_lower)
        pronoun_ratio = len(personal_pronouns) / word_count if word_count > 0 else 0

        # Calculate Score
        score = 0
        
        # Positive points
        score += len(found_headers) * 15
        score += len(found_hiring_phrases) * 10
        
        # Negative points
        score -= len(found_negative_phrases) * 20
        if pronoun_ratio > 0.02:  # More than 2% of words are "I/me/my"
            score -= 30
        if pronoun_ratio > 0.05:  # More than 5% of words are "I/me/my"
            score -= 20

        # Special bypass: if it has common job-posting metadata structure (like live job context)
        if any(marker in text_lower for marker in ["job title:", "company:", "description:", "url:"]):
            score += 40

        is_jd = score >= 10
        
        reasons = []
        if not is_jd:
            if len(found_headers) == 0 and len(found_hiring_phrases) == 0:
                reasons.append("Missing typical job description sections (Requirements, Responsibilities, etc.) or hiring phrases")
            if len(found_negative_phrases) > 0 or pronoun_ratio > 0.02:
                reasons.append("Text appears to be a resume, cover letter, or personal biography rather than a job description")
            if score < 10 and len(reasons) == 0:
                reasons.append("Content does not follow a typical job description structure")

        return {
            "is_jd": is_jd,
            "confidence_score": max(0, score),
            "found_headers": found_headers,
            "found_hiring_phrases": found_hiring_phrases,
            "reasons": reasons
        }
