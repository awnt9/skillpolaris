"""Sync keyword providers into the search_keywords catalog."""

from __future__ import annotations

from pipeline.config import Settings, get_configuration
from pipeline.storage.postgres import PostgresManager
from pipeline.tasks.keywords.providers.arbeitnow import ArbeitnowKeywordProvider
from pipeline.tasks.keywords.providers.base import KeywordProvider
from pipeline.tasks.keywords.providers.esco import EscoKeywordProvider
from pipeline.tasks.keywords.providers.esco_programming import EscoProgrammingProvider
from pipeline.tasks.keywords.providers.himalayas import HimalayasCategoryProvider
from pipeline.tasks.keywords.providers.jobicy import JobicyIndustryProvider
from pipeline.tasks.keywords.providers.landing_jobs import LandingJobsKeywordProvider
from pipeline.tasks.keywords.providers.manual import ManualKeywordProvider
from pipeline.tasks.keywords.providers.remoteok import RemoteOkTagProvider
from pipeline.tasks.keywords.providers.remotive import RemotiveKeywordProvider
from pipeline.tasks.keywords.providers.stackoverflow import StackOverflowTagProvider
from pipeline.tasks.keywords.providers.the_muse import TheMuseKeywordProvider
from prefect import get_run_logger, task


def build_keyword_providers(
    esco_groups: list[int] | None = None,
    *,
    include_manual: bool = True,
    so_pages: int = 2,
    so_min_count: int = 50_000,
    so_api_key: str | None = None,
) -> list[KeywordProvider]:
    providers: list[KeywordProvider] = [
        EscoKeywordProvider(group_codes=esco_groups),
        EscoProgrammingProvider(),
        StackOverflowTagProvider(
            pages=so_pages,
            min_count=so_min_count,
            api_key=so_api_key,
        ),
        RemoteOkTagProvider(),
        RemotiveKeywordProvider(),
        ArbeitnowKeywordProvider(),
        HimalayasCategoryProvider(),
        JobicyIndustryProvider(),
        LandingJobsKeywordProvider(),
        TheMuseKeywordProvider(),
    ]
    if include_manual:
        # Last so role seeds do not get origin-overwritten by SO on conflict.
        providers.append(ManualKeywordProvider())
    return providers


def run_keyword_sync(
    configuration: Settings,
    esco_groups: list[int] | None = None,
) -> dict[str, int]:
    so_key = (configuration.so_api_key or "").strip() or None
    providers = build_keyword_providers(
        esco_groups=esco_groups,
        so_pages=configuration.so_tag_pages,
        so_min_count=configuration.so_min_count,
        so_api_key=so_key,
    )
    total_upserted = 0

    with PostgresManager(configuration) as store:
        for provider in providers:
            keywords = provider.collect()
            total_upserted += store.upsert_search_keywords(keywords)
        store.refresh_keyword_raw_jobs_counts()

    return {"providers": len(providers), "upserted": total_upserted}


@task(name="sync-keywords", retries=1)
def sync_keywords_task(esco_groups: list[int] | None = None) -> dict[str, int]:
    logger = get_run_logger()
    configuration = get_configuration()
    result = run_keyword_sync(configuration, esco_groups=esco_groups)
    logger.info(
        "Keyword sync finished. providers=%s upserted=%s",
        result["providers"],
        result["upserted"],
    )
    return result
