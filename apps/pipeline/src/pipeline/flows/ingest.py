"""End-to-end ingest flow: extract → filter → transform."""

from __future__ import annotations

from pipeline.tasks.extract import extract_task
from pipeline.tasks.filter import filter_task
from pipeline.tasks.transform import transform_task
from prefect import flow, get_run_logger


@flow(name="ingest-jobs", log_prints=True)
def ingest_flow(esco_groups: list[int] | None = None) -> dict[str, dict[str, int]]:
    """
    Run the full pipeline with a durable checkpoint after each stage.

    raw_jobs → canonical_jobs → Qdrant
    """
    logger = get_run_logger()

    extract_result = extract_task(esco_groups=esco_groups)
    # filter_result = filter_task()
    # transform_result = transform_task()

    summary = {
        "extract": extract_result,
        # "filter": filter_result,
        # "transform": transform_result,
    }
    logger.info("Ingest finished: %s", summary)
    return summary


if __name__ == "__main__":
    ingest_flow()
