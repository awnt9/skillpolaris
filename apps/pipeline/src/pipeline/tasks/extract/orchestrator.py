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


def run_extract(
    configuration: Settings,
    *,
    ats_company_slugs: list[str] | None = None,
) -> ExtractRunResult:
    registry = build_extractor_registry(configuration)
    rate_limiter = SourceRateLimiter()
    result = ExtractRunResult()

    with PostgresManager(configuration) as store:
        run_detail_extract(
            store=store,
            registry=registry,
            configuration=configuration,
            rate_limiter=rate_limiter,
            result=result,
        )
        run_feed_extract(
            store=store,
            registry=registry,
            rate_limiter=rate_limiter,
            result=result,
        )
        run_ats_extract(
            store=store,
            registry=registry,
            rate_limiter=rate_limiter,
            result=result,
            company_slugs=ats_company_slugs or [],
        )

    return result


def run_extract_summary(configuration: Settings, **kwargs) -> dict[str, int]:
    return run_extract(configuration, **kwargs).model_dump()
