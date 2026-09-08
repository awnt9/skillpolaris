"""Prune flow: drop stale canonical_jobs, then refresh role/skill stats."""

from __future__ import annotations

from pipeline.tasks.enrich import recompute_role_stats_task
from pipeline.tasks.prune import prune_stale_jobs_task
from prefect import flow, get_run_logger


@flow(name="prune-jobs", log_prints=True)
def prune_stale_jobs_flow() -> dict[str, int]:
    logger = get_run_logger()
    result = prune_stale_jobs_task()
    logger.info("Prune flow finished: %s", result)

    stats_result = recompute_role_stats_task()
    logger.info("Role stats refresh finished: %s", stats_result)

    return result


if __name__ == "__main__":
    prune_stale_jobs_flow()
