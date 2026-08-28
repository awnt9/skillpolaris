"""Enrich flow: canonical_jobs (pending) → Postgres metadata."""

from __future__ import annotations

from pipeline.tasks.enrich import enrich_task, recompute_role_stats_task
from prefect import flow, get_run_logger


@flow(name="enrich-jobs", log_prints=True)
def enrich_flow() -> dict[str, int]:
    """Extract structured metadata from pending canonical_jobs into Postgres,
    then refresh the precomputed role/skill matching statistics."""
    logger = get_run_logger()
    result = enrich_task()
    logger.info("Enrich flow finished: %s", result)

    stats_result = recompute_role_stats_task()
    logger.info("Role stats refresh finished: %s", stats_result)

    return result


if __name__ == "__main__":
    enrich_flow()
