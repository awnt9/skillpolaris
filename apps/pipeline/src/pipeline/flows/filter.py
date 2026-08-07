"""Filter flow: raw_jobs (pending) → canonical_jobs."""

from __future__ import annotations

from pipeline.tasks.filter import filter_task
from prefect import flow, get_run_logger


@flow(name="filter-jobs", log_prints=True)
def filter_flow() -> dict[str, int]:
    """Classify pending raw_jobs into the programmable market."""
    logger = get_run_logger()
    result = filter_task()
    logger.info("Filter flow finished: %s", result)
    return result


if __name__ == "__main__":
    filter_flow()
