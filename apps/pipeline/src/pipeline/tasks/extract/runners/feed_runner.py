"""Feed sources: tag/keyword windows (or a single unscoped sweep) with dedupe."""

from __future__ import annotations

from pipeline.config import Settings
from pipeline.schemas.extract import ExtractRunResult
from pipeline.schemas.jobs import FeedBatch
from pipeline.storage.postgres import PostgresManager
from pipeline.tasks.extract.rate_limit import SourceRateLimiter
from pipeline.tasks.extract.registry import ExtractorRegistry
from pipeline.tasks.extract.sources.base import FeedExtractor
from prefect import get_run_logger


def _run_batch_loop(
    *,
    source_name: str,
    extractor: FeedExtractor,
    keyword: str | None,
    store: PostgresManager,
    rate_limiter: SourceRateLimiter,
    min_interval_seconds: float,
    result: ExtractRunResult,
    phase_saved: int,
    budget: int,
    max_batches: int,
    logger,
) -> int:
    cursor: str | None = None

    for batch_index in range(max_batches):
        if phase_saved >= budget:
            break

        rate_limiter.wait(source_name, min_interval_seconds)
        try:
            batch: FeedBatch = extractor.fetch_batch(cursor=cursor, keyword=keyword)
        except Exception:  # noqa: BLE001 — per-batch boundary
            result.failed += 1
            logger.info(
                "Extract feed: source=%s tag=%r batch=%s fetch failed",
                source_name,
                keyword,
                batch_index,
            )
            break

        candidates = []
        for payload in batch.records:
            try:
                candidates.append(extractor.to_raw_job(payload, keyword=keyword))
            except Exception:  # noqa: BLE001 — per-offer boundary
                result.failed += 1

        raw_ids = [job.external_id for job in candidates]
        new_ids = set(store.filter_new_job_ids(source_name, raw_ids))
        skipped = len(raw_ids) - len(new_ids)
        result.skipped += skipped

        logger.info(
            "Extract feed: source=%s tag=%r batch=%s records=%s "
            "new=%s skipped=%s cursor=%s",
            source_name,
            keyword,
            batch_index,
            len(raw_ids),
            len(new_ids),
            skipped,
            batch.next_cursor or "none",
        )

        batch_saved_before = result.saved
        for raw_job in candidates:
            if raw_job.external_id not in new_ids:
                continue
            if phase_saved >= budget:
                break
            try:
                if store.save_raw_job(raw_job=raw_job):
                    result.saved += 1
                    phase_saved += 1
                else:
                    result.skipped += 1
            except Exception:  # noqa: BLE001 — per-offer boundary
                result.failed += 1

        logger.info(
            "Extract feed: source=%s tag=%r batch=%s done saved+=%s",
            source_name,
            keyword,
            batch_index,
            result.saved - batch_saved_before,
        )

        if not batch.next_cursor or phase_saved >= budget:
            break
        cursor = batch.next_cursor

    return phase_saved


def run_feed_extract(
    *,
    store: PostgresManager,
    registry: ExtractorRegistry,
    configuration: Settings,
    rate_limiter: SourceRateLimiter,
    result: ExtractRunResult,
    max_batches_per_tag: int = 10,
) -> None:
    logger = get_run_logger()
    budget = configuration.max_total_details

    for source_name, extractor in registry.feed.items():
        policy = registry.policy_for(source_name)
        keywords = store.get_keywords_for_extract(
            source_name=source_name,
            limit=configuration.extract_keyword_limit,
            cooldown_hours=configuration.extract_keyword_cooldown_hours,
        )
        logger.info(
            "Extract feed: source=%s tags=%s budget=%s",
            source_name,
            len(keywords),
            budget,
        )

        if not keywords:
            logger.info(
                "Extract feed: source=%s no scoped tags, running unscoped sweep",
                source_name,
            )
            saved_before = result.saved
            failed_before = result.failed
            skipped_before = result.skipped
            _run_batch_loop(
                source_name=source_name,
                extractor=extractor,
                keyword=None,
                store=store,
                rate_limiter=rate_limiter,
                min_interval_seconds=policy.min_interval_seconds,
                result=result,
                phase_saved=0,
                budget=budget,
                max_batches=max_batches_per_tag,
                logger=logger,
            )
            logger.info(
                "Extract feed: source=%s unscoped sweep closed saved+=%s failed+=%s "
                "skipped+=%s",
                source_name,
                result.saved - saved_before,
                result.failed - failed_before,
                result.skipped - skipped_before,
            )
            continue

        phase_saved = 0
        for keyword_row in keywords:
            if phase_saved >= budget:
                logger.info(
                    "Extract feed: budget reached (saved=%s), stopping tags",
                    phase_saved,
                )
                break

            result.keywords_used += 1
            saved_before = result.saved
            failed_before = result.failed
            skipped_before = result.skipped
            logger.info(
                "Extract feed: source=%s tag=%r",
                source_name,
                keyword_row.keyword,
            )

            phase_saved = _run_batch_loop(
                source_name=source_name,
                extractor=extractor,
                keyword=keyword_row.keyword,
                store=store,
                rate_limiter=rate_limiter,
                min_interval_seconds=policy.min_interval_seconds,
                result=result,
                phase_saved=phase_saved,
                budget=budget,
                max_batches=max_batches_per_tag,
                logger=logger,
            )

            store.mark_keyword_searched(keyword_row.id)
            logger.info(
                "Extract feed: source=%s tag=%r closed saved+=%s failed+=%s "
                "skipped+=%s",
                source_name,
                keyword_row.keyword,
                result.saved - saved_before,
                result.failed - failed_before,
                result.skipped - skipped_before,
            )
