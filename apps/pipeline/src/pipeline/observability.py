"""Langfuse wiring for pydantic-ai tracing.

Raw OTel export (a plain TracerProvider + OTLPSpanExporter) is not enough:
self-hosted Langfuse only recognizes a trace's root span as such when it is
created through the official Langfuse SDK, not a bare third-party OTel span
with no parent. So the Langfuse client below owns the global TracerProvider,
and each call site wraps its pydantic-ai agent run in `start_root_span()` to
produce that SDK-marked root; pydantic-ai's own auto-instrumentation
(`Agent.instrument_all`) then attaches its spans as children through normal
OTel context propagation.

`score_current_span()` lets the async judge (`tasks/judge/`) attach its
verdict to its own judge trace for visibility in the Langfuse UI — this is
independent of Langfuse's native Evaluators/Rules feature, which does not
reliably trigger on this self-hosted instance (verified: its create-eval-queue
step is never invoked, on both v4.27.0 and v4.30.0).

No-ops when LANGFUSE_* settings are empty, so the pipeline keeps working
without Langfuse running.
"""

from __future__ import annotations

import contextlib
import logging
from typing import Any, Iterator

from langfuse import Langfuse
from pipeline.config import Settings
from pydantic_ai import Agent

logger = logging.getLogger(__name__)

_configured = False
_client: Langfuse | None = None


def configure_tracing(configuration: Settings) -> None:
    """Point pydantic-ai's OpenTelemetry instrumentation at Langfuse. Idempotent."""
    global _configured, _client
    if _configured:
        return
    _configured = True

    endpoint = configuration.langfuse_otel_endpoint
    public_key = configuration.langfuse_public_key
    secret_key = configuration.langfuse_secret_key
    if not (endpoint and public_key and secret_key):
        logger.info("Langfuse tracing disabled: LANGFUSE_* settings not configured")
        return

    # The SDK builds its own OTLP path; it wants the plain host, not the
    # OTel sub-path we otherwise use for the raw exporter.
    base_url = endpoint.rstrip("/").removesuffix("/api/public/otel")
    _client = Langfuse(public_key=public_key, secret_key=secret_key, base_url=base_url)
    Agent.instrument_all(True)
    logger.info("Langfuse tracing enabled: base_url=%s", base_url)


@contextlib.contextmanager
def start_root_span(name: str) -> Iterator[Any | None]:
    """Root span for one pipeline LLM call, explicitly marked by the Langfuse SDK.

    Yields the span so the caller can attach input/output — the Evaluator Rule
    targets this root span (not pydantic-ai's nested child span), so without
    this the judge would see an empty input/output.
    """
    if _client is None:
        yield None
        return
    with _client.start_as_current_observation(as_type="agent", name=name) as span:
        yield span


def score_current_span(*, name: str, value: float, comment: str) -> None:
    """Attach a judge verdict to the currently open root span, if tracing is on."""
    if _client is None:
        return
    _client.score_current_span(name=name, value=value, data_type="NUMERIC", comment=comment)
