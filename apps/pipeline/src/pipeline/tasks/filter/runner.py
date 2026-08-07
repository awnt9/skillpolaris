"""Filter runner: fixed hygiene rules then cheap LLM gate."""

from __future__ import annotations

from collections import Counter

from pipeline.config import Settings, get_configuration
from pipeline.schemas.jobs import CanonicalJobOffer
from pipeline.storage.postgres import PostgresManager
from pipeline.tasks.filter.llm import FilterLlmGate
from pipeline.tasks.filter.rules import apply_fixed_filters
from prefect import get_run_logger, task


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

    if not (configuration.filter_llm_model or "").strip():
        raise RuntimeError("FILTER_LLM_MODEL is empty; set it before running filter")

    gate = FilterLlmGate(
        base_url=configuration.ollama_base_url,
        api_key=configuration.ollama_api_key,
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

        for raw_job in pending:
            by_source[raw_job.source] += 1
            try:
                rules = apply_fixed_filters(
                    title_raw=raw_job.title_raw,
                    description_raw=raw_job.description_raw,
                    min_description_chars=configuration.filter_min_description_chars,
                )
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

                excerpt = rules.cleaned_description[
                    : configuration.filter_llm_excerpt_chars
                ]
                llm_calls += 1
                decision = gate.decide(
                    title=rules.cleaned_title,
                    description_excerpt=excerpt,
                    source=raw_job.source,
                    keyword=raw_job.keyword,
                )
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
