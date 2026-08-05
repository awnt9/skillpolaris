"""End-to-end ingest flow: extract → filter → transform."""

from __future__ import annotations

from pipeline.tasks.extract.task import extract_task
from prefect import flow, get_run_logger


@flow(name="ingest-jobs", log_prints=True)
def ingest_flow() -> dict[str, dict[str, int]]:
    """
    Run the full pipeline with a durable checkpoint after each stage.

    Reads search_keywords from Postgres, then:
    raw_jobs → canonical_jobs → Qdrant

    Keyword catalog sync is a separate flow: pipeline.flows.sync_keywords
    """
    logger = get_run_logger()

    extract_result = extract_task()
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
