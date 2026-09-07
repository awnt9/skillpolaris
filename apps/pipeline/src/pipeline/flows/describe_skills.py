"""Describe-skills flow: skills with no description -> one-sentence LLM description."""

from __future__ import annotations

from pipeline.tasks.skills import describe_skills_task
from prefect import flow, get_run_logger


@flow(name="describe-skills", log_prints=True)
def describe_skills_flow() -> dict[str, int]:
    logger = get_run_logger()
    result = describe_skills_task()
    logger.info("Describe-skills flow finished: %s", result)
    return result


if __name__ == "__main__":
    describe_skills_flow()
