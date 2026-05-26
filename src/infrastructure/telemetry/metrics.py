"""Infrastructure: Prometheus metrics definitions.

All metrics are registered at module import time (singleton pattern).
Exported via /metrics endpoint (prometheus_client WSGI middleware).
"""
from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram

# ── Request latency (SLA: p95 < 800ms, p99 < 2s) ─────────────────────────────
ATS_REQUEST_LATENCY = Histogram(
    "ats_request_latency_seconds",
    "End-to-end request latency for /v1/analyze",
    buckets=[0.05, 0.1, 0.25, 0.5, 0.8, 1.0, 1.5, 2.0, 5.0, 10.0],
)

# ── PDF extraction failures ───────────────────────────────────────────────────
ATS_PDF_EXTRACT_FAIL = Counter(
    "ats_pdf_extract_fail_total",
    "Total number of PDF text extraction failures",
)

# ── Cache hit/miss counters (ratio computed in dashboards) ───────────────────
ATS_CACHE_HITS = Counter(
    "ats_cache_hit_total",
    "Total cache hits for scored results",
)
ATS_CACHE_MISSES = Counter(
    "ats_cache_miss_total",
    "Total cache misses (full pipeline executed)",
)

# ── Circuit breaker state ─────────────────────────────────────────────────────
ATS_CIRCUIT_BREAKER_OPEN = Gauge(
    "ats_circuit_breaker_open",
    "1 when MiniLM circuit breaker is open (TF-IDF fallback active)",
)

# ── Malware detections ───────────────────────────────────────────────────────
ATS_MALWARE_DETECTED = Counter(
    "ats_malware_detected_total",
    "Total PDFs rejected by ClamAV scanner",
)

# ── Rate limit violations ─────────────────────────────────────────────────────
ATS_RATE_LIMIT_EXCEEDED = Counter(
    "ats_rate_limit_exceeded_total",
    "Total requests rejected due to daily rate limit",
)
