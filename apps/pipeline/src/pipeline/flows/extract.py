"""Extract flow: sources → raw_jobs."""

from __future__ import annotations

from pipeline.tasks.extract.task import extract_task
from prefect import flow, get_run_logger


@flow(name="extract-jobs", log_prints=True)
def extract_flow(
    ats_company_slugs: dict[str, list[str]] | None = None,
) -> dict[str, int]:
    """Pull new offers into raw_jobs (filter_status=pending)."""
    logger = get_run_logger()
    result = extract_task(ats_company_slugs=ats_company_slugs)
    logger.info("Extract flow finished: %s", result)
    return result


if __name__ == "__main__":
    extract_flow()
