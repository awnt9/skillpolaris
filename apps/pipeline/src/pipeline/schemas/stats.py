"""Structured data for precomputed role/skill matching statistics."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SkillMention:
    """One (job, skill) link, with the requirement info stats are weighted by.

    alt_group is None for an ordinary independent requirement, or a short label
    shared by two or more skills the posting states are interchangeable
    alternatives (e.g. "AWS or GCP") — see tasks.enrich.stats.compute_role_stats
    for how groups are weighted.
    """

    skill_id: int
    requirement_level: str
    alt_group: str | None


@dataclass(frozen=True)
class EnrichedJobSnapshot:
    """One enriched canonical_job's fields relevant to role/skill stats."""

    standard_role: str
    is_remote: bool | None
    language_required: str | None
    skills: tuple[SkillMention, ...]


@dataclass(frozen=True)
class RoleSkillWeight:
    """Precomputed per-(role, skill) matching weight."""

    standard_role: str
    skill_id: int
    score_weight: float
    market_pct: float


@dataclass(frozen=True)
class RoleAggregate:
    """Precomputed per-role aggregate over canonical_jobs."""

    standard_role: str
    job_count: int
    is_remote_pct: float | None
    language_distribution: dict[str, float]
