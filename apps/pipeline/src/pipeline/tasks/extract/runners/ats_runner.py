"""ATS sources: sync all postings for a list of company boards."""

from __future__ import annotations

from pipeline.config import Settings
from pipeline.schemas.extract import ExtractRunResult
from pipeline.storage.postgres import PostgresManager
from pipeline.tasks.extract.rate_limit import SourceRateLimiter
from pipeline.tasks.extract.registry import ExtractorRegistry
from prefect import get_run_logger


def run_ats_extract(
    *,
    store: PostgresManager,
    registry: ExtractorRegistry,
    configuration: Settings,
    rate_limiter: SourceRateLimiter,
    result: ExtractRunResult,
    company_slugs: list[str],
) -> None:
    logger = get_run_logger()
    budget = configuration.max_total_details

    if not company_slugs:
        logger.info("Extract ats: no company_slugs, skipping")
        return

    if not registry.ats:
        logger.info("Extract ats: no ats extractors registered, skipping")
        return

    for source_name, extractor in registry.ats.items():
        policy = registry.policy_for(source_name)
        phase_saved = 0
        logger.info(
            "Extract ats: source=%s boards=%s budget=%s",
            source_name,
            len(company_slugs),
            budget,
        )

        for slug in company_slugs:
            if phase_saved >= budget:
                logger.info(
                    "Extract ats: budget reached (saved=%s), stopping boards",
                    phase_saved,
                )
                break

            rate_limiter.wait(source_name, policy.min_interval_seconds)
            saved_before = result.saved
            failed_before = result.failed
            skipped_before = result.skipped
            logger.info("Extract ats: source=%s board=%s starting", source_name, slug)

            try:
                postings = extractor.fetch_board(slug)
            except Exception:  # noqa: BLE001 — per-board boundary
                result.failed += 1
                logger.info(
                    "Extract ats: source=%s board=%s fetch failed",
                    source_name,
                    slug,
                )
                continue

            logger.info(
                "Extract ats: source=%s board=%s postings=%s",
                source_name,
                slug,
                len(postings),
            )

            for payload in postings:
                if phase_saved >= budget:
                    break
                try:
                    raw_job = extractor.to_raw_job(payload, company_slug=slug)
                    if store.save_raw_job(raw_job=raw_job):
                        result.saved += 1
                        phase_saved += 1
                    else:
                        result.skipped += 1
                except Exception:  # noqa: BLE001 — per-offer boundary
                    result.failed += 1

            logger.info(
                "Extract ats: source=%s board=%s closed saved+=%s failed+=%s "
                "skipped+=%s",
                source_name,
                slug,
                result.saved - saved_before,
                result.failed - failed_before,
                result.skipped - skipped_before,
            )
