"""Judge runner: async, sampled LLM-as-a-judge quality check on filter/enrich outputs.

Runs after the fact, on a random sample of already-processed jobs — cheap and
decoupled from the real filter/enrich hot path, mirroring the sampling rate
Langfuse's native Rules would have used had they worked on this instance.

Each sampled item's LLM call(s) run concurrently with the other items,
bounded by `LLM_MAX_CONCURRENCY` — the same I/O-bound reasoning as
filter/enrich's own runners. Postgres writes stay synchronous and sequential,
in sample order, once every call has resolved.
"""

from __future__ import annotations

import asyncio
import json
import random
from dataclasses import dataclass

from pipeline.config import Settings, get_configuration
from pipeline.observability import configure_tracing, score_current_span, start_root_span
from pipeline.schemas.judge import JudgeVerdict
from pipeline.storage.postgres import PostgresManager
from pipeline.tasks.filter.llm import FilterLlmGate
from pipeline.tasks.filter.rules import apply_fixed_filters
from pipeline.tasks.judge.llm import EnrichJudge, FilterJudge
from prefect import get_run_logger, task


@dataclass
class _FilterJudgeOutcome:
    title: str
    excerpt: str
    label: str
    confidence: float
    verdict: JudgeVerdict | None
    error: Exception | None


async def _judge_filter_all(
    gate: FilterLlmGate,
    judge: FilterJudge,
    sample: list,
    excerpt_chars: int,
    max_concurrency: int,
    logger,
) -> list[tuple[int, _FilterJudgeOutcome | None]]:
    """Runs concurrently, logging progress as each item resolves — otherwise
    the whole concurrent phase is silent until the batch finishes."""
    semaphore = asyncio.Semaphore(max_concurrency)
    total = len(sample)
    done = 0

    async def _one(raw_job) -> tuple[int, _FilterJudgeOutcome | None]:
        nonlocal done
        rules = apply_fixed_filters(
            title_raw=raw_job.title_raw,
            description_raw=raw_job.description_raw,
            min_description_chars=0,
        )
        if not rules.ok:
            return raw_job.id, None

        excerpt = rules.cleaned_description[:excerpt_chars]
        async with semaphore:
            try:
                decision = await gate.decide_async(
                    title=rules.cleaned_title,
                    description_excerpt=excerpt,
                    source=raw_job.source,
                    keyword=raw_job.keyword,
                )
                with start_root_span("judge-filter") as span:
                    verdict = await judge.score_async(
                        title=rules.cleaned_title,
                        description_excerpt=excerpt,
                        label=decision.label,
                        confidence=decision.confidence,
                    )
                    if span is not None:
                        span.update(
                            input=f"TITLE: {rules.cleaned_title}\n{excerpt}",
                            output=f"label={decision.label}, confidence={decision.confidence}",
                        )
                    score_current_span(
                        name="quality", value=verdict.score, comment=verdict.reasoning
                    )
                done += 1
                logger.info(
                    "Judge filter progress %s/%s id=%s score=%.2f",
                    done,
                    total,
                    raw_job.id,
                    verdict.score,
                )
                return raw_job.id, _FilterJudgeOutcome(
                    title=rules.cleaned_title,
                    excerpt=excerpt,
                    label=decision.label,
                    confidence=decision.confidence,
                    verdict=verdict,
                    error=None,
                )
            except Exception as exc:  # noqa: BLE001 — per-item boundary
                done += 1
                logger.warning(
                    "Judge filter progress %s/%s id=%s failed: %s", done, total, raw_job.id, exc
                )
                return raw_job.id, _FilterJudgeOutcome(
                    title=rules.cleaned_title,
                    excerpt=excerpt,
                    label="",
                    confidence=0.0,
                    verdict=None,
                    error=exc,
                )

    return await asyncio.gather(*(_one(raw_job) for raw_job in sample))


def run_judge_filter(configuration: Settings) -> dict[str, int]:
    logger = get_run_logger()
    configure_tracing(configuration)

    gate = FilterLlmGate(
        base_url=configuration.llm_base_url,
        api_key=configuration.llm_api_key,
        model=configuration.filter_llm_model,
    )
    judge = FilterJudge(
        base_url=configuration.llm_base_url,
        api_key=configuration.llm_api_key,
        model=configuration.llm_model,
    )

    judged = 0
    with PostgresManager(configuration) as store:
        pool = store.get_recent_llm_filtered_raw_jobs(limit=configuration.judge_sample_size)
        sample = [job for job in pool if random.random() < configuration.judge_sample_rate]

        results = asyncio.run(
            _judge_filter_all(
                gate,
                judge,
                sample,
                configuration.filter_llm_excerpt_chars,
                configuration.llm_max_concurrency,
                logger,
            )
        )

        for raw_job_id, outcome in results:
            if outcome is None:
                continue  # rules rejected this one on re-derivation; nothing to judge
            if outcome.error is not None:
                logger.exception(
                    "Judge filter failed for raw_job id=%s", raw_job_id, exc_info=outcome.error
                )
                continue
            verdict = outcome.verdict
            assert verdict is not None

            store.save_judge_score(
                judge_type="filter",
                target_id=raw_job_id,
                score=verdict.score,
                reasoning=verdict.reasoning,
                judge_model=configuration.llm_model,
            )
            judged += 1
            logger.info("Judge filter id=%s score=%.2f", raw_job_id, verdict.score)

    return {"pool": len(pool), "judged": judged}


@dataclass
class _EnrichJudgeOutcome:
    metadata_json: str
    verdict: JudgeVerdict | None
    error: Exception | None


async def _judge_enrich_all(
    judge: EnrichJudge,
    sample: list,
    max_concurrency: int,
    logger,
) -> list[tuple[int, _EnrichJudgeOutcome]]:
    """Runs concurrently, logging progress as each item resolves — otherwise
    the whole concurrent phase is silent until the batch finishes."""
    semaphore = asyncio.Semaphore(max_concurrency)
    total = len(sample)
    done = 0

    async def _one(job) -> tuple[int, _EnrichJudgeOutcome]:
        nonlocal done
        metadata_json = json.dumps(
            {
                "standard_role": job.standard_role,
                "is_remote": job.is_remote,
                "language_required": job.language_required,
                "min_years_experience": job.min_years_experience,
                "hard_skills": [skill.model_dump() for skill in job.hard_skills],
            }
        )
        async with semaphore:
            try:
                with start_root_span("judge-enrich") as span:
                    verdict = await judge.score_async(
                        title=job.title,
                        description=job.description,
                        metadata_json=metadata_json,
                    )
                    if span is not None:
                        span.update(
                            input=f"TITLE: {job.title}\n\n{job.description}",
                            output=metadata_json,
                        )
                    score_current_span(
                        name="quality", value=verdict.score, comment=verdict.reasoning
                    )
                done += 1
                logger.info(
                    "Judge enrich progress %s/%s id=%s score=%.2f",
                    done,
                    total,
                    job.id,
                    verdict.score,
                )
                return job.id, _EnrichJudgeOutcome(
                    metadata_json=metadata_json, verdict=verdict, error=None
                )
            except Exception as exc:  # noqa: BLE001 — per-item boundary
                done += 1
                logger.warning(
                    "Judge enrich progress %s/%s id=%s failed: %s", done, total, job.id, exc
                )
                return job.id, _EnrichJudgeOutcome(
                    metadata_json=metadata_json, verdict=None, error=exc
                )

    return await asyncio.gather(*(_one(job) for job in sample))


def run_judge_enrich(configuration: Settings) -> dict[str, int]:
    logger = get_run_logger()
    configure_tracing(configuration)

    judge = EnrichJudge(
        base_url=configuration.llm_base_url,
        api_key=configuration.llm_api_key,
        model=configuration.llm_model,
    )

    judged = 0
    with PostgresManager(configuration) as store:
        pool = store.get_recent_enriched_jobs(limit=configuration.judge_sample_size)
        sample = [job for job in pool if random.random() < configuration.judge_sample_rate]

        results = asyncio.run(
            _judge_enrich_all(judge, sample, configuration.llm_max_concurrency, logger)
        )

        for job_id, outcome in results:
            if outcome.error is not None:
                logger.exception(
                    "Judge enrich failed for canonical_job id=%s", job_id, exc_info=outcome.error
                )
                continue
            verdict = outcome.verdict
            assert verdict is not None

            store.save_judge_score(
                judge_type="enrich",
                target_id=job_id,
                score=verdict.score,
                reasoning=verdict.reasoning,
                judge_model=configuration.llm_model,
            )
            judged += 1
            logger.info("Judge enrich id=%s score=%.2f", job_id, verdict.score)

    return {"pool": len(pool), "judged": judged}


@task(name="judge-filter", retries=1)
def judge_filter_task() -> dict[str, int]:
    configuration = get_configuration()
    result = run_judge_filter(configuration)
    get_run_logger().info(
        "Judge-filter finished. pool=%s judged=%s", result["pool"], result["judged"]
    )
    return result


@task(name="judge-enrich", retries=1)
def judge_enrich_task() -> dict[str, int]:
    configuration = get_configuration()
    result = run_judge_enrich(configuration)
    get_run_logger().info(
        "Judge-enrich finished. pool=%s judged=%s", result["pool"], result["judged"]
    )
    return result
