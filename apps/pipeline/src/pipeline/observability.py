"""OpenTelemetry wiring for Langfuse.

pydantic-ai's Instrumentation capability uses the global OTel TracerProvider when
none is passed explicitly (see InstrumentationSettings), so configuring one here
and calling Agent.instrument_all() once per process is enough to trace every
agent — no per-agent wiring in filter/llm.py or enrich/llm.py.

No-ops when LANGFUSE_* settings are empty, so the pipeline keeps working without
Langfuse running.
"""

from __future__ import annotations

import base64
import logging

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from pipeline.config import Settings
from pydantic_ai import Agent

logger = logging.getLogger(__name__)

_configured = False


def configure_tracing(configuration: Settings) -> None:
    """Point pydantic-ai's OpenTelemetry instrumentation at Langfuse. Idempotent."""
    global _configured
    if _configured:
        return
    _configured = True

    endpoint = configuration.langfuse_otel_endpoint
    public_key = configuration.langfuse_public_key
    secret_key = configuration.langfuse_secret_key
    if not (endpoint and public_key and secret_key):
        logger.info("Langfuse tracing disabled: LANGFUSE_* settings not configured")
        return

    credentials = base64.b64encode(f"{public_key}:{secret_key}".encode()).decode()
    exporter = OTLPSpanExporter(
        # An explicit `endpoint=` is used verbatim by this exporter (no auto
        # "/v1/traces" suffix — that only happens when it falls back to the
        # generic OTEL_EXPORTER_OTLP_ENDPOINT env var), so append it ourselves.
        endpoint=f"{endpoint.rstrip('/')}/v1/traces",
        headers={"Authorization": f"Basic {credentials}"},
    )
    provider = TracerProvider(resource=Resource.create({"service.name": "skillpolaris-pipeline"}))
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    Agent.instrument_all(True)
    logger.info("Langfuse tracing enabled: endpoint=%s", endpoint)
