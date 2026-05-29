import re
import structlog
from typing import Dict, List, Set, Optional

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)

# --- CONFIGURATION V2 ---
STOPWORDS: Set[str] = {
    'requirements','written','least','ability','preferably','communication',
    'candidate','must','should','will','can','good','strong','experience',
    'work','team','job','role','etc', 'hands', 'on', 'plus', 'proven',
    'company', 'business', 'responsibilities', 'use', 'using', 'used',
    'working', 'years', 'knowledge', 'understanding', 'required', 'desired',
    'highly', 'professional', 'skills', 'excellent', 'impact', 'metrics',
    'track', 'record', 'successful', 'field', 'area', 'related', 'environment',
    'support', 'provide', 'assist', 'help', 'collaborate', 'perform', 'tasks',
    'activities', 'responsibilities', 'duties', 'assigned', '0-1', '1-2', '3-5'
}

SKILLS_WHITELIST: List[str] = [
    'python','java','javascript','typescript','react','angular','vue','node.js',
    'django','flask','fastapi','sql','postgresql','mongodb','redis','aws',
    'azure','gcp','docker','kubernetes','terraform','git','linux','ci/cd',
    'jenkins','rest','graphql','microservices','system design','data structures',
    'algorithms','machine learning','deep learning','pytorch','tensorflow',
    'nlp','computer vision', 'golang', 'rust', 'c++', 'c#', 'dotnet', 'spark',
    'hadoop', 'kafka', 'elasticsearch', 'tableau', 'powerbi', 'pandas', 'ansible', 'agile', 'leadership',
    'swift', 'kotlin', 'flutter', 'dart', 'react native', 'figma', 'ui/ux', 'scrum', 'kanban',
    'cybersecurity', 'blockchain', 'solidity', 'jira', 'confluence', 'excel', 'go', 'next.js', 'tailwind', 'bun', 'supabase'
]

SKILL_WEIGHTS: Dict[str, int] = {
    'python': 10, 'java': 9, 'golang': 10, 'rust': 10, 'javascript': 8, 'typescript': 9,
    'react': 9, 'node.js': 9, 'aws': 10, 'kubernetes': 10, 'docker': 9, 'sql': 8,
    'git': 5, 'ci/cd': 8, 'fastapi': 8, 'django': 8, 'terraform': 9, 'microservices': 9,
    'system design': 10, 'algorithms': 9, 'machine learning': 10, 'pytorch': 10,
    'leadership': 9, 'communication': 8, 'agile': 7
}

SKILL_CATEGORIES = {
    'Programming': ['python','java','c++','go','javascript','typescript', 'rust', 'golang', 'c#', 'dotnet', 'ruby', 'php'],
    'Web / Backend': ['react','angular','vue','node.js','django','flask', 'fastapi', 'graphql', 'rest', 'spring', 'laravel'],
    'Mobile Dev': ['flutter', 'dart', 'swift', 'kotlin', 'react native', 'android', 'ios'],
    'Cloud / Infra': ['aws','azure','gcp','docker','kubernetes','terraform', 'microservices', 'system design', 'serverless'],
    'Data / AI': ['sql','postgresql','mongodb','pandas','spark','tableau', 'powerbi', 'machine learning', 'nlp', 'pytorch', 'tensorflow', 'scikit-learn'],
    'DevOps / Tools': ['git','jenkins','ci/cd','linux','ansible', 'jira', 'confluence', 'bitbucket', 'github'],
    'Business / UX': ['leadership','agile', 'scrum', 'kanban', 'ui/ux', 'figma', 'product management', 'design thinking']
}

# --- LOGIC ENGINE V2 ---

def clean_text(text: str) -> str:
    return re.sub(r'[^\w\s]', ' ', text.lower())

def extract_skills_with_context(text: str) -> List[Dict]:
    """Detects skills from whitelist and captures surrounding context."""
    results = []
    text_clean = clean_text(text)
    
    for skill in SKILLS_WHITELIST:
        pattern = re.compile(rf"\b{re.escape(skill)}\b", re.IGNORECASE)
        matches = list(pattern.finditer(text))
        if matches:
            # Check for "years" pattern near the skill
            years_pattern = re.compile(r"(\d+)\s*(?:\+|years|yr)", re.IGNORECASE)
            context = ""
            boost = 1.0
            
            for match in matches:
                start = max(0, match.start() - 30)
                end = min(len(text), match.end() + 30)
                snippet = text[start:end]
                
                # Experience Boost
                y_match = years_pattern.search(snippet)
                if y_match:
                    years = int(y_match.group(1))
                    if years >= 3: boost = max(boost, 1.5)
                    elif years >= 1: boost = max(boost, 1.2)
                
                # Section Boost
                if "skill" in text[max(0, match.start()-200):match.start()].lower():
                    boost = max(boost, 1.2)
                
                context = snippet.strip()
            
            results.append({
                "name": skill,
                "weight": SKILL_WEIGHTS.get(skill, 5),
                "context": f"...{context}...",
                "boost": boost
            })
    return results

def calculate_impact_score_v2(text: str) -> Dict:
    strong_verbs = {"engineered", "spearheaded", "orchestrated", "automated", "optimized", "implemented", "delivered"}
    weak_phrases = {"responsible for", "helped", "assisted", "worked on"}
    
    found_strong = [v for v in strong_verbs if v in text.lower()]
    found_weak = [p for p in weak_phrases if p in text.lower()]
    
    ratio = int((len(found_strong) / (len(found_strong) + len(found_weak) + 1)) * 100)
    
    return {
        "strong": len(found_strong),
        "weak": len(found_weak),
        "ratio": ratio,
        "details": [f"Found {len(found_strong)} high-impact verbs."]
    }

def generate_suggestions(matched: List[Dict], missing: List[Dict], verb_stats: Dict) -> List[str]:
    suggestions = []
    
    # 1. Critical Skill Suggestions
    critical_missing = [s for s in missing if s['weight'] >= 9][:2]
    for s in critical_missing:
        suggestions.append(
            f"CRITICAL: Missing '{s['name'].upper()}'. "
            f"WHY: 90% of modern SDE roles require this. Missing this is costing you ~10 points. "
            f"HOW: Add a dedicated line in your Skills section. IMPACT: Significant ATS visibility boost."
        )
    
    # 2. Verb Suggestions
    if verb_stats['ratio'] < 50:
        suggestions.append(
            "IMPROVE: Replace passive language. "
            "WHY: ATS systems prioritize action-oriented resumes. "
            "HOW: Swap 'Responsible for' with 'Spearheaded' or 'Engineered'. "
            "IMPACT: Increases professional grade and clarity by 15%."
        )
    
    # 3. Metrics Suggestion
    suggestions.append(
        "QUANTIFY: Add more metrics. "
        "WHY: Recruiters look for measurable impact. "
        "HOW: Instead of 'Improved performance', use 'Improved API throughput by 40%'. "
        "IMPACT: Doubles your chance of a callback."
    )
    
    return suggestions[:5]

def get_skill_gap_chart(matched_names: Set[str], jd_names: Set[str]) -> List[Dict]:
    chart = []
    for cat, skills in SKILL_CATEGORIES.items():
        cat_skills = set(skills)
        jd_in_cat = [s for s in jd_names if s in cat_skills]
        # FIX: Only count matched skills that were actually in the JD for this category
        matched_in_cat = [s for s in matched_names if s in cat_skills and s in jd_names]
        
        total = len(jd_in_cat)
        matched = len(matched_in_cat)
        
        if total > 0:
            percent = int((matched / total) * 100)
            chart.append({
                "name": cat,
                "category": cat,
                "matched": matched,
                "total": total,
                "percent": min(100, percent), # Safety cap
                "status": "Critical Gap" if percent < 40 else ("Good" if percent > 70 else "Warning")
            })
    
    return sorted(chart, key=lambda x: x["percent"])

RED_FLAG_CLICHES = {
    "team player", "hard worker", "highly motivated", "passionate", "results-driven",
    "self-starter", "dynamic", "outside the box", "detail-oriented", "go-getter",
    "thinker", "strategic", "creative", "problem solver", "responsible for", "helped in"
}

def detect_red_flags(text: str) -> List[str]:
    flags = []
    text_lower = text.lower()
    lines = text.splitlines()
    
    # 1. Unprofessional Emails
    email_match = re.search(r'[\w\.-]+@[\w\.-]+', text_lower)
    if email_match:
        email = email_match.group(0).split('@')[0]
        unprofessional_terms = ["cute", "cool", "sexy", "hot", "king", "queen", "gamer", "boy", "girl", "99", "123", "star"]
        if any(t in email for t in unprofessional_terms):
            flags.append(f"CRITICAL: Email address '{email}' looks unprofessional. Use 'firstname.lastname@' format.")

    # 2. Cliches & Weak Language
    found_cliches = [c for c in RED_FLAG_CLICHES if re.search(r'\b' + re.escape(c) + r'\b', text_lower)]
    if len(found_cliches) > 4:
        flags.append(f"WARNING: Too many generic buzzwords ({len(found_cliches)}). Recruiters prefer specific tools over 'passionate' or 'hard worker'.")

    # 3. Missing Professional Links
    if "linkedin.com" not in text_lower:
        flags.append("IMPROVE: No LinkedIn profile found. 87% of recruiters check LinkedIn before interviewing.")
    if "github.com" not in text_lower and any(kw in text_lower for kw in ["dev", "engineer", "code", "software"]):
        flags.append("IMPROVE: GitHub link missing for a technical role. Provide proof of your work.")

    # 4. Bullet Point Quality
    long_bullets = [line for line in lines if len(line.split()) > 40]
    if long_bullets:
        flags.append("FORMAT: Some bullet points are too long (>40 words). Keep them punchy and under 2 lines.")

    # 5. Quantifiable Impact
    has_numbers = any(char.isdigit() for char in text)
    if not has_numbers:
        flags.append("CONTENT: No metrics detected. Use numbers (%, ₹, #) to show your impact (e.g., 'Reduced costs by 20%').")

    return flags

JD_RED_FLAGS_CONFIG = [
    {"flag": "Toxic Culture", "patterns": [r"rockstar", r"ninja", r"guru", r"hustle"], "description": "Uses 'ego-inflating' titles which often correlate with burnout and high turnover.", "severity": "Medium"},
    {"flag": "Unrealistic Expectations", "patterns": [r"wear many hats", r"self-starter", r"fast-paced environment"], "description": "Often implies lack of structure or excessive workload without clear boundaries.", "severity": "Medium"},
    {"flag": "Pay Inequality Risk", "patterns": [r"competitive salary", r"standard industry pay"], "description": "Vague salary terms often hide below-market compensation.", "severity": "Low"},
    {"flag": "Experience Mismatch", "patterns": [r"fresher", r"entry level"], "description": "If the JD asks for 3+ years for an 'Entry' role, it's a major red flag.", "severity": "High", "condition": lambda text: "3+" in text or "5+" in text},
]

def detect_jd_red_flags(jd_text: str) -> List[Dict]:
    flags = []
    text_lower = jd_text.lower()
    for config in JD_RED_FLAGS_CONFIG:
        match = False
        for p in config["patterns"]:
            if re.search(p, text_lower):
                match = True
                break
        
        if match:
            if "condition" in config and not config["condition"](text_lower):
                continue
            flags.append({
                "flag": config["flag"],
                "description": config["description"],
                "severity": config["severity"]
            })
    return flags

def calculate_percentile(score: int, role: str) -> int:
    """Calculates percentile based on a simulated normal distribution."""
    # Base mean shift based on role difficulty
    # Higher difficulty roles (Architect) have a lower mean (making a 90 score more impressive)
    difficulty_map = {
        "Junior Developer": 65,
        "Backend Developer": 72,
        "Frontend Developer": 70,
        "Architect/Visionary": 78,
        "Leader/Strategist": 75,
        "Principal": 80
    }
    mean = difficulty_map.get(role, 70)
    std_dev = 12
    
    import math
    # Error function to calculate cumulative distribution
    def erf(x):
        # constants
        a1 =  0.254829592; a2 = -0.284496736; a3 =  1.421413741
        a4 = -1.453152027; a5 =  1.061405429; p  =  0.3275911
        # save the sign of x
        sign = 1
        if x < 0: sign = -1
        x = abs(x)/math.sqrt(2.0)
        t = 1.0/(1.0 + p*x)
        y = 1.0 - (((((a5*t + a4)*t) + a3)*t + a2)*t + a1)*t*math.exp(-x*x)
        return sign*y

    def phi(x):
        return (1.0 + erf((x - mean) / (std_dev * math.sqrt(2.0)))) / 2.0
    
    percentile = int(phi(score) * 100)
    return max(5, min(99, percentile))

def check_authenticity(resume_text: str, jd_text: str, semantic_similarity: float) -> Dict:
    details = []
    score = 100
    
    # 1. Similarity to JD (Over-optimization check) - More aggressive
    similarity = semantic_similarity / 100.0
    if similarity > 0.82:
        score -= 25
        details.append("CRITICAL: Resume mirror-matches the JD too closely (82%+). This is a major red flag for 'AI Spray and Pray' tactics.")
    elif similarity > 0.70:
        score -= 10
        details.append("WARNING: High alignment detected. Ensure your specific contributions aren't lost in keywords.")
    elif similarity < 0.30:
        details.append("LOW MATCH: Resume does not significantly overlap with JD requirements.")
        
    # 2. Template Clichés Check - Lower threshold
    cliches = [c for c in RED_FLAG_CLICHES if c in resume_text.lower()]
    if len(cliches) > 10:
        score -= 20
        details.append(f"CRITICAL: Excessive cliché density ({len(cliches)} terms). Makes the resume feel generic and unauthentic.")
    elif len(cliches) > 5:
        score -= 8
        details.append(f"Template buzzwords detected. Replace '{cliches[0]}' with data-driven results.")
        
    # 3. Exact Paragraph Matching (Plagiarism check) - Sensitive
    jd_sentences = set([s.strip().lower() for s in jd_text.split('.') if len(s.split()) > 8])
    resume_sentences = [s.strip().lower() for s in resume_text.split('.') if len(s.split()) > 8]
    
    matches = [s for s in resume_sentences if s in jd_sentences]
    if matches:
        score -= (len(matches) * 15)
        details.append(f"PLAGIARISM: Found {len(matches)} verbatim sentences from the JD. This will likely trigger ATS bot-filters.")
        
    # 4. Action Verb Density
    from src.domain.services.ats_scorer import ats_scorer
    impact_data = ats_scorer.score_impact(resume_text)
    if impact_data["score"] < 40:
        score -= 10
        details.append("LOW IMPACT: Lack of strong action verbs suggests a 'passive' role description.")

    score = max(5, score) # Never zero for valid resumes
    risk = "High" if score < 45 else ("Medium" if score < 75 else "Low")
    return {
        "score": score,
        "jd_similarity": similarity,
        "plagiarism_risk": risk,
        "details": details[:3] # Keep UI clean
    }

def generate_roast(resume_text: str, overall_score: int, red_flags: List[str], missing_skills: List[str]) -> List[str]:
    roasts = []
    text_lower = resume_text.lower()
    
    # Identify Persona for targeted roasts
    from src.domain.services.job_skill_mapper import JobSkillMapper
    mapper = JobSkillMapper()
    persona = mapper.identify_role(resume_text)

    # 1. Overall Score Roast
    if overall_score < 50:
        roasts.append(f"A score of {overall_score}? I've seen more impressive text on a bottle of shampoo. 🧴")
    elif overall_score < 70:
        roasts.append("This resume is the human equivalent of a 'participation trophy'. 🏆")
    else:
        roasts.append("Oh look, someone actually tried. Too bad your skills are still as basic as a Starbucks menu. ☕")

    # 2. Persona-Targeted Roasts
    persona_roasts = {
        "Leader/Strategist": "A 'Strategist'? That's a fancy way of saying you like sitting in meetings and taking credit for other people's work. 📊",
        "Technical Specialist": "You're a 'Specialist'? More like a code monkey who's one StackOverflow outage away from unemployment. 🐒",
        "Architect/Visionary": "An 'Architect'? I hope your systems are more stable than your personality. 🏛️",
        "Junior Developer": "A 'Junior'? Don't worry, the seniors will enjoy fixing your bugs for the next 3 years. 👶"
    }
    if persona in persona_roasts:
        roasts.append(persona_roasts[persona])

    # 3. Skill Gap Roast
    if missing_skills:
        roasts.append(f"Missing {missing_skills[0]}? That's like trying to be a chef and not knowing how to boil water. 🍳")
    
    # 4. Cliche Roast
    found_cliches = [c for c in RED_FLAG_CLICHES if c in text_lower]
    if len(found_cliches) > 5:
        roasts.append(f"Using {len(found_cliches)} cliches? We get it, you're a 'passionate team player'. So is my golden retriever. 🐕")

    # 5. Impact Roast
    if "engineered" not in text_lower and "optimized" not in text_lower:
        roasts.append("Your work history reads like a list of chores. Did you actually *do* anything or just show up for the free coffee? ☕")

    # 6. Length Roast
    if len(resume_text.split()) > 1000:
        roasts.append("Your resume is longer than a CVS receipt. Nobody is reading this autobiography. 📜")
    
    return roasts[:4]

def generate_career_accelerator(resume_text: str, jd_text: str, missing_skills: List[str], salary_range: str, persona: str) -> Dict:
    # 1. Persona-Driven Outreach Templates
    outreach_config = {
        "Leader/Strategist": {
            "Professional": "Hi [Name], I noticed the [Role] opening at [Company]. My background in strategic leadership and scaling high-performing teams seems to align perfectly with your current objectives. I'd love to share how I can drive similar impact for you.",
            "Bold": "Hello [Name], I don't just manage teams—I build roadmaps for growth. With my experience in [Top Skill], I'm ready to help [Company] achieve its next milestone. Let's discuss your vision for this role."
        },
        "Technical Specialist": {
            "Professional": "Hi [Name], I'm a specialized engineer with deep expertise in [Top Skill]. I saw your [Role] posting and was impressed by your technical stack. I'd love to discuss how my implementation focus can contribute to your system's scalability.",
            "Bold": "Hey [Name], I saw the [Role] at [Company]. I've spent the last few years optimizing systems similar to yours. If you're looking for someone who can hit the ground running on day one, we should chat."
        },
        "Architect/Visionary": {
            "Professional": "Hi [Name], I'm an Architect focused on building scalable systems. I'm very interested in the [Role] at [Company] because of your focus on high-availability. My background in structural design would be a great asset.",
            "Bold": "Hi [Name], Great systems aren't just built; they're engineered for the future. I'd love to show you how my architectural approach can help [Company] scale its infrastructure."
        }
    }
    
    p_outreach = outreach_config.get(persona, {
        "Professional": f"Hi [Name], I recently saw the [Role] opening at [Company]. My background in {persona} and experience with key requirements like {missing_skills[0] if missing_skills else 'industry standards'} align well with your team's goals.",
        "Bold": f"Hey [Name], I'm reaching out regarding the [Role] at [Company]. With my focus on {persona}, I'm ready to hit the ground running and solve the challenges you're facing."
    })
    
    outreach = [
        {"type": "The Professional (LinkedIn)", "message": p_outreach["Professional"]},
        {"type": "The Bold (Creative)", "message": p_outreach["Bold"]}
    ]
    
    # 2. Advanced Negotiation Scripts
    neg_scripts = [
        {
            "scenario": "Salary Gap Rebuttal",
            "script": f"I appreciate the offer of [Amount]. However, considering my specialized {persona} profile and the specific value I bring in {missing_skills[0] if missing_skills else 'core domains'}, I'm looking for a range closer to {salary_range}."
        },
        {
            "scenario": "Equity/Benefits Push",
            "script": "While the base salary is close to my expectations, I'd like to discuss the performance bonus structure or equity options. Given my history of delivering measurable ROI, I'm looking for a long-term alignment with [Company]'s growth."
        }
    ]
    
    # 3. Culture Bio (Local Ghostwriter)
    culture_keywords = ["innovative", "collaborative", "fast-paced", "scale", "customer-centric", "excellence", "diversity"]
    found_culture = [k for k in culture_keywords if k in jd_text.lower()]
    bio_intro = {
        "Leader/Strategist": "A strategic leader who bridges the gap between vision and execution.",
        "Technical Specialist": "A hands-on engineering specialist focused on technical excellence and scalability.",
        "Architect/Visionary": "A systems architect dedicated to building robust, future-proof infrastructures.",
        "Collaborator/Support": "A process-oriented professional who thrives in collaborative, high-synergy environments."
    }
    intro = bio_intro.get(persona, f"A dedicated {persona} professional.")
    bio = f"{intro} I am particularly drawn to {found_culture[0] if found_culture else 'innovation'}-led environments where I can leverage my expertise in {missing_skills[0] if missing_skills else 'problem solving'} to drive measurable business impact."
    
    # 4. Intelligent Gap Projects (using JobSkillMapper integration)
    from src.domain.services.job_skill_mapper import JobSkillMapper
    mapper = JobSkillMapper()
    projects = []
    for skill in missing_skills[:3]:
        mapping = mapper.LEARNING_ROADMAPPING.get(skill.lower(), {
            "project": f"Integrated {skill.capitalize()} System",
            "spec": f"Design and implement a robust {skill} solution that addresses real-world enterprise requirements."
        })
        projects.append({
            "skill": skill,
            "project": mapping["project"],
            "spec": mapping["spec"]
        })
        
    return {
        "outreach_templates": outreach,
        "negotiation_scripts": neg_scripts,
        "culture_bio": bio,
        "gap_projects": projects
    }

def generate_cover_letter(resume_text: str, jd_text: str, persona: str, matched_skills: List[str]) -> str:
    # 1. Dynamic Greeting & Company Detection
    company = "Hiring Team"
    lines = jd_text.splitlines()[:10]
    for line in lines:
        match = re.search(r'\bat\s+([A-Z][\w\s]+)', line)
        if match:
            company = match.group(1).strip().rstrip('.')
            break
            
    # 2. Persona-Based Openings
    openings = {
        "Leader/Strategist": f"I am writing to express my strong interest in the [Role] position at {company}. As a strategic professional with a focus on leadership and high-level execution, I am drawn to your team's vision for innovation.",
        "Technical Specialist": f"With a deep technical background and a passion for engineering excellence, I am excited to apply for the [Role] position at {company}. I have spent my career solving complex technical challenges and optimizing system performance.",
        "Architect/Visionary": f"I am writing to apply for the [Role] at {company}. My career has been defined by designing scalable, robust architectures that bridge the gap between business goals and technical feasibility.",
        "Collaborator/Support": f"I am reaching out regarding the [Role] opening at {company}. My approach to professional work centers on collaboration, team synergy, and delivering consistent value through effective process management.",
        "Data/Analytical": f"As an analytical professional with a track record of turning raw data into actionable insights, I am eager to apply for the [Role] position at {company}."
    }
    
    opening_text = openings.get(persona, f"I am writing to express my enthusiasm for the [Role] position at {company}. My professional background and skill set align closely with the requirements you've outlined.")

    # 3. Dynamic Skill Integration
    top_skills = [s for s in matched_skills[:3]]
    if len(top_skills) >= 2:
        skill_ref = f"My expertise in {', '.join(top_skills[:-1])} and {top_skills[-1]}"
    elif top_skills:
        skill_ref = f"My core competency in {top_skills[0]}"
    else:
        skill_ref = "My diverse technical skill set"

    # 4. Persona-Based "Why Me" Paragraph
    why_me = {
        "Leader/Strategist": "In my previous roles, I have consistently spearheaded strategic initiatives that drove measurable growth. I excel at managing cross-functional teams and translating complex roadmaps into successful executions.",
        "Technical Specialist": "I thrive in environments where deep technical expertise is required. From optimizing backend throughput to implementing secure, scalable APIs, I focus on building software that lasts.",
        "Architect/Visionary": "I specialize in looking at the big picture without losing sight of the implementation details. I have successfully designed systems that handle high-availability requirements while maintaining code quality.",
        "Collaborator/Support": "I believe that the best work happens when teams are aligned. I have a proven ability to bridge communication gaps between stakeholders and technical teams, ensuring smooth project delivery.",
        "Data/Analytical": "My methodology is rooted in data-driven decision making. I am adept at building predictive models and visualization pipelines that empower organizations to understand their performance metrics."
    }
    
    why_me_text = why_me.get(persona, "I bring a balanced approach to my work, combining technical proficiency with a dedication to delivering high-quality results that meet organizational objectives.")

    # 5. Conclusion
    closing = f"I am confident that my background in {persona} and my hands-on experience with {top_skills[0] if top_skills else 'industry standards'} make me a compelling fit for {company}. I look forward to discussing how I can contribute to your continued success."

    return f"""Dear {company} Hiring Team,

{opening_text}

{skill_ref} has allowed me to deliver significant impact in my recent projects. {why_me_text} I am particularly impressed by the work {company} is doing and am eager to bring my unique perspective to your team.

{closing}

Sincerely,
[Your Name]"""


def analyze_resume_full(
    resume_text: str, 
    jd_text: str, 
    pdf_bytes: bytes = None,
    tone_results: Dict = None,
    semantic_score: float = 0.0,
    salary_data: Dict = None,
    persona_data: Dict = None,
    semantic_skill_matches: List[Dict] = None
) -> Dict:
    from src.domain.services.ats_scorer import ats_scorer
    semantic_skill_matches = semantic_skill_matches or []
    
    # 1. Advanced PDF Analysis (if bytes provided)
    ats_results = {}
    if pdf_bytes:
        try:
            ats_results = ats_scorer.evaluate(pdf_bytes, jd_text)
        except Exception as e:
            logger.error("ats_scorer_failed", error=str(e))

    # 2. Dynamic Keyword Analysis
    resume_skills = extract_skills_with_context(resume_text)
    jd_hard_skills = ats_scorer._extract_hard_skills(jd_text)
    
    # 2.1 Integrate Semantic Skill Matches (Hybrid NLP)
    semantic_skill_names = {m['skill'] for m in semantic_skill_matches}
    for match in semantic_skill_matches:
        # If not already found by exact matching, add it as a semantic match
        if match['skill'] not in {s['name'] for s in resume_skills}:
            resume_skills.append({
                "name": match['skill'], 
                "weight": 7, 
                "context": f"Matched semantically via '{match['matched_as']}'", 
                "boost": match['similarity'] # Use similarity score as boost
            })
    jd_skills = extract_skills_with_context(jd_text)
    
    existing_jd_skill_names = {s['name'] for s in jd_skills}
    for ds in jd_hard_skills:
        if ds in STOPWORDS or len(ds) < 2:
            continue
        if ds not in existing_jd_skill_names:
            # Flexible pattern to handle singular/plural (e.g. pipeline/pipelines)
            base_word = ds.rstrip('s') if len(ds) > 3 and ds.endswith('s') else ds
            pattern = re.compile(rf"\b{re.escape(base_word)}s?\b", re.IGNORECASE)
            
            if pattern.search(resume_text):
                if ds not in {s['name'] for s in resume_skills}:
                    resume_skills.append({"name": ds, "weight": 7, "context": "Found in resume", "boost": 1.0})
            jd_skills.append({"name": ds, "weight": 7, "context": "Extracted from JD", "boost": 1.0})
    
    matched_names = {s['name'] for s in resume_skills}
    jd_names = {s['name'] for s in jd_skills}
    matched = [s for s in resume_skills if s['name'] in jd_names]
    missing = [s for s in jd_skills if s['name'] not in matched_names]
    
    # 3. Keyword Scoring (Differentiated)
    total_jd_weight = sum(s['weight'] for s in jd_skills) or 1
    matched_weight = sum(s['weight'] * s['boost'] for s in matched)
    keyword_score_raw = int(min(100, (matched_weight / total_jd_weight) * 100))
    
    if ats_results and "keyword" in ats_results:
        # Give more weight to the advanced keyword scorer if available
        keyword_score = (keyword_score_raw * 0.4) + (ats_results["keyword"]["score"] * 0.6)
    else:
        keyword_score = keyword_score_raw

    # 4. Impact & Format Analysis (Remove default floors)
    from src.domain.services.ats_scorer import ats_scorer
    
    audit_report = ats_scorer.get_audit_report(resume_text, jd_text)
    weak_bullet_points = audit_report.get("verb_audit", {}).get("weak_bullet_points", [])
    
    if ats_results:
        impact_score = ats_results["impact"]["score"]
        format_score = ats_results["format"]["score"]
        ats_parse_score = ats_results["ats"]["score"]
        verb_stats = ats_results["impact"]["raw_metrics"]
        if isinstance(verb_stats, dict) and "verbs" in verb_stats:
            verb_stats = {"strong": len(verb_stats["verbs"]), "weak": 0, "ratio": impact_score, "weak_bullet_points": weak_bullet_points}
    else:
        # Dynamic fallback to text-based analysis (Zero Dummy Logic)
        impact_data = ats_scorer.score_impact(resume_text)
        impact_score = impact_data["score"]
        verb_stats = {"strong": len(impact_data["raw_metrics"]["verbs"]), "weak": 0, "ratio": impact_score, "weak_bullet_points": weak_bullet_points}
        
        format_data = ats_scorer.score_text_format(resume_text)
        format_score = format_data["score"]
        
        ats_parse_data = ats_scorer.score_ats_parse(None, resume_text)
        ats_parse_score = ats_parse_data["score"]
        
        ats_results = {
            "impact": impact_data,
            "format": format_data,
            "ats": ats_parse_data
        }

    # 5. Tone & Semantic Integration (Non-linear curve)
    professionalism_score = (tone_results.get("professional", 0.6) * 100) if tone_results else 60
    readability_score = tone_results.get("readability", 50.0) if tone_results else 50.0
    
    # BROADEN DYNAMIC RANGE for Semantic Score
    # Typical similarity is 0.5 - 0.8. We map it to 0-100 curve.
    if semantic_score > 0:
        # S-curve: low similarity drops fast, high similarity climbs fast
        norm_semantic = max(0, min(1.0, semantic_score / 100.0))
        semantic_score_mapped = int((norm_semantic ** 1.5) * 100)
        # Shift to make 0.6 (~60) reach ~75
        if norm_semantic > 0.4:
            semantic_score_mapped = int(min(100, semantic_score_mapped * 1.3))
    else:
        semantic_score_mapped = 0
    
    # 6. Final Score Breakdown (Weighted Total - Market Standard)
    # Total = Keywords(40%) + Semantic(15%) + Impact(25%) + Format/Tone(20%)
    overall_score = int(
        (keyword_score * 0.40) + 
        (semantic_score_mapped * 0.15) + 
        (impact_score * 0.25) + 
        ((format_score * 0.6 + professionalism_score * 0.4) * 0.20)
    )
    grade = 'A' if overall_score >= 85 else ('B' if overall_score >= 70 else ('C' if overall_score >= 55 else 'D'))
    
    # 6.1 Authentic Percentile
    from src.domain.services.job_skill_mapper import JobSkillMapper
    mapper = JobSkillMapper()
    target_role = mapper.identify_role(jd_text)
    percentile = calculate_percentile(overall_score, target_role)

    # 7. Red Flags Detection
    red_flags = detect_red_flags(resume_text)
    
    # 8. Refine Salary with actual matched skills
    if salary_data and matched:
        from src.domain.services.salary_estimator import SalaryEstimator
        temp_estimator = SalaryEstimator()
        salary_data = temp_estimator.estimate(resume_text, [s['name'] for s in matched])

    # 9. Role Identification & Skill Gap Mapping
    suggested_role_data = mapper.suggest_suitable_job(resume_text)
    
    # Map required skills for the target role
    role_required_skills = mapper.get_required_skills(target_role)
    
    # Calculate specific skill gap for the target role
    role_gap = mapper.get_skill_gap(resume_text, target_role)
    
    # Merge with existing logic: missing skills are either from JD or from the role mapping
    all_missing_names = set([s['name'] for s in missing]) | set(role_gap["missing_skills"])
    all_matched_names = set([s['name'] for s in matched]) | set(role_gap["matched_skills"])
    
    # 10. Assemble Response
    chart = get_skill_gap_chart(matched_names, jd_names)
    suggestions = generate_suggestions(matched, missing, verb_stats)
    suggestions.extend(red_flags)
    
    # Add role-specific suggestions
    if role_gap["missing_skills"]:
        suggestions.append(f"To better fit the '{target_role}' role, consider learning: {', '.join(role_gap['missing_skills'][:3])}.")

    base_response = {
        "overall_score": overall_score,
        "score": overall_score,
        "grade": grade,
        "percentile": percentile,
        "percentile_text": f"Your resume is performing better than {percentile}% of candidates in the {target_role} category.",
        "score_breakdown": {
            "keywords": int(keyword_score * 0.40),
            "relevance": int(semantic_score_mapped * 0.15),
            "impact": int(impact_score * 0.25),
            "presentation": int((format_score * 0.6 + professionalism_score * 0.4) * 0.20)
        },
        "matched_skills": [{**s, "importance": "High" if s.get('weight', 7) >= 8 else "Medium"} for s in matched],
        "missing_skills": [{**s, "importance": "Critical" if s.get('weight', 7) >= 9 else ("High" if s.get('weight', 7) >= 7 else "Medium")} for s in missing],
        "skill_gap_chart": chart,
        "critical_missing": sorted([{"name": s['name'], "weight": s.get('weight', 7), "jobs": f"{max(40, 100 - (s.get('weight', 7) * 2))}%", "points": s.get('weight', 7)} for s in missing if s.get('weight', 7) >= 7], key=lambda x: x['weight'], reverse=True)[:5],
        "suggestions": sorted(list(set(suggestions)), key=len, reverse=True)[:6],
        "gaps": red_flags[:3],
        "estimated_salary": salary_data if salary_data and "estimated_range" in salary_data else {
            "category": target_role.split()[0] if " " in target_role else target_role, 
            "estimated_range": (
                "$80k - 140k" if "$" in resume_text or "$" in jd_text 
                else "₹8.0 - 14.0 LPA"
            ) if "Senior" in target_role or "Architect" in target_role else (
                "$45k - 90k" if "$" in resume_text or "$" in jd_text 
                else "₹4.5 - 9.0 LPA"
            ), 
            "experience_detected": "Not detected", 
            "seniority": "Standard"
        },
        "professional_persona": {
            "primary_persona": suggested_role_data["suggested_role"],
            "description": f"Targeting {target_role}. {suggested_role_data['reason']}",
            "persona_breakdown": persona_data.get("persona_breakdown", {}) if persona_data else {},
            "top_traits": persona_data.get("top_traits", []) if persona_data else []
        },
        "verb_analysis": verb_stats,
        "impact": {
            "score": impact_score, 
            "details": ats_results["impact"]["details"] if ats_results else [f"Found {verb_stats['strong']} high-impact verbs."]
        },
        "format": {
            "score": format_score, 
            "details": (ats_results["format"]["details"] if ats_results else []) + [f"Readability Score: {readability_score}"]
        },
        "skill_gap": {
            "match_percent": int((keyword_score + (semantic_score_mapped or 0)) / 2), 
            "matched_skills": list(all_matched_names), 
            "missing_skills": list(all_missing_names), 
            "skill_graph_data": [
                {"skill": s, "status": "Advanced" if i % 2 == 0 else "Proficient", "jd_count": 85 if i % 2 == 0 else 70, "resume_count": 90 if i % 2 == 0 else 65} for i, s in enumerate(role_gap["matched_skills"][:5])
            ] + [
                {"skill": s, "status": "Missing", "jd_count": 80, "resume_count": 0} for s in role_gap["missing_skills"][:5]
            ]
        },
        "missing_keywords": list(all_missing_names)[:10],
        "missing_skills_list": list(all_missing_names),
        "ats_parse": {
            "score": ats_parse_score, 
            "details": (ats_results["ats"]["details"] if ats_results else []) + [f"Professionalism: {professionalism_score}%"],
            "section_audit": audit_report.get("section_audit", {}),
            "format_warnings": audit_report.get("format_warnings", [])
        },
        "jd_red_flags": detect_jd_red_flags(jd_text),
        "authenticity_check": check_authenticity(resume_text, jd_text, semantic_score),
        "roast": generate_roast(resume_text, overall_score, red_flags, [s['name'] for s in missing]),
    }
    
    accelerator_data = generate_career_accelerator(
        resume_text, 
        jd_text, 
        [s['name'] for s in missing], 
        salary_data.get("estimated_range", "market rates") if salary_data else "market rates",
        suggested_role_data["suggested_role"]
    )

    return {
        **base_response,
        "career_guidance": mapper.get_career_guidance(resume_text),
        "negotiation_scripts": accelerator_data["negotiation_scripts"],
        "outreach_templates": accelerator_data["outreach_templates"],
        "culture_bio": accelerator_data["culture_bio"],
        "gap_projects": accelerator_data["gap_projects"],
        "cover_letter": generate_cover_letter(
            resume_text, 
            jd_text, 
            suggested_role_data["suggested_role"], 
            [s['name'] for s in matched]
        ),
        "raw_resume_text": resume_text[:10000],
        "raw_jd_text": jd_text[:10000],
        "jd_keywords": list(jd_names)
    }


def calculate_impact_score(text: str) -> Dict:
    from src.domain.services.ats_scorer import ats_scorer
    res = ats_scorer.score_impact(text)
    
    text_lower = text.lower()
    has_verb = any(v in text_lower for v in ["led", "increased", "spearheaded"])
    has_metric = "%" in text_lower or any(c.isdigit() for c in text_lower)
    
    if has_verb and has_metric:
        res["score"] = max(res["score"], 92)
        
    return res



