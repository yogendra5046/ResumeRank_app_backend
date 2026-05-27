import re
from typing import List, Dict, Set

class JobSkillMapper:
    """Maps job roles to required skills and suggests roles based on resume content."""

    def __init__(self):
        # Role -> Required Skills
        self.ROLE_SKILLS = {
            "Backend Developer": ["python", "django", "fastapi", "sql", "postgresql", "docker", "kubernetes", "rest api", "microservices", "redis", "mongodb"],
            "Frontend Developer": ["javascript", "typescript", "react", "angular", "vue", "html", "css", "tailwind", "figma", "sass", "webpack"],
            "Fullstack Developer": ["python", "javascript", "react", "node.js", "sql", "docker", "aws", "express", "mongodb"],
            "Data Scientist": ["python", "pandas", "numpy", "machine learning", "deep learning", "pytorch", "tensorflow", "sql", "scikit-learn", "data visualization"],
            "DevOps Engineer": ["aws", "azure", "gcp", "docker", "kubernetes", "terraform", "jenkins", "ci/cd", "ansible", "linux", "bash"],
            "Mobile Developer": ["flutter", "dart", "swift", "kotlin", "react native", "android", "ios", "firebase"],
            "Product Manager": ["leadership", "agile", "scrum", "kanban", "product management", "stakeholder management", "roadmap", "jira"],
            "UI/UX Designer": ["figma", "ui/ux", "design thinking", "adobe xd", "prototyping", "wireframing", "user research"],
            "Data Engineer": ["python", "sql", "spark", "hadoop", "kafka", "airflow", "data pipeline", "etl", "snowflake"],
            "Cybersecurity Engineer": ["network security", "penetration testing", "siem", "firewalls", "encryption", "vulnerability assessment", "linux"],
            "Junior Developer": ["git", "python", "javascript", "data structures", "algorithms", "problem solving", "html", "css", "sql"],
            "General Professional": ["communication", "teamwork", "git", "problem solving", "leadership", "management", "documentation", "agile"]
        }

        # CAREER PATH GRAPH (Role -> Next Possible Roles)
        self.CAREER_PATHS = {
            "Junior Developer": ["Backend Developer", "Frontend Developer", "Fullstack Developer"],
            "Backend Developer": ["Fullstack Developer", "DevOps Engineer", "Data Engineer"],
            "Frontend Developer": ["Fullstack Developer", "UI/UX Designer"],
            "Mobile Developer": ["Fullstack Developer", "Product Manager"],
            "Data Scientist": ["Data Engineer", "ML Ops Engineer"],
            "DevOps Engineer": ["Site Reliability Engineer", "Cloud Architect"],
            "Fullstack Developer": ["Software Architect", "Product Manager"],
            "UI/UX Designer": ["Product Designer", "Product Manager"]
        }

        # SKILL LEARNING BRIDGES (Skill -> Specific Learning Topics & Projects)
        self.LEARNING_ROADMAPPING = {
            "docker": {
                "topics": ["Container Fundamentals", "Dockerfile Optimization", "Docker Compose"],
                "project": "Cloud-Native Microservices Wrapper",
                "spec": "Dockerize a polyglot microservices application with optimized multi-stage builds and a private registry setup."
            },
            "kubernetes": {
                "topics": ["K8s Architecture", "Helm Charts", "Managed K8s (EKS/GKE)"],
                "project": "Auto-scaling Cluster Deployment",
                "spec": "Deploy a high-availability cluster with Horizontal Pod Autoscaling (HPA) and ingress controllers for traffic management."
            },
            "python": {
                "topics": ["AsyncIO", "Metaprogramming", "FastAPI/Django"],
                "project": "High-Throughput Async API",
                "spec": "Build a distributed task queue system using Python's asyncio and Redis for real-time data processing."
            },
            "react": {
                "topics": ["Hooks API", "State Management (Redux/Zustand)", "Next.js/SSR"],
                "project": "Enterprise Dashboard with SSR",
                "spec": "Create a performant dashboard featuring server-side rendering, dynamic routing, and complex state synchronization."
            },
            "machine learning": {
                "topics": ["Linear Algebra", "Scikit-Learn", "Neural Networks"],
                "project": "Predictive Analytics Pipeline",
                "spec": "Develop an end-to-end ML pipeline from data cleaning to model deployment using Scikit-Learn and MLflow."
            },
            "aws": {
                "topics": ["EC2/S3 Essentials", "Serverless (Lambda)", "IAM Security"],
                "project": "Serverless Image Processor",
                "spec": "Build an event-driven architecture using Lambda, S3, and DynamoDB for automated image optimization and tagging."
            },
            "leadership": {
                "topics": ["Agile Methodologies", "Conflict Resolution", "Strategic Planning"],
                "project": "Organizational Roadmap Design",
                "spec": "Develop a comprehensive strategic roadmap and OKR framework for a scaling engineering team."
            },
            "fastapi": {
                "topics": ["Dependency Injection", "Pydantic V2", "WebSocket Integration"],
                "project": "Real-time Analytics Engine",
                "spec": "Engineer a real-time monitoring system using WebSockets and background tasks for live telemetry streaming."
            },
            "sql": {
                "topics": ["Query Optimization", "Window Functions", "Indexing Strategies"],
                "project": "Financial Transaction Auditor",
                "spec": "Design a complex relational schema with advanced SQL procedures for auditing multi-currency transactions."
            },
            "javascript": {
                "topics": ["ES6+ Features", "Event Loop", "Memory Management"],
                "project": "Interactive Canvas Engine",
                "spec": "Build a custom 2D rendering engine using vanilla JS and HTML5 Canvas with efficient collision detection."
            }
        }

        # Role -> Identification Keywords (for JD analysis)
        self.ROLE_IDENTIFIERS = {
            "Backend Developer": ["backend", "server-side", "api developer", "python developer", "java developer", "golang developer"],
            "Frontend Developer": ["frontend", "client-side", "ui developer", "react developer", "web developer"],
            "Fullstack Developer": ["fullstack", "full stack", "end-to-end"],
            "Data Scientist": ["data scientist", "machine learning engineer", "ml engineer", "ai engineer"],
            "DevOps Engineer": ["devops", "site reliability", "sre", "infrastructure engineer"],
            "Mobile Developer": ["mobile", "android", "ios", "flutter", "react native"],
            "Product Manager": ["product manager", "pm", "product owner"],
            "UI/UX Designer": ["ui/ux", "product designer", "user experience"],
            "Data Engineer": ["data engineer", "etl developer", "big data"],
            "Cybersecurity Engineer": ["cybersecurity", "security analyst", "information security"],
            "Junior Developer": ["student", "intern", "trainee", "fresher", "junior", "computer science student", "entry level"]
        }

        # TRANSITION DIFFICULTY (Role A -> Role B : 1-10 scale)
        self.TRANSITION_METRICS = {
            ("Junior Developer", "Backend Developer"): {"difficulty": 3, "time": "3-6 months"},
            ("Junior Developer", "Frontend Developer"): {"difficulty": 2, "time": "2-4 months"},
            ("Backend Developer", "Fullstack Developer"): {"difficulty": 4, "time": "6 months"},
            ("Frontend Developer", "Fullstack Developer"): {"difficulty": 5, "time": "8 months"},
            ("Backend Developer", "DevOps Engineer"): {"difficulty": 6, "time": "9 months"},
            ("Data Scientist", "Data Engineer"): {"difficulty": 5, "time": "6 months"},
            ("Fullstack Developer", "Software Architect"): {"difficulty": 8, "time": "12-18 months"},
            ("Mobile Developer", "Product Manager"): {"difficulty": 7, "time": "12 months"},
        }

        # FUTURE-PROOFING (Emerging vs Legacy)
        self.FUTURE_SKILLS = {
            "emerging": ["fastapi", "rust", "golang", "terraform", "kubernetes", "pytorch", "transformers", "next.js", "flutter", "solidity"],
            "stable": ["python", "java", "sql", "aws", "react", "docker", "typescript", "linux", "git"],
            "legacy": ["jquery", "php", "perl", "svn", "struts", "angularjs", "coldfusion", "vb6"]
        }

        # INDUSTRY ALIGNMENT
        self.INDUSTRY_MAP = {
            "FinTech": ["python", "sql", "security", "java", "kubernetes", "blockchain"],
            "E-Commerce": ["javascript", "react", "node.js", "aws", "next.js", "seo"],
            "HealthTech": ["data privacy", "hipaa", "python", "machine learning", "cloud security"],
            "AI / Robotics": ["pytorch", "tensorflow", "c++", "rust", "linux", "nlp"],
            "EdTech": ["flutter", "dart", "firebase", "react", "video streaming"]
        }

    def identify_role(self, text: str) -> str:
        """Identifies the most likely job role from text (JD or Resume)."""
        text_lower = text.lower()
        scores = {}
        
        # Check for seniority to prevent false 'Junior' flagging
        seniority_keywords = ["senior", "lead", "manager", "staff", "principal", "director", "head of", "architect"]
        is_senior = any(re.search(r'\b' + re.escape(kw) + r'\b', text_lower) for kw in seniority_keywords)

        for role, keywords in self.ROLE_IDENTIFIERS.items():
            score = 0
            for kw in keywords:
                if re.search(r'\b' + re.escape(kw) + r'\b', text_lower):
                    score += 5  # Strong identifier match
            
            # Boost score significantly based on actual skills
            for skill in self.ROLE_SKILLS.get(role, []):
                if re.search(r'\b' + re.escape(skill) + r'\b', text_lower):
                    score += 2  # Increased from 1 to 2
            
            # Penalize Junior Developer if senior keywords are present
            if role == "Junior Developer" and is_senior:
                score -= 15
                
            scores[role] = score

        if not scores or max(scores.values()) < 4:
            return "General Professional"

        return max(scores, key=scores.get)

    def get_required_skills(self, role: str) -> List[str]:
        """Returns the list of required skills for a given role."""
        return self.ROLE_SKILLS.get(role, [])

    def suggest_suitable_job(self, resume_text: str) -> Dict[str, any]:
        """Suggests a suitable job title and lists why."""
        role = self.identify_role(resume_text)
        required_skills = self.get_required_skills(role)
        
        # Simple match check
        resume_lower = resume_text.lower()
        matched = [s for s in required_skills if re.search(r'\b' + re.escape(s) + r'\b', resume_lower)]
        
        return {
            "suggested_role": role,
            "match_count": len(matched),
            "total_required": len(required_skills),
            "reason": f"Matches {len(matched)} key skills for {role}."
        }

    def get_skill_gap(self, resume_text: str, role: str) -> Dict[str, List[str]]:
        """Calculates which required skills for a role are missing from the resume."""
        required = self.get_required_skills(role)
        resume_lower = resume_text.lower()
        
        matched = []
        missing = []
        
        for skill in required:
            if re.search(r'\b' + re.escape(skill) + r'\b', resume_lower):
                matched.append(skill)
            else:
                missing.append(skill)
                
        return {
            "matched_skills": matched,
            "missing_skills": missing
        }

    def get_future_proof_score(self, resume_text: str) -> Dict[str, any]:
        """Analyzes the resume for emerging vs legacy skills."""
        text_lower = resume_text.lower()
        emerging_found = [s for s in self.FUTURE_SKILLS["emerging"] if re.search(r'\b' + re.escape(s) + r'\b', text_lower)]
        legacy_found = [s for s in self.FUTURE_SKILLS["legacy"] if re.search(r'\b' + re.escape(s) + r'\b', text_lower)]
        
        score = 70 + (len(emerging_found) * 5) - (len(legacy_found) * 10)
        score = max(10, min(99, score))
        
        return {
            "score": score,
            "emerging_skills": emerging_found,
            "legacy_skills": legacy_found,
            "verdict": "Future-Proof" if score > 80 else ("Stable" if score > 50 else "High Legacy Risk")
        }

    def get_industry_alignment(self, resume_text: str) -> List[Dict[str, any]]:
        """Determines which industries best suit the user's skill set."""
        text_lower = resume_text.lower()
        alignments = []
        
        for industry, skills in self.INDUSTRY_MAP.items():
            matched = [s for s in skills if re.search(r'\b' + re.escape(s) + r'\b', text_lower)]
            if matched:
                alignments.append({
                    "industry": industry,
                    "fit_score": int((len(matched) / len(skills)) * 100),
                    "matched_skills": matched
                })
        
        return sorted(alignments, key=lambda x: x["fit_score"], reverse=True)

    def get_career_guidance(self, resume_text: str) -> Dict[str, any]:
        """Predicts the next career step and provides a roadmap to get there."""
        current_role = self.identify_role(resume_text)
        next_roles = self.CAREER_PATHS.get(current_role, ["Senior " + current_role])
        
        # Comprehensive Roadmap
        roadmap = []
        for i, target_role in enumerate(next_roles[:3]):
            gap = self.get_skill_gap(resume_text, target_role)
            metric = self.TRANSITION_METRICS.get((current_role, target_role), {"difficulty": 5, "time": "6-12 months"})
            
            step_roadmap = []
            for skill in gap["missing_skills"][:3]:
                mapping = self.LEARNING_ROADMAPPING.get(skill.lower(), {
                    "topics": ["Advanced " + skill.capitalize() + " Implementation"],
                    "project": f"Integrated {skill.capitalize()} System",
                    "spec": f"Design and implement a robust {skill} solution that addresses real-world enterprise requirements."
                })
                step_roadmap.append({
                    "skill": skill,
                    "topics": mapping["topics"],
                    "project": mapping["project"],
                    "spec": mapping["spec"]
                })

            roadmap.append({
                "milestone": f"Step {i+1}: {target_role}",
                "role": target_role,
                "difficulty": metric["difficulty"],
                "estimated_time": metric["time"],
                "readiness": int((len(gap["matched_skills"]) / max(1, len(self.ROLE_SKILLS.get(target_role, [])))) * 100),
                "skills_to_add": gap["missing_skills"][:4],
                "learning_path": step_roadmap
            })
            
        future_proof = self.get_future_proof_score(resume_text)
        industry_fit = self.get_industry_alignment(resume_text)

        # For frontend compat
        first_step_readiness = roadmap[0]["readiness"] if roadmap else 0
        first_step_roadmap = roadmap[0]["learning_path"] if roadmap else []

        return {
            "current_role": current_role,
            "next_best_move": next_roles[0],
            "roadmap": roadmap,
            "future_proof_analysis": future_proof,
            "industry_alignment": industry_fit,
            "alternative_paths": next_roles[1:],
            "skill_readiness": first_step_readiness,
            "learning_roadmap": first_step_roadmap
        }

    def get_skills_for_role(self, role: str) -> List[str]:
        """Helper for Market Insights Use Case."""
        return self.ROLE_SKILLS.get(role, [])
