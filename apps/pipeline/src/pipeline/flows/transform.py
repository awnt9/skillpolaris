"""Transform flow: canonical_jobs (pending) → Qdrant."""

from __future__ import annotations

from pipeline.tasks.transform import transform_task
from prefect import flow, get_run_logger


@flow(name="transform-jobs", log_prints=True)
def transform_flow() -> dict[str, int]:
    """Embed and upsert pending canonical_jobs."""
    logger = get_run_logger()
    result = transform_task()
    logger.info("Transform flow finished: %s", result)
    return result


if __name__ == "__main__":
    transform_flow()
