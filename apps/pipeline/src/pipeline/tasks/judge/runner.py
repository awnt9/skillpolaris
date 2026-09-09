"""Judge runner: async, sampled LLM-as-a-judge quality check on filter/enrich outputs.

Runs after the fact, on a random sample of already-processed jobs — cheap and
decoupled from the real filter/enrich hot path, mirroring the sampling rate
Langfuse's native Rules would have used had they worked on this instance.
"""

from __future__ import annotations

import json
import random

from pipeline.config import Settings, get_configuration
from pipeline.observability import configure_tracing, score_current_span, start_root_span
from pipeline.storage.postgres import PostgresManager
from pipeline.tasks.filter.llm import FilterLlmGate
from pipeline.tasks.filter.rules import apply_fixed_filters
from pipeline.tasks.judge.llm import EnrichJudge, FilterJudge
from prefect import get_run_logger, task


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

        for raw_job in sample:
            # Re-derive the exact decision the real run made (temperature=0, so
            # reproducible) — filter_status only stores the resolved status,
            # not the raw label/confidence the judge needs.
            rules = apply_fixed_filters(
                title_raw=raw_job.title_raw,
                description_raw=raw_job.description_raw,
                min_description_chars=0,
            )
            if not rules.ok:
                continue

            excerpt = rules.cleaned_description[: configuration.filter_llm_excerpt_chars]
            decision = gate.decide(
                title=rules.cleaned_title,
                description_excerpt=excerpt,
                source=raw_job.source,
                keyword=raw_job.keyword,
            )
            with start_root_span("judge-filter") as span:
                verdict = judge.score(
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
                score_current_span(name="quality", value=verdict.score, comment=verdict.reasoning)

            store.save_judge_score(
                judge_type="filter",
                target_id=raw_job.id,
                score=verdict.score,
                reasoning=verdict.reasoning,
                judge_model=configuration.llm_model,
            )
            judged += 1
            logger.info("Judge filter id=%s score=%.2f", raw_job.id, verdict.score)

    return {"pool": len(pool), "judged": judged}


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

        for job in sample:
            metadata_json = json.dumps(
                {
                    "standard_role": job.standard_role,
                    "is_remote": job.is_remote,
                    "language_required": job.language_required,
                    "min_years_experience": job.min_years_experience,
                    "hard_skills": [skill.model_dump() for skill in job.hard_skills],
                }
            )
            with start_root_span("judge-enrich") as span:
                verdict = judge.score(
                    title=job.title,
                    description=job.description,
                    metadata_json=metadata_json,
                )
                if span is not None:
                    span.update(
                        input=f"TITLE: {job.title}\n\n{job.description}",
                        output=metadata_json,
                    )
                score_current_span(name="quality", value=verdict.score, comment=verdict.reasoning)

            store.save_judge_score(
                judge_type="enrich",
                target_id=job.id,
                score=verdict.score,
                reasoning=verdict.reasoning,
                judge_model=configuration.llm_model,
            )
            judged += 1
            logger.info("Judge enrich id=%s score=%.2f", job.id, verdict.score)

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
