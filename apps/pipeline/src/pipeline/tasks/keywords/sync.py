"""Sync keyword providers into the search_keywords catalog."""

from __future__ import annotations

import time

from pipeline.config import Settings, get_configuration
from pipeline.storage.postgres import PostgresManager
from pipeline.tasks.keywords.providers.arbeitnow import ArbeitnowKeywordProvider
from pipeline.tasks.keywords.providers.base import KeywordProvider
from pipeline.tasks.keywords.providers.himalayas import HimalayasCategoryProvider
from pipeline.tasks.keywords.providers.jobicy import JobicyIndustryProvider
from pipeline.tasks.keywords.providers.landing_jobs import LandingJobsKeywordProvider
from pipeline.tasks.keywords.providers.remoteok import RemoteOkTagProvider
from pipeline.tasks.keywords.providers.remotive import RemotiveKeywordProvider
from pipeline.tasks.keywords.providers.the_muse import TheMuseKeywordProvider
from prefect import get_run_logger, task


def build_keyword_providers() -> list[KeywordProvider]:
    return [
        RemoteOkTagProvider(),
        RemotiveKeywordProvider(),
        ArbeitnowKeywordProvider(),
        HimalayasCategoryProvider(),
        JobicyIndustryProvider(),
        LandingJobsKeywordProvider(),
        TheMuseKeywordProvider(),
    ]


def run_keyword_sync(configuration: Settings) -> dict[str, int]:
    logger = get_run_logger()
    providers = build_keyword_providers()
    total_upserted = 0
    all_new_keywords: list[str] = []
    failed_origins: list[str] = []

    with PostgresManager(configuration) as store:
        for provider in providers:
            origin = provider.origin
            started = time.perf_counter()
            logger.info("Keyword sync: provider=%s starting", origin)

            try:
                keywords = provider.collect()
            except Exception:
                logger.exception("Keyword sync: provider=%s collect failed, skipping", origin)
                failed_origins.append(origin)
                continue

            elapsed = time.perf_counter() - started
            result = store.upsert_search_keywords(keywords)
            total_upserted += result.upserted
            all_new_keywords.extend(result.new_keywords)
            logger.info(
                "Keyword sync: provider=%s collected=%s upserted=%s new=%s elapsed=%.2fs",
                origin,
                len(keywords),
                result.upserted,
                len(result.new_keywords),
                elapsed,
            )
            if result.new_keywords:
                logger.info(
                    "Keyword sync: provider=%s new_keywords=%s",
                    origin,
                    result.new_keywords,
                )

    if failed_origins:
        logger.warning("Keyword sync: providers failed=%s", failed_origins)

    if all_new_keywords:
        logger.info("Keyword sync: new_keywords=%s", all_new_keywords)

    return {
        "providers": len(providers),
        "upserted": total_upserted,
        "new": len(all_new_keywords),
        "failed": len(failed_origins),
    }


@task(name="sync-keywords", retries=1)
def sync_keywords_task() -> dict[str, int]:
    logger = get_run_logger()
    configuration = get_configuration()
    result = run_keyword_sync(configuration)
    logger.info(
        "Keyword sync finished. providers=%s upserted=%s new=%s failed=%s",
        result["providers"],
        result["upserted"],
        result["new"],
        result["failed"],
    )
    return result
