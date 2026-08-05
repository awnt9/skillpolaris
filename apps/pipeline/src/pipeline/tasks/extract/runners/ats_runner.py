"""ATS sources: sync all postings for a list of company boards."""

from __future__ import annotations

from pipeline.schemas.extract import ExtractRunResult
from pipeline.storage.postgres import PostgresManager
from pipeline.tasks.extract.rate_limit import SourceRateLimiter
from pipeline.tasks.extract.registry import ExtractorRegistry


def run_ats_extract(
    *,
    store: PostgresManager,
    registry: ExtractorRegistry,
    rate_limiter: SourceRateLimiter,
    result: ExtractRunResult,
    company_slugs: list[str],
) -> None:
    if not company_slugs:
        return

    for source_name, extractor in registry.ats.items():
        policy = registry.policy_for(source_name)

        for slug in company_slugs:
            rate_limiter.wait(source_name, policy.min_interval_seconds)
            try:
                postings = extractor.fetch_board(slug)
            except Exception:  # noqa: BLE001 — per-board boundary
                result.failed += 1
                continue

            for payload in postings:
                try:
                    raw_job = extractor.to_raw_job(payload, company_slug=slug)
                    store.save_raw_job(raw_job=raw_job)
                    result.saved += 1
                except Exception:  # noqa: BLE001 — per-offer boundary
                    result.failed += 1
