from __future__ import annotations

from pipeline.config import get_configuration
from pipeline.tasks.extract.orchestrator import run_extract_summary
from prefect import get_run_logger, task


@task(name="extract", retries=1)
def extract_task(
    *,
    ats_company_slugs: list[str] | None = None,
) -> dict[str, int]:
    logger = get_run_logger()
    configuration = get_configuration()
    result = run_extract_summary(
        configuration,
        ats_company_slugs=ats_company_slugs,
    )
    logger.info(
        "Extract finished. keywords_used=%s saved=%s failed=%s skipped=%s",
        result["keywords_used"],
        result["saved"],
        result["failed"],
        result["skipped"],
    )
    return result
