"""Filter task: classify raw offers into the programmable market."""

from __future__ import annotations

import re

from pipeline.config import Settings, get_configuration
from pipeline.schemas.jobs import CanonicalJobOffer, PendingRawJob
from pipeline.storage.postgres import PostgresManager
from prefect import get_run_logger, task

PROGRAMMING_SIGNALS = {
    "python",
    "java",
    "javascript",
    "typescript",
    "go",
    "rust",
    "sql",
    "docker",
    "kubernetes",
    "git",
    "api",
    "backend",
    "frontend",
    "devops",
    "software",
    "developer",
    "engineer",
    "programmer",
}


def clean_description(text: str) -> str:
    if not text or not isinstance(text, str):
        return ""

    text = re.sub(r"http[s]?://\S+", "", text)
    text = re.sub(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b", "", text)
    text = re.sub(r"#{2,}", "", text)
    text = re.sub(r"-{3,}", "", text)
    text = re.sub(r"\*{3,}", "", text)
    text = re.sub(r"\n\s*[\*\-]\s+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def is_programmable(raw_job: PendingRawJob) -> bool:
    """Cheap rule-based filter; LLM refinement comes later."""
    haystack = f"{raw_job.title_raw} {raw_job.description_raw}".lower()
    tokens = set(re.findall(r"[a-z][a-z0-9+#./-]*", haystack))
    return len(tokens & PROGRAMMING_SIGNALS) >= 2


def run_filter(configuration: Settings) -> dict[str, int]:
    accepted = 0
    rejected = 0

    with PostgresManager(configuration) as store:
        pending = store.get_pending_filter_jobs(limit=configuration.filter_batch_size)

        for raw_job in pending:
            if is_programmable(raw_job):
                store.save_canonical_job(
                    CanonicalJobOffer(
                        raw_job_id=raw_job.id,
                        source=raw_job.source,
                        job_id=raw_job.job_id,
                        title=raw_job.title_raw.strip(),
                        description=clean_description(raw_job.description_raw),
                        url=raw_job.url,
                        posted_at=raw_job.posted_at_raw,
                        keyword=raw_job.keyword,
                    )
                )
                store.update_raw_filter_status(raw_job.id, "accepted", "rules")
                accepted += 1
            else:
                store.update_raw_filter_status(raw_job.id, "rejected", "rules")
                rejected += 1

    return {"pending": len(pending), "accepted": accepted, "rejected": rejected}


@task(name="filter", retries=1)
def filter_task() -> dict[str, int]:
    logger = get_run_logger()
    configuration = get_configuration()
    result = run_filter(configuration)
    logger.info(
        "Filter finished. pending=%s accepted=%s rejected=%s",
        result["pending"],
        result["accepted"],
        result["rejected"],
    )
    return result
