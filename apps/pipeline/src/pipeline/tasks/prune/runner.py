"""Prune runner: drop canonical_jobs past CANONICAL_JOB_MAX_AGE_DAYS.

Keeps role_skill_stats/role_stats a rolling reflection of recent market
demand instead of accumulating months-old postings forever — recomputing
those tables is the caller's job (see flows.prune), not this task's, since
it's shared with the enrich flow (tasks.enrich.runner.recompute_role_stats_task).
"""

from __future__ import annotations

from pipeline.config import Settings, get_configuration
from pipeline.storage.postgres import PostgresManager
from prefect import get_run_logger, task


def run_prune(configuration: Settings) -> dict[str, int]:
    logger = get_run_logger()

    with PostgresManager(configuration) as store:
        deleted = store.delete_stale_canonical_jobs(configuration.canonical_job_max_age_days)

    logger.info(
        "Pruned canonical_jobs older than %s days: deleted=%s",
        configuration.canonical_job_max_age_days,
        deleted,
    )
    return {"deleted": deleted}


@task(name="prune", retries=1)
def prune_stale_jobs_task() -> dict[str, int]:
    configuration = get_configuration()
    return run_prune(configuration)
