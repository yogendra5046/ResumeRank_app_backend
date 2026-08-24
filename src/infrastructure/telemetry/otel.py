"""Infrastructure: OpenTelemetry setup.

Configures OTLP gRPC exporter + FastAPI auto-instrumentation.
JSON structured logs via structlog with PII redaction processor.
"""
from __future__ import annotations

import logging
import re
import uuid

import structlog

# ───────────────────────────────────────────
# OPTIONAL — Wrap ALL OpenTelemetry imports
# ───────────────────────────────────────────
try:
    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    OTEL_AVAILABLE = True
except Exception as e:
    print("[WARN] OpenTelemetry disabled:", e)
    OTEL_AVAILABLE = False

# PII redaction patterns
_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
_PHONE_RE = re.compile(r"\b(\+?\d[\d\s\-().]{7,}\d)\b")


def _redact_pii(value: str) -> str:
    import hashlib

    def hash_match(m: re.Match[str]) -> str:
        return f"[REDACTED:{hashlib.sha256(m.group().encode()).hexdigest()[:8]}]"

    value = _EMAIL_RE.sub(hash_match, value)
    value = _PHONE_RE.sub(hash_match, value)
    return value


def _pii_redaction_processor(
    logger: logging.Logger,
    method: str,
    event_dict: dict[str, object],
) -> dict[str, object]:
    for key, val in event_dict.items():
        if isinstance(val, str):
            event_dict[key] = _redact_pii(val)
    return event_dict


def configure_logging() -> None:
    """Set up structlog with JSON output and PII redaction."""
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            _pii_redaction_processor,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
    )


def configure_tracing(service_name: str, otlp_endpoint: str | None) -> None:
    """Safe OTEL bootstrap — does nothing if OTEL missing."""
    if not OTEL_AVAILABLE:
        print("[WARN] configure_tracing skipped (no OTEL)")
        return

    resource = Resource.create({"service.name": service_name, "service.version": "1.0.0"})
    provider = TracerProvider(resource=resource)

    if otlp_endpoint:
        try:
            exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
            provider.add_span_processor(BatchSpanProcessor(exporter))
        except Exception as e:
            print("[WARN] Failed to init OTLP exporter:", e)

    trace.set_tracer_provider(provider)


def instrument_app(app: object) -> None:
    """FastAPI instrumentation — optional."""
    if not OTEL_AVAILABLE:
        print("[WARN] instrument_app skipped (no OTEL)")
        return
    try:
        FastAPIInstrumentor.instrument_app(app)  # type: ignore[arg-type]
    except Exception as e:
        print("[WARN] Failed to instrument FastAPI:", e)


def new_trace_id() -> str:
    return str(uuid.uuid4())