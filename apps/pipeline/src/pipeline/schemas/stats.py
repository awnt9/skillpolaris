"""Structured data for precomputed role/skill matching statistics."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EnrichedJobSnapshot:
    """One enriched canonical_job's fields relevant to role/skill stats."""

    standard_role: str
    is_remote: bool | None
    language_required: str | None
    skill_ids: frozenset[int]


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
