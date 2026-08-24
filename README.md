# ResumeRank Pro

Production ATS backend + Flutter SDK. Google L5 quality.

## Architecture

```
Hexagonal Architecture
backend/src/
  domain/         ← Pure business logic. Zero I/O. Zero framework deps.
  application/    ← Use cases. Orchestrates ports. No HTTP here.
  infrastructure/ ← Adapters: PyMuPDF, MiniLM INT8, Redis, ClamAV, ESCO graph.
  presentation/   ← FastAPI routes. Thin. No logic. DI via dependencies.py.
```

## Quick Start (Local)

```bash
# Generate ESCO fixture (CI fallback)
cd backend && python scripts/generate_esco_fixture.py

# Start full stack
docker compose up

# Test
curl -X POST http://localhost:8080/v1/analyze \
  -H "X-API-Key: your-key" \
  -F "resume=@path/to/resume.pdf" \
  -F "job_description=Senior Python engineer needed..."
```

## Performance SLA

| Metric | Target | Mechanism |
|--------|--------|-----------|
| p95 latency | < 800ms | INT8 MiniLM + FAISS + Redis cache |
| p99 latency | < 2s | Async pipeline + thread pools |
| Cache hit | < 50ms | Redis hiredis + sha256 keying |
| >10s requests | 202 + poll | Async job store (ULID IDs) |

## Security

- **Auth**: `X-API-Key` → SHA-256 hashed, 100/day Redis rate limit
- **Scan**: ClamAV on all PDF bytes before parsing (fail-closed)
- **PII**: Email/phone regex-hashed in all structured logs
- **GDPR**: `DELETE /gdpr/delete/{trace_id}` erases all cached data

## Scoring Formula

```
final = 0.5 × cosine_similarity
      + 0.3 × esco_skill_graph_weight
      + 0.1 × impact_verb_score
      + 0.1 × format_score
```

## Flutter SDK

```dart
import 'package:resumerank_sdk/resumerank_sdk.dart';

final client = ResumeRankClient(apiKey: 'your-key');
final result = await client.analyze(File('resume.pdf'), jobDescription);
print('${result.finalScore} (${result.grade})');
```

## CI/CD

`lint → test (95% coverage) → docker build → trivy scan → deploy Cloud Run`

## Deployment

```bash
cd terraform
terraform init
terraform apply \
  -var="project_id=my-gcp-project" \
  -var="domain=api.resumerank.pro" \
  -var="container_image=gcr.io/my-project/resumerank-backend:sha" \
  -var="api_key_salt=$(openssl rand -hex 32)"
```
