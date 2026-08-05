"""Feed sources: pull batches until exhausted or budget is reached."""

from __future__ import annotations

from pipeline.schemas.extract import ExtractRunResult
from pipeline.storage.postgres import PostgresManager
from pipeline.tasks.extract.rate_limit import SourceRateLimiter
from pipeline.tasks.extract.registry import ExtractorRegistry


def run_feed_extract(
    *,
    store: PostgresManager,
    registry: ExtractorRegistry,
    rate_limiter: SourceRateLimiter,
    result: ExtractRunResult,
    max_batches_per_source: int = 10,
) -> None:
    for source_name, extractor in registry.feed.items():
        policy = registry.policy_for(source_name)
        cursor: str | None = None

        for _ in range(max_batches_per_source):
            rate_limiter.wait(source_name, policy.min_interval_seconds)
            try:
                batch = extractor.fetch_batch(cursor=cursor)
            except Exception:  # noqa: BLE001 — per-batch boundary
                result.failed += 1
                break

            for payload in batch.records:
                try:
                    raw_job = extractor.to_raw_job(payload)
                    store.save_raw_job(raw_job=raw_job)
                    result.saved += 1
                except Exception:  # noqa: BLE001 — per-offer boundary
                    result.failed += 1

            if not batch.next_cursor:
                break
            cursor = batch.next_cursor
