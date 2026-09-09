"""Filter runner: fixed hygiene rules then cheap LLM gate.

The LLM gate calls are I/O-bound (waiting on the provider's HTTP response),
so the batch runs them concurrently, bounded by `LLM_MAX_CONCURRENCY`, rather
than one at a time. Everything that touches Postgres stays synchronous and
sequential, in the original pending-list order, after all the concurrent
calls have resolved — the async phase only produces decisions/exceptions,
it does not write anything itself.
"""

from __future__ import annotations

import asyncio
from collections import Counter
from dataclasses import dataclass

from pipeline.config import Settings, get_configuration
from pipeline.observability import configure_tracing
from pipeline.schemas.filter import FilterLlmDecision
from pipeline.schemas.jobs import CanonicalJobOffer
from pipeline.storage.postgres import PostgresManager
from pipeline.tasks.filter.llm import FilterLlmGate
from pipeline.tasks.filter.rules import RuleOutcome, apply_fixed_filters
from prefect import get_run_logger, task


@dataclass
class _LlmOutcome:
    decision: FilterLlmDecision | None
    error: Exception | None


async def _decide_all(
    gate: FilterLlmGate,
    items: list[tuple[object, RuleOutcome]],
    excerpt_chars: int,
    max_concurrency: int,
    logger,
) -> dict[int, _LlmOutcome]:
    """Run the gate concurrently for every rule-passing job, bounded by a semaphore.

    Logs a progress line as each call resolves — without this, the whole
    concurrent phase is silent until every call in the batch has returned,
    which for a large batch can look hung even though it's working.
    """
    semaphore = asyncio.Semaphore(max_concurrency)
    total = len(items)
    done = 0

    async def _one(raw_job, rules: RuleOutcome) -> tuple[int, _LlmOutcome]:
        nonlocal done
        excerpt = rules.cleaned_description[:excerpt_chars]
        async with semaphore:
            try:
                decision = await gate.decide_async(
                    title=rules.cleaned_title,
                    description_excerpt=excerpt,
                    source=raw_job.source,
                    keyword=raw_job.keyword,
                )
                done += 1
                logger.info(
                    "Filter llm progress %s/%s id=%s label=%s conf=%.2f",
                    done,
                    total,
                    raw_job.id,
                    decision.label,
                    decision.confidence,
                )
                return raw_job.id, _LlmOutcome(decision=decision, error=None)
            except Exception as exc:  # noqa: BLE001 — per-offer boundary
                done += 1
                logger.warning(
                    "Filter llm progress %s/%s id=%s failed: %s", done, total, raw_job.id, exc
                )
                return raw_job.id, _LlmOutcome(decision=None, error=exc)

    results = await asyncio.gather(*(_one(raw_job, rules) for raw_job, rules in items))
    return dict(results)


def _resolve_llm_status(
    *,
    label: str,
    confidence: float,
    threshold: float,
) -> str:
    """Map LLM output to filter_status using a confidence floor."""
    if confidence < threshold or label == "uncertain":
        return "uncertain"
    if label == "accept":
        return "accepted"
    if label == "reject":
        return "rejected"
    return "uncertain"


def run_filter(configuration: Settings) -> dict[str, int]:
    logger = get_run_logger()
    configure_tracing(configuration)

    if not (configuration.filter_llm_model or "").strip():
        raise RuntimeError("FILTER_LLM_MODEL is empty; set it before running filter")

    gate = FilterLlmGate(
        base_url=configuration.llm_base_url,
        api_key=configuration.llm_api_key,
        model=configuration.filter_llm_model,
    )

    accepted = 0
    rejected = 0
    uncertain = 0
    failed = 0
    rules_rejected = 0
    llm_calls = 0
    by_source: Counter[str] = Counter()

    with PostgresManager(configuration) as store:
        pending = store.get_pending_filter_jobs(limit=configuration.filter_batch_size)
        logger.info(
            "Filter batch: pending=%s limit=%s model=%s min_desc=%s excerpt=%s conf>=%s",
            len(pending),
            configuration.filter_batch_size,
            configuration.filter_llm_model,
            configuration.filter_min_description_chars,
            configuration.filter_llm_excerpt_chars,
            configuration.filter_llm_confidence,
        )

        rules_by_id: dict[int, RuleOutcome] = {}
        llm_items: list[tuple[object, RuleOutcome]] = []
        for raw_job in pending:
            by_source[raw_job.source] += 1
            rules = apply_fixed_filters(
                title_raw=raw_job.title_raw,
                description_raw=raw_job.description_raw,
                min_description_chars=configuration.filter_min_description_chars,
            )
            rules_by_id[raw_job.id] = rules
            if rules.ok:
                llm_items.append((raw_job, rules))

        llm_calls = len(llm_items)
        outcomes = asyncio.run(
            _decide_all(
                gate,
                llm_items,
                configuration.filter_llm_excerpt_chars,
                configuration.llm_max_concurrency,
                logger,
            )
        )

        for raw_job in pending:
            rules = rules_by_id[raw_job.id]
            try:
                if not rules.ok:
                    store.update_raw_filter_status(raw_job.id, "rejected", "rules")
                    rejected += 1
                    rules_rejected += 1
                    logger.info(
                        "Filter rules reject id=%s source=%s reason=%s",
                        raw_job.id,
                        raw_job.source,
                        rules.reject_reason,
                    )
                    continue

                outcome = outcomes[raw_job.id]
                if outcome.error is not None:
                    raise outcome.error
                decision = outcome.decision
                assert decision is not None

                status = _resolve_llm_status(
                    label=decision.label,
                    confidence=decision.confidence,
                    threshold=configuration.filter_llm_confidence,
                )

                if status == "accepted":
                    store.save_canonical_job(
                        CanonicalJobOffer(
                            raw_job_id=raw_job.id,
                            source=raw_job.source,
                            job_id=raw_job.job_id,
                            title=rules.cleaned_title,
                            description=rules.cleaned_description,
                            url=raw_job.url,
                            posted_at=raw_job.posted_at_raw,
                            keyword=raw_job.keyword,
                        )
                    )
                    store.update_raw_filter_status(raw_job.id, "accepted", "llm")
                    accepted += 1
                elif status == "rejected":
                    store.update_raw_filter_status(raw_job.id, "rejected", "llm")
                    rejected += 1
                else:
                    store.update_raw_filter_status(raw_job.id, "uncertain", "llm")
                    uncertain += 1

                logger.info(
                    "Filter llm id=%s source=%s label=%s conf=%.2f status=%s",
                    raw_job.id,
                    raw_job.source,
                    decision.label,
                    decision.confidence,
                    status,
                )
            except Exception:  # noqa: BLE001 — per-offer boundary
                logger.exception(
                    "Filter failed for raw_job id=%s source=%s job_id=%s",
                    raw_job.id,
                    raw_job.source,
                    raw_job.job_id,
                )
                try:
                    store.update_raw_filter_status(raw_job.id, "failed", "llm")
                except Exception:  # noqa: BLE001
                    logger.exception(
                        "Could not mark raw_job id=%s as failed",
                        raw_job.id,
                    )
                failed += 1

    if by_source:
        logger.info(
            "Filter by source: %s",
            ", ".join(f"{source}={count}" for source, count in sorted(by_source.items())),
        )

    return {
        "pending": len(pending),
        "accepted": accepted,
        "rejected": rejected,
        "uncertain": uncertain,
        "failed": failed,
        "rules_rejected": rules_rejected,
        "llm_calls": llm_calls,
    }


@task(name="filter", retries=1)
def filter_task() -> dict[str, int]:
    logger = get_run_logger()
    configuration = get_configuration()
    result = run_filter(configuration)
    logger.info(
        "Filter finished. pending=%s accepted=%s rejected=%s uncertain=%s "
        "failed=%s rules_rejected=%s llm_calls=%s",
        result["pending"],
        result["accepted"],
        result["rejected"],
        result["uncertain"],
        result["failed"],
        result["rules_rejected"],
        result["llm_calls"],
    )
    return result
