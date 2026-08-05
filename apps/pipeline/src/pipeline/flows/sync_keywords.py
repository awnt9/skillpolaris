"""Sync keyword catalog into Postgres."""

from __future__ import annotations

from pipeline.tasks.keywords.sync import sync_keywords_task
from prefect import flow, get_run_logger


@flow(name="sync-keywords", log_prints=True)
def sync_keywords_flow(esco_groups: list[int] | None = None) -> dict[str, int]:
    logger = get_run_logger()
    result = sync_keywords_task(esco_groups=esco_groups)
    logger.info("Keyword sync flow finished: %s", result)
    return result


if __name__ == "__main__":
    sync_keywords_flow()
