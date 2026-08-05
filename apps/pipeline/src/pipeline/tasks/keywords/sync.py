"""Sync keyword providers into the search_keywords catalog."""

from __future__ import annotations

from pipeline.config import Settings, get_configuration
from pipeline.storage.postgres import PostgresManager
from pipeline.tasks.keywords.providers.base import KeywordProvider
from pipeline.tasks.keywords.providers.esco import EscoKeywordProvider
from prefect import get_run_logger, task


def build_keyword_providers(
    esco_groups: list[int] | None = None,
) -> list[KeywordProvider]:
    return [
        EscoKeywordProvider(group_codes=esco_groups),
    ]


def run_keyword_sync(
    configuration: Settings,
    esco_groups: list[int] | None = None,
) -> dict[str, int]:
    providers = build_keyword_providers(esco_groups=esco_groups)
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
