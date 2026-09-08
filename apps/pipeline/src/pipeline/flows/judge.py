"""Judge-quality flow: async, sampled LLM-as-a-judge check on filter/enrich outputs."""

from __future__ import annotations

from pipeline.tasks.judge import judge_enrich_task, judge_filter_task
from prefect import flow, get_run_logger


@flow(name="judge-quality", log_prints=True)
def judge_quality_flow() -> dict[str, dict[str, int]]:
    logger = get_run_logger()
    filter_result = judge_filter_task()
    enrich_result = judge_enrich_task()
    logger.info(
        "Judge-quality flow finished: filter=%s enrich=%s",
        filter_result,
        enrich_result,
    )
    return {"filter": filter_result, "enrich": enrich_result}


if __name__ == "__main__":
    judge_quality_flow()
