"""Prune: drop canonical_jobs older than CANONICAL_JOB_MAX_AGE_DAYS."""

from pipeline.tasks.prune.runner import prune_stale_jobs_task, run_prune

__all__ = [
    "prune_stale_jobs_task",
    "run_prune",
]
