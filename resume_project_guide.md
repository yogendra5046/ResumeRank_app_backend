# ResumeRank Pro: Project Documentation & Resume Integration Guide

This guide provides a comprehensive breakdown of the **ResumeRank Pro** project. It is designed to give you all the technical details, architecture descriptions, scoring formulas, and high-impact resume bullet points so you can easily add this project to your resume or feed it into any resume-builder AI.

---

## 1. Project Profile: ResumeRank Pro

* **Project Title**: **ResumeRank Pro** (Enterprise ATS & Career Accelerator Platform)
* **Tagline**: An asynchronous, domain-driven applicant tracking scoring engine and career accelerator built with Python, FastAPI, React, and Flutter, matching resumes to job descriptions using hybrid semantic keyword matching and Hugging Face sentence transformers.
* **Architecture**: Clean Architecture / Hexagonal Architecture (Domain-Driven Design).
* **Key Stats**: 
  - Sync request processing latency: **< 800ms** (p95) using local embedder and Redis caching.
  - Test suite coverage requirement: **> 95%** code coverage enforcement.
  - Image size: **< 150MB** optimized using secure, distroless Docker builds.

---

## 2. Technology Stack & Keywords (For Resume Skills Section)

| Category | Technologies / Tools |
| :--- | :--- |
| **Backend Frameworks** | Python 3.11, FastAPI, Uvicorn, SQLAlchemy ORM, Pydantic v2, Structlog |
| **AI / Machine Learning** | Sentence-Transformers (`all-MiniLM-L6-v2`), PyTorch, spaCy (`en_core_web_sm`), NumPy, Jina AI Reader API |
| **Databases & Caching** | Redis (v7.0) with `orjson` serialization, SQLite (dev), PostgreSQL (prod) |
| **Frontend & SDK** | React 19, Vite 8, Vanilla CSS (Glassmorphism), Flutter SDK (v3.19.0), Flutter BLoC, Hive NoSQL |
| **Security & Compliance** | ClamAV (malware protection), GDPR Right-to-Erasure (Article 17 compliance), PII regex-hashing, API-key authentication |
| **Infrastructure / DevOps** | Terraform, Google Cloud Platform (Cloud Run, Cloud Memorystore Redis, Secret Manager, Cloud Load Balancer), Docker (distroless), GitHub Actions, Trivy Security Scanner, Workload Identity Federation (WIF) |

---

## 3. High-Impact Resume Bullet Points (Ready to Copy)

### Option A: For Backend / Full-Stack Engineer Roles
* **Engineered** a high-performance ATS parser and scoring backend using **FastAPI** and **Python 3.11**, achieving sub-800ms (p95) latency by implementing an asynchronous pipeline, thread-pool offloading, and custom Redis caching.
* **Designed** and deployed an enterprise-grade cloud architecture on **GCP** using **Terraform (IaC)**, leveraging Cloud Run (auto-scaling), Cloud Memorystore (Redis), and Cloud Load Balancer with SSL/TLS termination.
* **Implemented** a secure, containerized file-upload workflow integrated with a **ClamAV** scanner service, ensuring a fail-closed architecture that scans PDF bytes via TCP sockets before execution.
* **Authored** a robust CI/CD pipeline using **GitHub Actions** enforcing linting (Ruff), strict static typing (Mypy), container vulnerability scans (Trivy), and **95% unit test coverage** using Pytest with real containerized services.
* **Developed** the **ResumeRank Flutter SDK** and cross-platform mobile client utilizing the **BLoC pattern** for state management, secure credentials storage, and **Hive NoSQL** for fast local caching.

### Option B: For AI / NLP / Machine Learning Engineer Roles
* **Built** a hybrid semantic search and keyword extraction pipeline using **spaCy** and **Sentence-Transformers (`all-MiniLM-L6-v2`)** to evaluate resumes against job descriptions with 384-dimensional dense vectors.
* **Created** a custom non-linear scoring algorithm mapping cosine similarity, exact/synonym keyword match density, content impact quality (action verbs and metrics detection), and formatting issues (deducting for tables/multi-columns).
* **Integrated** a local Hugging Face NLP model, eliminating external API dependencies, reducing inference costs to zero, and reducing caching hit times to **< 5ms** using SHA-256 key hashing in **Redis**.
* **Developed** a career accelerator engine leveraging **LLaMA** models (via Groq) to generate context-aware cover letters, dynamic LinkedIn outreach templates, salary negotiation scripts, and custom skill-gap learning projects.
* **Designed** a semantic skill-bridging model using spaCy's noun-chunking and vector dot-products to match conceptual skills (e.g., matching "AWS" to "Amazon Cloud Services") at a similarity threshold >0.82.

---

## 4. System Architecture & Detailed Workings

### 4.1 Hexagonal Architecture Layout
The backend follows Domain-Driven Design (DDD) principles:
* **Domain Layer**: Contains pure business logic, scoring formulas (`scoring.py`), entity definitions, and ports (interfaces). Zero external framework dependencies.
* **Application Layer**: Contains use cases (`AnalyzeResumeUseCase`) that orchestrate domain logic and ports.
* **Infrastructure Layer**: Contains adapters implementing ports (e.g., `PyMuPdfExtractor` for text extraction, `RedisCacheAdapter` for caching, `ClamAvScanner` for security, and ML models).
* **Presentation Layer**: Thin FastAPI route controllers (`/v1/analyze`) handling HTTP requests, file reading, and routing.

```
+------------------------------------------------------------+
|                     PRESENTATION LAYER                     |
|            FastAPI Routers (REST endpoints, DI)            |
+-----------------------------+------------------------------+
                              |
                              v
+------------------------------------------------------------+
|                      APPLICATION LAYER                     |
|           Use Cases (Orchestration, Async Jobs)            |
+-----------------------------+------------------------------+
                              |
                              v
+------------------------------------------------------------+
|                        DOMAIN LAYER                        |
|       Entities, Scorers, Validators, Interfaces (Ports)     |
+-----------------------------+------------------------------+
                              ^
                              | (Implements Ports)
+-----------------------------+------------------------------+
|                    INFRASTRUCTURE LAYER                    |
|  Adapters: Redis, PyMuPDF, all-MiniLM-L6-v2, ClamAV, GCP    |
+------------------------------------------------------------+
```

### 4.2 Step-by-Step Request-Response Execution Lifecycle
1. **Authentication & Validation**: The API request to `/v1/analyze` is verified using SHA-256 hashed API-key credentials with a **100 requests/day** Redis rate-limiter.
2. **Malware Scanning**: Streamed PDF bytes are sent directly to a ClamAV daemon via TCP sockets. The system fails closed and rejects infected files with a `400 Bad Request`.
3. **Validation Heuristics**: The job description is verified via `JobDescriptionValidator` (length, structure, content checks).
4. **Cache Lookup**: SHA-256 hashes of the PDF bytes and the Job Description are concatenated to form a unique key. A Redis cache hit returns the entire analysis in **< 5ms**.
5. **Text Extraction**: On a cache miss, `PyMuPDF` extracts the text. To handle multi-column resumes, page text blocks are sorted top-to-bottom and left-to-right before parsing.
6. **Resume Verification**: The extracted text is validated using `ResumeValidator` to verify it contains sections like experience, education, or skills.
7. **Semantic Embeddings**: The text is encoded using the `all-MiniLM-L6-v2` transformer model to generate 384-dimensional vector embeddings.
8. **ATS Scoring Engine**: Evaluates the resume using four weighted scoring pillars (see below) and generates career guidance data.
9. **Generative Processing**: Connects to the Groq API (LLaMA models) to output customized cover letters, outreach drafts, negotiation scripts, and custom gap projects.
10. **Cache Write & Return**: The response is saved in Redis with a TTL and returned as a JSON payload.

---

## 5. The ATS Scoring Engine Algorithm

The overall score is a weighted value out of 100, calculated using the following four pillars:

$$\text{Overall ATS Score} = (Keywords \times 0.40) + (Semantic Relevance \times 0.15) + (Impact \times 0.25) + (Format \& Tone \times 0.20)$$

### 5.1 Keyword & Skill Match (40% Weight)
* **Extraction**: Programmatically parses Job Descriptions using spaCy to extract nouns/proper nouns, filtered against stop words and a curated `SKILLS_WHITELIST` (e.g., Python, AWS, Docker).
* **Point Allocation Rules**:
  - **Exact/Flexible Match (10 Points)**: RegEx matching of base words (e.g., "React" matches "reactjs", "react").
  - **Synonym Match (7 Points)**: Pre-mapped synonym lookup (e.g., "AWS" matches "Amazon Web Services", "EC2", "S3").
  - **Hybrid Semantic Match (6 Points)**: Checks for word overlap and substring containment within spaCy noun chunks (e.g., "React" matches "React Native Architecture").
  - **Partial Match (4 Points)**: Matches parts of multi-word skills.
* **Formula**: The raw matching score is scaled using a non-linear S-curve ($Score^{0.8}$) to distinguish between average match profiles and high-relevance matches.

### 5.2 Semantic Relevance (15% Weight)
* **Embedding**: Resumes and Job Descriptions are converted into dense vector spaces.
* **Comparison**: Computes the Cosine Similarity (dot product of L2-normalized vectors) using NumPy.
* **Mapping**: Cosine similarity values (typically 0.5 to 0.8) are mapped non-linearly to a 0-100 scale: 
  $$\text{Semantic Mapped Score} = \min(100, (\text{Cosine Similarity})^{1.5} \times 1.3 \times 100)$$

### 5.3 Content Impact Quality (25% Weight)
Analyzes resume content to determine if the candidate lists duties or achievements.
* **Action Verbs (30% of Impact)**: Scans for high-impact verbs (e.g., *engineered, optimized, automated, spearheaded*), awarding 6 points per unique verb (max 30).
* **Quantified Results (45% of Impact)**: Detects metrics, percentages, and currencies (e.g., *40%, $1.2M, 15 clients*), awarding 15 points per metric (max 45).
* **Power Words (25% of Impact)**: Detects excellence indicators (e.g., *promoted, certified, exceeded*), awarding 5 points per word (max 25).
* **Deduction**: Presence of weak, passive phrases (e.g., *responsible for, assisted*) reduces the overall impact ratio.

### 5.4 Formatting & Technical Parsability (20% Weight)
Evaluates layout parsability for legacy applicant tracking systems.
* **Base Score**: 100 points, subject to structural deductions:
  - **Tables Detected**: **-25 points** (tables break text flow in standard parsers).
  - **Multi-Column Layout**: **-15 points** (results in jumbled left-to-right reading).
  - **Low Text Density**: **-15 points** (less than 500 characters signals an image-only scan).
  - **Excessive Images/Graphics**: **-10 points** (more than 2 images).
  - **Tiny Font Size**: **-10 points** (font size below 8.5pt).
  - **Special Character Density**: **-30 points** (excessive non-ASCII characters or custom bullet symbols).
  - **Section Integrity**: Awards 20 points per standard section detected (*Experience, Education, Skills, Contact, Summary*).

---

## 6. Advanced Platform Features

1. **Intelligent Gap Roadmapping**: Identifies missing critical skills and generates custom project ideas with specs (e.g., "Build a CI/CD pipeline using GitHub Actions" to learn DevOps).
2. **Authenticity & Plagiarism Scanner**: Scans for copy-pasted Job Description sentences (verbatim phrases deduct 15 points each) and checks if the resume matches the JD too closely (>82% semantic overlap is flagged as a spam risk).
3. **Asynchronous Task Offloading**: If request processing exceeds **10 seconds**, the use case returns a `202 Accepted` status with a polling URL (e.g., `/status/{job_id}`). A background worker processes the job, storing results in the Database/Redis.
4. **GDPR Compliance (Article 17)**: A dedicated `DELETE /gdpr/delete/{trace_id}` endpoint permanently wipes all cached reports, traces, and customer metadata, fulfilling the right-to-erasure.
5. **PII Obfuscation**: Hashing algorithms run over email addresses, phone numbers, and names within structured application logs to prevent data leaks.

---

## 7. GCP Infrastructure & Production CI/CD Setup

### 7.1 Infrastructure (Terraform)
* **GCP Cloud Run**: Containerized backend hosted with autoscaling configurations (min 1 instance to avoid cold-start lag, max 10 instances).
* **Cloud Memorystore (Redis)**: Managed Redis instance inside a private VPC.
* **Secret Manager**: Secure runtime environment variable injections (API keys, salts, database credentials).
* **Cloud Load Balancer**: External HTTP/HTTPS load balancer managing SSL certificates and domain mappings.

### 7.2 Deployment (GitHub Actions CI/CD)
* **Linting & Formatting**: Enforces code styling with `ruff check` and `ruff format`.
* **Testing SLA**: Real Redis and ClamAV containers spin up in GitHub Actions runners. Pytest runs integration checks, requiring a **95% minimum coverage** to pass.
* **Security & Build**: Builds a lightweight **distroless** Docker image (<150MB), runs security vulnerability scans with **Trivy**, and deploys to GCP Cloud Run using **Workload Identity Federation (WIF)** (no long-lived JSON keys stored in secrets).
