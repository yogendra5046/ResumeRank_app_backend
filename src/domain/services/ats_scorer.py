import re
import fitz  # PyMuPDF
import spacy
import hashlib
import numpy as np

# Load spaCy model
try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    import spacy.cli
    spacy.cli.download("en_core_web_sm")
    nlp = spacy.load("en_core_web_sm")

class AtsScorer:
    def __init__(self):
        self.action_verbs = {
            "achieved", "spearheaded", "accelerated", "reduced", "increased", 
            "generated", "led", "built", "launched", "optimized", "orchestrated",
            "engineered", "streamlined", "pioneered", "implemented", "delivered",
            "automated", "managed", "coordinated", "designed", "developed"
        }
        self.power_words = {
            "promoted", "awarded", "recognized", "top performer", "exceeded",
            "distinction", "highest", "certified", "expert", "specialist"
        }
        self.synonym_map = {
            "react.js": ["reactjs", "react", "react native"],
            "node.js": ["nodejs", "node", "express.js", "express"],
            "aws": ["amazon web services", "ec2", "s3", "lambda"],
            "python": ["python3", "django", "flask", "fastapi"],
            "js": ["javascript", "es6"],
            "ts": ["typescript"],
            "vue.js": ["vue", "vuejs"],
            "sql": ["postgresql", "mysql", "sql server", "oracle"],
            "ml": ["machine learning", "deep learning", "artificial intelligence", "ai"],
            "docker": ["containerization", "kubernetes", "k8s"]
        }

    def score_impact(self, resume_text: str) -> dict:
        text_lower = resume_text.lower()
        
        # 1. Action Verbs (Award 6 pts per unique verb, up to 30 -> 5 verbs)
        found_verbs = set()
        for verb in self.action_verbs:
            if re.search(r'\b' + re.escape(verb) + r'\b', text_lower):
                found_verbs.add(verb)
        verb_score = min(len(found_verbs) * 6.0, 30.0)

        # 2. Quantified Results (Award 15 pts per unique metric, up to 45 -> 3 metrics)
        metric_pattern = r'\d+%\s*|\b\d+\s*(?:users|clients|revenue|cost|time|million|thousand|crore|lakh)\b|(?:\$|₹|Rs\.?)\s*\d+[KM]?'
        metrics = list(set(re.findall(metric_pattern, text_lower, flags=re.IGNORECASE)))
        metric_score = min(len(metrics) * 15.0, 45.0)

        # 3. Power Words (Award 5 pts per unique power word, up to 25 -> 5 words)
        found_power = set()
        for word in self.power_words:
            if re.search(r'\b' + re.escape(word) + r'\b', text_lower):
                found_power.add(word)
        power_score = min(len(found_power) * 5.0, 25.0)

        total_score = verb_score + metric_score + power_score
        
        # MARKET STANDARD: A good resume should have at least 5 verbs and 2 metrics
        # to cross 50. A great one has 10+ verbs and 5+ metrics to hit 80-100.
            
        return {
            "score": round(min(total_score, 100.0)),
            "details": [
                f"Action verbs: {len(found_verbs)}/15 recommended",
                f"Metrics detected: {len(metrics)} (Quantifiable impact is critical)",
                f"Power words: {len(found_power)}"
            ],
            "raw_metrics": {"verbs": list(found_verbs), "metrics_count": len(metrics), "power_words": list(found_power)}
        }

    def score_format(self, doc: fitz.Document) -> dict:
        score = 100
        details = []

        # 1. Pages (1-2 is ideal, 3 is acceptable, 4+ is bad)
        num_pages = len(doc)
        if num_pages > 3:
            score -= 20
            details.append(f"Resume is too long ({num_pages} pages). Aim for 1-2.")
        elif num_pages == 3:
            score -= 5
            
        # 2. Tables (ATS Nightmare)
        has_table = False
        for page in doc:
            tables = page.find_tables()
            if tables and len(tables.tables) > 0:
                has_table = True
                break
        if has_table:
            score -= 25
            details.append("Tables detected. Some ATS systems cannot parse text inside tables.")

        # 3. Text Density check
        total_text = "".join([p.get_text() for p in doc])
        if len(total_text) < 500:
            score -= 15
            details.append("Very low text density detected.")

        multi_col_pages = 0
        for page in doc:
            blocks = page.get_text("blocks")
            if len(blocks) > 5:
                mid_x = page.rect.width / 2
                left_blocks = [b for b in blocks if b[0] < mid_x and b[2] < mid_x + 50]
                right_blocks = [b for b in blocks if b[0] > mid_x - 50]
                if len(left_blocks) > 3 and len(right_blocks) > 3:
                    multi_col_pages += 1

        if multi_col_pages > 0:
            score -= 15
            details.append("Multi-column layout detected. Single-column is safer for ATS readability.")

        # 4. Images/Graphics
        total_images = 0
        for page in doc:
            total_images += len(page.get_images(full=True))
        if total_images > 2:
            score -= 10
            details.append("Excessive graphics/images detected. Keep it text-focused.")

        # 5. Font Size
        small_font = False
        for page in doc:
            blocks = page.get_text("dict").get("blocks", [])
            for b in blocks:
                if "lines" in b:
                    for l in b["lines"]:
                        for s in l.get("spans", []):
                            if s.get("size", 10) < 8.5:
                                small_font = True
                                break
        if small_font:
            score -= 10
            details.append("Font size below 9pt detected. May be hard to read.")

        return {
            "score": max(0, score),
            "details": details if details else ["Excellent formatting (ATS-Friendly)"]
        }

    def score_text_format(self, text: str) -> dict:
        """Text-based format analysis for non-PDF inputs."""
        score = 90  
        details = ["Analyzing text structure (Visual layout skipped for raw text input)."]
        
        # 1. Length check
        word_count = len(text.split())
        if word_count < 200:
            score -= 20
            details.append("Resume is very short. Aim for 400-800 words.")
        elif word_count > 1500:
            score -= 10
            details.append("Resume is quite long. Consider more concise bullet points.")
            
        # 2. Section Balance
        sections = ["experience", "education", "skills", "projects", "summary"]
        found = [s for s in sections if s in text.lower()]
        if len(found) < 3:
            score -= 15
            details.append(f"Missing key sections. Found only: {', '.join(found) if found else 'none'}.")
            
        return {"score": max(0, score), "details": details}

    def _extract_hard_skills(self, text: str) -> list[str]:
        # Market standard blacklist for resume/JD text
        blacklist = {
            "experience", "years", "requirements", "engineer", "software", "developer",
            "impact", "metrics", "strong", "results", "excellent", "skills", "ability",
            "team", "work", "proven", "track", "record", "professional", "management",
            "knowledge", "understanding", "degree", "qualification", "candidate",
            "company", "business", "responsibilities", "use", "activities", "duties",
            "assigned", "provide", "support", "environment", "field", "area", "related"
        }
        
        doc = nlp(text.lower())
        skills = []
        # Filter for nouns and proper nouns that aren't too common
        for token in doc:
            # Filter for nouns and proper nouns that aren't too common
            # and ignore purely numeric or hyphenated number strings like '0-1'
            t_text = token.text
            if token.pos_ in ["NOUN", "PROPN"] and not token.is_stop and len(t_text) > 2:
                if t_text not in blacklist and not re.match(r'^\d+-\d+$', t_text):
                    skills.append(t_text)
                
        # Also include common skill chunks (Big Data, Machine Learning, etc.)
        for chunk in doc.noun_chunks:
            clean_chunk = " ".join([t.text for t in chunk if not t.is_stop and not t.is_punct])
            if clean_chunk and len(clean_chunk) > 2 and clean_chunk not in blacklist:
                # Check if any part of the chunk is in blacklist (e.g. "strong impact")
                if not any(word in blacklist for word in clean_chunk.split()):
                    skills.append(clean_chunk)
            
        skill_counts = {}
        for s in skills:
            skill_counts[s] = skill_counts.get(s, 0) + 1
            
        return sorted(skill_counts.keys(), key=lambda k: skill_counts[k], reverse=True)[:20]

    def score_keyword(self, resume_text: str, jd_text: str, embedder=None) -> dict:
        jd_skills = self._extract_hard_skills(jd_text)
        if not jd_skills:
            return {"score": 100, "details": ["Job description is too short to extract skills."]}

        resume_lower = resume_text.lower()
        matched_count = 0
        total_points = 0
        max_points = len(jd_skills) * 10
        
        # Pre-extract noun chunks from resume for semantic matching
        resume_doc = nlp(resume_lower)
        resume_chunks = [chunk.text for chunk in resume_doc.noun_chunks if len(chunk.text) > 2]
        
        details = []
        for skill in jd_skills:
            skill_pts = 0
            base_skill = skill.rstrip('s') if len(skill) > 3 and skill.endswith('s') else skill
            flexible_pattern = re.compile(rf"\b{re.escape(base_skill)}s?\b", re.IGNORECASE)

            # 1. Exact or Flexible Match (10 pts)
            if flexible_pattern.search(resume_lower):
                skill_pts = 10
                matched_count += 1
            else:
                # 2. Synonym/Alias Match (7 pts)
                synonyms = self.synonym_map.get(skill, [])
                syn_found = False
                for syn in synonyms:
                    if re.search(r'\b' + re.escape(syn) + r'\b', resume_lower):
                        skill_pts = 7
                        matched_count += 1
                        syn_found = True
                        break
                
                if not syn_found:
                    # 3. Hybrid Semantic Match (6 pts)
                    # This bridges gaps like "AWS" matching "Amazon Cloud"
                    # We check if any noun chunk in the resume is semantically similar to the JD skill
                    for chunk in resume_chunks:
                        chunk_lower = chunk.lower()
                        # a) Local fast-path: Word Overlap (if 50% of words in multi-word skill match chunk)
                        skill_words = set(skill.split())
                        chunk_words = set(chunk_lower.split())
                        if len(skill_words) > 1 and len(skill_words & chunk_words) / len(skill_words) >= 0.5:
                            skill_pts = 6
                            matched_count += 1
                            break
                        
                        # b) Substring of chunk (e.g. "React" in "React Native Architecture")
                        if len(skill) > 3 and skill in chunk_lower:
                            skill_pts = 6
                            matched_count += 1
                            break
                    
                    # c) Real Semantic Match (if embedder provided - handled in higher-level pipeline)
                    # Note: Higher-level pipeline in analyze_resume_full already handles 
                    # advanced semantic matches using the 'semantic_skill_matches' list.

                # 4. Partial/Sub-word Match (4 pts)
                if skill_pts == 0 and " " in skill:
                    for part in skill.split():
                        if len(part) > 3 and re.search(r'\b' + re.escape(part) + r'\b', resume_lower):
                            skill_pts = 4
                            matched_count += 1
                            break
            
            total_points += skill_pts

        raw_score = (total_points / max_points) * 100 if max_points > 0 else 0
        
        # Market Standard: Differentiate between "Found nothing" and "Found something"
        if raw_score > 0:
            # Shift the curve to make it more discriminatory
            # 50% match should yield ~60 score, 80% match should yield ~90 score
            raw_score = (raw_score ** 0.8) * (100 / (100 ** 0.8))

        return {
            "score": round(min(raw_score, 100.0)),
            "details": [f"Matched {matched_count} of {len(jd_skills)} identified skills (Hybrid Semantic)."]
        }

    def score_ats_parse(self, doc: fitz.Document, resume_text: str) -> dict:
        score = 0
        details = []
        
        text_len = len(resume_text.strip())
        if text_len == 0:
            return {"score": 0, "details": ["Text extractable < 100 chars (0)"]}
            
        # Check special characters
        special_chars = [c for c in resume_text if ord(c) > 127 or c in "•→▪◦☑☐"]
        has_special_penalty = False
        if len(resume_text) > 0 and (len(special_chars) / len(resume_text)) > 0.05:
            has_special_penalty = True
            details.append("Excessive special characters/bullet symbols detected (-30).")

        if text_len < 200:
            score_val = 5
            if has_special_penalty:
                score_val = max(0, score_val - 30)
            return {"score": score_val, "details": ["Document contains very little extractable text (potential image-only PDF)."] + details}
        
        score += 20
        
        # 2. Standard Sections
        sections = {
            "experience": r'(?i)\b(?:experience|employment|work history|career)\b',
            "education": r'(?i)\b(?:education|academic|studies)\b',
            "skills": r'(?i)\b(?:skills|technologies|competencies|expertise)\b',
            "projects": r'(?i)\b(?:projects|portfolio|achievements)\b'
        }
        
        found_sections = 0
        for name, pattern in sections.items():
            if re.search(pattern, resume_text):
                found_sections += 1
                score += 15
        
        if found_sections < 2:
            details.append("Critical sections (Experience/Education) missing or poorly labeled.")

        # 3. Contact Details
        if re.search(r'[\w\.-]+@[\w\.-]+', resume_text): score += 10
        if re.search(r'\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b', resume_text): score += 10

        if has_special_penalty:
            score -= 30

        return {
            "score": max(0, min(score, 100)),
            "details": details if details else ["Standard ATS headers detected."]
        }

    def evaluate(self, pdf_bytes: bytes, jd_text: str) -> dict:
        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            resume_text = ""
            for page in doc:
                resume_text += page.get_text()
                
            impact_res = self.score_impact(resume_text)
            format_res = self.score_format(doc)
            keyword_res = self.score_keyword(resume_text, jd_text)
            ats_res = self.score_ats_parse(doc, resume_text)
            
            # MARKET STANDARD WEIGHTS:
            # Keyword/Skill Match is most important (40%)
            # Impact/Content Quality (30%)
            # ATS Parsability (20%)
            # Formatting (10%)
            overall = (keyword_res["score"] * 0.40) + \
                      (impact_res["score"] * 0.30) + \
                      (ats_res["score"] * 0.20) + \
                      (format_res["score"] * 0.10)
                      
            return {
                "overall": round(overall),
                "impact": impact_res,
                "format": format_res,
                "keyword": keyword_res,
                "ats": ats_res,
                "raw_resume_text": resume_text,
                "raw_jd_text": jd_text
            }
        except Exception as e:
            raise ValueError(f"Failed to parse or score PDF: {str(e)}")


    def get_audit_report(self, resume_text: str, jd_text: str) -> dict:
        """
        Deterministic, rule-based audit. No API keys required.
        """
        text_lower = resume_text.lower()
        jd_skills = self._extract_hard_skills(jd_text)
        
        # 1. Keyword Density Audit
        density = {}
        for skill in jd_skills:
            count = len(re.findall(r'\b' + re.escape(skill) + r'\b', text_lower))
            density[skill] = {
                "count": count,
                "status": "Optimal" if count >= 2 else "Missing" if count == 0 else "Low"
            }
            
        # 2. Section Integrity
        sections = ["experience", "education", "skills", "projects", "contact", "summary"]
        found_sections = []
        missing_sections = []
        for s in sections:
            if s in text_lower:
                found_sections.append(s.capitalize())
            else:
                missing_sections.append(s.capitalize())
                
        # 3. Action Verb Audit
        lines = [l.strip() for l in resume_text.split('\n') if len(l.strip()) > 10]
        weak_lines = []
        for line in lines:
            line_lower = line.lower()
            if not any(v in line_lower for v in self.action_verbs):
                weak_lines.append(line[:60] + "...")
                
        # 4. Format Warnings (Basic)
        warnings = []
        if len(resume_text) < 500:
            warnings.append("Resume text is very short. Ensure it's not a scanned image.")
        if "@" not in resume_text:
            warnings.append("Missing email address.")
            
        return {
            "keyword_density": density,
            "section_audit": {
                "found": found_sections,
                "missing": missing_sections
            },
            "verb_audit": {
                "weak_bullet_points": weak_lines[:5],
                "score": max(0, 100 - (len(weak_lines) * 10))
            },
            "format_warnings": warnings
        }

ats_scorer = AtsScorer()
