"""Describe-skills runner: skills with no description -> one-sentence LLM description."""

from __future__ import annotations

from pipeline.config import Settings, get_configuration
from pipeline.observability import configure_tracing
from pipeline.storage.postgres import PostgresManager
from pipeline.tasks.skills.llm import SkillDescriber
from prefect import get_run_logger, task


def run_describe_skills(configuration: Settings) -> dict[str, int]:
    logger = get_run_logger()
    configure_tracing(configuration)

    processed = 0
    failed = 0

    with PostgresManager(configuration) as store:
        describer = SkillDescriber(
            base_url=configuration.llm_base_url,
            api_key=configuration.llm_api_key,
            model=configuration.llm_model,
        )

        pending = store.get_skills_missing_description(limit=configuration.enrich_batch_size)
        logger.info("Describe-skills batch: pending=%s", len(pending))

        for skill in pending:
            try:
                description = describer.describe(skill.name)
                store.save_skill_description(skill.id, description)
                processed += 1
            except Exception:  # noqa: BLE001 — per-skill boundary
                logger.exception(
                    "Describe-skills failed for skill id=%s name=%s",
                    skill.id,
                    skill.name,
                )
                failed += 1

    return {"pending": len(pending), "processed": processed, "failed": failed}


@task(name="describe-skills", retries=1)
def describe_skills_task() -> dict[str, int]:
    logger = get_run_logger()
    configuration = get_configuration()
    result = run_describe_skills(configuration)
    logger.info(
        "Describe-skills finished. pending=%s processed=%s failed=%s",
        result["pending"],
        result["processed"],
        result["failed"],
    )
    return result
