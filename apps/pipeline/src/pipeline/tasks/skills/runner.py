"""Describe-skills runner: skills with no description -> one-sentence LLM description.

Description calls are I/O-bound, so the batch runs them concurrently, bounded
by `LLM_MAX_CONCURRENCY`; Postgres writes stay synchronous and sequential in
the original pending-list order once every call has resolved.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

from pipeline.config import Settings, get_configuration
from pipeline.observability import configure_tracing
from pipeline.storage.postgres import PostgresManager
from pipeline.tasks.skills.llm import SkillDescriber
from prefect import get_run_logger, task


@dataclass
class _DescribeOutcome:
    description: str | None
    error: Exception | None


async def _describe_all(
    describer: SkillDescriber,
    skills: list,
    max_concurrency: int,
    logger,
) -> dict[int, _DescribeOutcome]:
    """Run description calls concurrently, logging progress as each resolves —
    otherwise the whole concurrent phase is silent until the batch finishes."""
    semaphore = asyncio.Semaphore(max_concurrency)
    total = len(skills)
    done = 0

    async def _one(skill) -> tuple[int, _DescribeOutcome]:
        nonlocal done
        async with semaphore:
            try:
                description = await describer.describe_async(skill.name)
                done += 1
                logger.info(
                    "Describe-skills llm progress %s/%s id=%s name=%s",
                    done,
                    total,
                    skill.id,
                    skill.name,
                )
                return skill.id, _DescribeOutcome(description=description, error=None)
            except Exception as exc:  # noqa: BLE001 — per-skill boundary
                done += 1
                logger.warning(
                    "Describe-skills llm progress %s/%s id=%s name=%s failed: %s",
                    done,
                    total,
                    skill.id,
                    skill.name,
                    exc,
                )
                return skill.id, _DescribeOutcome(description=None, error=exc)

    results = await asyncio.gather(*(_one(skill) for skill in skills))
    return dict(results)


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

        outcomes = asyncio.run(
            _describe_all(describer, pending, configuration.llm_max_concurrency, logger)
        )

        for skill in pending:
            try:
                outcome = outcomes[skill.id]
                if outcome.error is not None:
                    raise outcome.error
                assert outcome.description is not None

                store.save_skill_description(skill.id, outcome.description)
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
