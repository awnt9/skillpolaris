"""Enrichment: extract standardized role and attested skills into Postgres."""

from pipeline.tasks.enrich.runner import enrich_task, run_enrich

__all__ = ["enrich_task", "run_enrich"]
