"""Extract: read keywords from Postgres, call sources, save raw_jobs."""

from __future__ import annotations

from pipeline.config import Settings
from pipeline.schemas.extract import ExtractRunResult
from pipeline.storage.postgres import PostgresManager
from pipeline.tasks.extract.rate_limit import SourceRateLimiter
from pipeline.tasks.extract.registry import build_extractor_registry
from pipeline.tasks.extract.runners.ats_runner import run_ats_extract
from pipeline.tasks.extract.runners.detail_runner import run_detail_extract
from pipeline.tasks.extract.runners.feed_runner import run_feed_extract
from pipeline.tasks.extract.sources.base import parse_board_tokens
from prefect import get_run_logger


def _default_ats_company_slugs(configuration: Settings) -> dict[str, list[str]]:
    return {
        "greenhouse": parse_board_tokens(configuration.greenhouse_board_tokens),
        "lever": parse_board_tokens(configuration.lever_board_tokens),
        "ashby": parse_board_tokens(configuration.ashby_board_tokens),
        "recruitee": parse_board_tokens(configuration.recruitee_board_tokens),
        "workable": parse_board_tokens(configuration.workable_board_tokens),
        "smartrecruiters": parse_board_tokens(configuration.smartrecruiters_board_tokens),
    }


def run_extract(
    configuration: Settings,
    *,
    ats_company_slugs: dict[str, list[str]] | None = None,
) -> ExtractRunResult:
    logger = get_run_logger()
    registry = build_extractor_registry(configuration)
    rate_limiter = SourceRateLimiter()
    result = ExtractRunResult()
    board_slugs = ats_company_slugs or _default_ats_company_slugs(configuration)

    with PostgresManager(configuration) as store:
        logger.info("Extract phase=detail starting")
        saved_before, failed_before, skipped_before = result.saved, result.failed, result.skipped
        run_detail_extract(
            store=store,
            registry=registry,
            configuration=configuration,
            rate_limiter=rate_limiter,
            result=result,
        )
        logger.info(
            "Extract phase=detail finished saved+=%s failed+=%s skipped+=%s",
            result.saved - saved_before,
            result.failed - failed_before,
            result.skipped - skipped_before,
        )

        logger.info("Extract phase=feed starting")
        saved_before, failed_before, skipped_before = result.saved, result.failed, result.skipped
        run_feed_extract(
            store=store,
            registry=registry,
            configuration=configuration,
            rate_limiter=rate_limiter,
            result=result,
        )
        logger.info(
            "Extract phase=feed finished saved+=%s failed+=%s skipped+=%s",
            result.saved - saved_before,
            result.failed - failed_before,
            result.skipped - skipped_before,
        )

        logger.info("Extract phase=ats starting")
        saved_before, failed_before, skipped_before = result.saved, result.failed, result.skipped
        run_ats_extract(
            store=store,
            registry=registry,
            configuration=configuration,
            rate_limiter=rate_limiter,
            result=result,
            company_slugs=board_slugs,
        )
        logger.info(
            "Extract phase=ats finished saved+=%s failed+=%s skipped+=%s",
            result.saved - saved_before,
            result.failed - failed_before,
            result.skipped - skipped_before,
        )

        store.refresh_keyword_raw_jobs_counts()

    logger.info(
        "Extract run finished. keywords_used=%s saved=%s failed=%s skipped=%s",
        result.keywords_used,
        result.saved,
        result.failed,
        result.skipped,
    )
    return result


def run_extract_summary(configuration: Settings, **kwargs) -> dict[str, int]:
    return run_extract(configuration, **kwargs).model_dump()
