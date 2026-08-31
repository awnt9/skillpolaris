"""Detail sources: unscoped page sweep → fetch new IDs → save raw_jobs."""

from __future__ import annotations

from pipeline.config import Settings
from pipeline.schemas.extract import ExtractRunResult
from pipeline.storage.postgres import PostgresManager
from pipeline.tasks.extract.rate_limit import SourceRateLimiter
from pipeline.tasks.extract.registry import ExtractorRegistry
from pipeline.tasks.extract.sources.base import DetailExtractor
from prefect import get_run_logger


def _fetch_and_save(
    extractor: DetailExtractor,
    *,
    job_id: str,
    store: PostgresManager,
) -> bool:
    detail = extractor.fetch_detail(job_id)
    if not detail:
        return False
    raw_job = extractor.to_raw_job(detail, keyword=None)
    return store.save_raw_job(raw_job=raw_job)


def run_detail_extract(
    *,
    store: PostgresManager,
    registry: ExtractorRegistry,
    configuration: Settings,
    rate_limiter: SourceRateLimiter,
    result: ExtractRunResult,
) -> None:
    logger = get_run_logger()
    budget = configuration.max_total_details

    for source_name, extractor in registry.detail.items():
        policy = registry.policy_for(source_name)
        phase_saved = 0
        page = 0
        logger.info(
            "Extract detail: source=%s budget=%s",
            source_name,
            budget,
        )

        while page < configuration.max_depth and phase_saved < budget:
            rate_limiter.wait(source_name, policy.min_interval_seconds)
            raw_ids = extractor.search_ids(page)

            if not raw_ids:
                logger.info(
                    "Extract detail: source=%s page=%s empty",
                    source_name,
                    page,
                )
                break

            new_ids = store.filter_new_job_ids(source_name, raw_ids)
            skipped = len(raw_ids) - len(new_ids)
            logger.info(
                "Extract detail: source=%s page=%s ids=%s new=%s skipped=%s",
                source_name,
                page,
                len(raw_ids),
                len(new_ids),
                skipped,
            )

            page_saved_before = result.saved
            page_failed_before = result.failed
            for job_id in new_ids:
                if phase_saved >= budget:
                    break

                rate_limiter.wait(source_name, policy.min_interval_seconds)
                try:
                    if _fetch_and_save(
                        extractor,
                        job_id=job_id,
                        store=store,
                    ):
                        result.saved += 1
                        phase_saved += 1
                    else:
                        result.failed += 1
                except Exception:  # noqa: BLE001 — per-offer boundary
                    result.failed += 1

            logger.info(
                "Extract detail: source=%s page=%s done "
                "saved+=%s failed+=%s total_saved=%s",
                source_name,
                page,
                result.saved - page_saved_before,
                result.failed - page_failed_before,
                phase_saved,
            )

            if phase_saved >= budget:
                logger.info(
                    "Extract detail: budget reached (saved=%s), stopping",
                    phase_saved,
                )
                break

            page += 1
