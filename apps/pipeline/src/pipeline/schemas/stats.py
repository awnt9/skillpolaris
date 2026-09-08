"""Structured data for precomputed role/skill matching statistics."""

from __future__ import annotations

from dataclasses import dataclass

# Postgres primary keys can't be NULL, so RoleSkillWeight/RoleAggregate (which
# become role_skill_stats/role_stats PK columns) need a non-null stand-in for
# "posting didn't state a number of years" — -1, not 0, since 0 is a legitimate
# extracted value ("no experience required"). Only ever appears here and in
# tasks.enrich.stats.compute_role_stats; EnrichedJobSnapshot stays nullable,
# matching the source. apps/api/src/api/repositories/role_stats.py mirrors this
# constant (no cross-package dependency) and is the only place it's translated
# back to None.
UNSPECIFIED_EXPERIENCE_YEARS: int = -1


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
    min_years_experience: int | None
    skills: tuple[SkillMention, ...]


@dataclass(frozen=True)
class RoleSkillWeight:
    """Precomputed per-(role, experience_years, skill) matching weight."""

    standard_role: str
    experience_years: int
    skill_id: int
    score_weight: float
    market_pct: float


@dataclass(frozen=True)
class RoleAggregate:
    """Precomputed per-(role, experience_years) aggregate over canonical_jobs."""

    standard_role: str
    experience_years: int
    job_count: int
    is_remote_pct: float | None
    language_distribution: dict[str, float]
