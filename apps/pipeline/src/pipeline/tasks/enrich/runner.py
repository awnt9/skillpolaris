"""Enrich runner: canonical job text → relational metadata in Postgres.

Extraction calls are I/O-bound, so the batch runs them concurrently, bounded
by `LLM_MAX_CONCURRENCY`; Postgres writes stay synchronous and sequential in
the original pending-list order once every call has resolved.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

from pipeline.config import Settings, get_configuration
from pipeline.observability import configure_tracing
from pipeline.schemas.enrich import JobOfferMetadata
from pipeline.storage.postgres import PostgresManager
from pipeline.tasks.enrich.llm import MetadataExtractor
from pipeline.tasks.enrich.stats import compute_role_stats
from prefect import get_run_logger, task


@dataclass
class _ExtractOutcome:
    metadata: JobOfferMetadata | None
    error: Exception | None


async def _extract_all(
    extractor: MetadataExtractor,
    canonical_jobs: list,
    max_concurrency: int,
    logger,
) -> dict[int, _ExtractOutcome]:
    """Run extraction concurrently, logging progress as each call resolves —
    otherwise the whole concurrent phase is silent until the batch finishes."""
    semaphore = asyncio.Semaphore(max_concurrency)
    total = len(canonical_jobs)
    done = 0

    async def _one(canonical_job) -> tuple[int, _ExtractOutcome]:
        nonlocal done
        async with semaphore:
            try:
                metadata = await extractor.extract_async(
                    title=canonical_job.title,
                    description=canonical_job.description,
                )
                done += 1
                logger.info(
                    "Enrich llm progress %s/%s id=%s role=%s",
                    done,
                    total,
                    canonical_job.id,
                    metadata.standard_role,
                )
                return canonical_job.id, _ExtractOutcome(metadata=metadata, error=None)
            except Exception as exc:  # noqa: BLE001 — per-offer boundary
                done += 1
                logger.warning(
                    "Enrich llm progress %s/%s id=%s failed: %s",
                    done,
                    total,
                    canonical_job.id,
                    exc,
                )
                return canonical_job.id, _ExtractOutcome(metadata=None, error=exc)

    results = await asyncio.gather(*(_one(job) for job in canonical_jobs))
    return dict(results)


def run_enrich(configuration: Settings) -> dict[str, int]:
    logger = get_run_logger()
    configure_tracing(configuration)

    processed = 0
    failed = 0

    with PostgresManager(configuration) as store:
        roles = store.get_active_standard_roles()
        extractor = MetadataExtractor(
            base_url=configuration.llm_base_url,
            api_key=configuration.llm_api_key,
            model=configuration.llm_model,
            roles=roles,
        )

        pending = store.get_pending_canonical_jobs(limit=configuration.enrich_batch_size)
        logger.info(
            "Enrich batch: pending=%s limit=%s model=%s",
            len(pending),
            configuration.enrich_batch_size,
            configuration.llm_model,
        )

        outcomes = asyncio.run(
            _extract_all(extractor, pending, configuration.llm_max_concurrency, logger)
        )

        for canonical_job in pending:
            try:
                outcome = outcomes[canonical_job.id]
                if outcome.error is not None:
                    raise outcome.error
                metadata = outcome.metadata
                assert metadata is not None

                store.save_job_enrichment(canonical_job.id, metadata)
                processed += 1
                logger.info(
                    "Enrich ok id=%s source=%s role=%s skills=%s",
                    canonical_job.id,
                    canonical_job.source,
                    metadata.standard_role,
                    len(metadata.hard_skills),
                )
            except Exception:  # noqa: BLE001 — per-offer boundary
                logger.exception(
                    "Enrich failed for canonical_job id=%s source=%s job_id=%s",
                    canonical_job.id,
                    canonical_job.source,
                    canonical_job.job_id,
                )
                try:
                    store.mark_canonical_failed(canonical_job.id)
                except Exception:  # noqa: BLE001
                    logger.exception(
                        "Could not mark canonical_job id=%s as failed",
                        canonical_job.id,
                    )
                failed += 1

    return {"pending": len(pending), "processed": processed, "failed": failed}


@task(name="enrich", retries=1)
def enrich_task() -> dict[str, int]:
    logger = get_run_logger()
    configuration = get_configuration()
    result = run_enrich(configuration)
    logger.info(
        "Enrich finished. pending=%s processed=%s failed=%s",
        result["pending"],
        result["processed"],
        result["failed"],
    )
    return result


def run_recompute_role_stats(configuration: Settings) -> dict[str, int]:
    logger = get_run_logger()

    with PostgresManager(configuration) as store:
        jobs = store.get_enrich_snapshot()
        skill_weights, role_aggregates = compute_role_stats(jobs)
        store.replace_role_stats(skill_weights, role_aggregates)

    logger.info(
        "Role stats recomputed. jobs=%s roles=%s role_skill_pairs=%s",
        len(jobs),
        len(role_aggregates),
        len(skill_weights),
    )
    return {
        "jobs": len(jobs),
        "roles": len(role_aggregates),
        "role_skill_pairs": len(skill_weights),
    }


@task(name="recompute-role-stats", retries=1)
def recompute_role_stats_task() -> dict[str, int]:
    configuration = get_configuration()
    return run_recompute_role_stats(configuration)
