"""Detail sources: keyword search → fetch new IDs → save raw_jobs."""

from __future__ import annotations

from pipeline.config import Settings
from pipeline.schemas.extract import ExtractRunResult
from pipeline.storage.postgres import PostgresManager
from pipeline.tasks.extract.rate_limit import SourceRateLimiter
from pipeline.tasks.extract.registry import ExtractorRegistry
from pipeline.tasks.sources.base import DetailExtractor


def _fetch_and_save(
    extractor: DetailExtractor,
    *,
    job_id: str,
    keyword: str,
    store: PostgresManager,
) -> bool:
    detail = extractor.fetch_detail(job_id)
    if not detail:
        return False
    raw_job = extractor.to_raw_job(detail, keyword=keyword)
    store.save_raw_job(raw_job=raw_job)
    return True


def run_detail_extract(
    *,
    store: PostgresManager,
    registry: ExtractorRegistry,
    configuration: Settings,
    rate_limiter: SourceRateLimiter,
    result: ExtractRunResult,
) -> None:
    budget = configuration.max_total_details

    for source_name, extractor in registry.detail.items():
        if result.saved >= budget:
            break

        policy = registry.policy_for(source_name)
        keywords = store.get_keywords_for_extract(
            source_name=source_name,
            limit=configuration.extract_keyword_limit,
            cooldown_hours=configuration.extract_keyword_cooldown_hours,
        )

        for keyword_row in keywords:
            if result.saved >= budget:
                break

            result.keywords_used += 1
            page = 0

            while page < configuration.max_depth and result.saved < budget:
                rate_limiter.wait(source_name, policy.min_interval_seconds)
                raw_ids = extractor.search_ids(keyword_row.keyword, page)

                if not raw_ids:
                    break

                new_ids = store.filter_new_job_ids(source_name, raw_ids)
                if raw_ids and not new_ids:
                    page += 1
                    continue

                for job_id in new_ids:
                    if result.saved >= budget:
                        break

                    rate_limiter.wait(source_name, policy.min_interval_seconds)
                    try:
                        if _fetch_and_save(
                            extractor,
                            job_id=job_id,
                            keyword=keyword_row.keyword,
                            store=store,
                        ):
                            result.saved += 1
                        else:
                            result.failed += 1
                    except Exception:  # noqa: BLE001 — per-offer boundary
                        result.failed += 1

                break

            store.mark_keyword_searched(keyword_row.id)