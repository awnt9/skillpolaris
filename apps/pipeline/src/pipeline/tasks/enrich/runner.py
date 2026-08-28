"""Enrich runner: canonical job text → relational metadata in Postgres."""

from __future__ import annotations

from pipeline.config import Settings, get_configuration
from pipeline.storage.postgres import PostgresManager
from pipeline.tasks.enrich.llm import MetadataExtractor
from pipeline.tasks.enrich.stats import compute_role_stats
from prefect import get_run_logger, task


def run_enrich(configuration: Settings) -> dict[str, int]:
    logger = get_run_logger()

    extractor = MetadataExtractor(
        base_url=configuration.llm_base_url,
        api_key=configuration.llm_api_key,
        model=configuration.llm_model,
    )

    processed = 0
    failed = 0

    with PostgresManager(configuration) as store:
        pending = store.get_pending_canonical_jobs(limit=configuration.enrich_batch_size)
        logger.info(
            "Enrich batch: pending=%s limit=%s model=%s",
            len(pending),
            configuration.enrich_batch_size,
            configuration.llm_model,
        )

        for canonical_job in pending:
            try:
                metadata = extractor.extract(
                    title=canonical_job.title,
                    description=canonical_job.description,
                )
                store.save_job_enrichment(canonical_job.id, metadata)
                processed += 1
                logger.info(
                    "Enrich ok id=%s source=%s role=%s skills=%s",
                    canonical_job.id,
                    canonical_job.source,
                    metadata.standard_role.value,
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
