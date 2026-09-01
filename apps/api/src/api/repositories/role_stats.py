"""Read-only access to skills / role_skill_stats / role_stats.

No scoring logic here — see api.services.matching for that. This module only
turns rows into plain dataclasses.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import Engine, bindparam, text


@dataclass(frozen=True)
class RoleSkillRow:
    standard_role: str
    skill_id: int
    skill_name: str
    score_weight: float
    market_pct: float


@dataclass(frozen=True)
class RoleAggregateRow:
    standard_role: str
    job_count: int
    is_remote_pct: float | None
    language_distribution: dict[str, float]


def resolve_skill_ids(engine: Engine, normalized_names: list[str]) -> dict[str, int]:
    """Exact-match lookup: a candidate skill only resolves if its normalized
    form is byte-for-byte equal to a stored skills.name."""
    if not normalized_names:
        return {}

    statement = text("SELECT id, name FROM skills WHERE name IN :names").bindparams(
        bindparam("names", expanding=True)
    )
    with engine.connect() as conn:
        rows = conn.execute(statement, {"names": normalized_names}).all()
    return {name: skill_id for skill_id, name in rows}


def get_role_skill_stats(engine: Engine, skill_ids: list[int]) -> list[RoleSkillRow]:
    if not skill_ids:
        return []

    statement = text(
        """
        SELECT rss.standard_role, rss.skill_id, s.name, rss.score_weight, rss.market_pct
        FROM role_skill_stats rss
        JOIN skills s ON s.id = rss.skill_id
        WHERE rss.skill_id IN :skill_ids
        """
    ).bindparams(bindparam("skill_ids", expanding=True))
    with engine.connect() as conn:
        rows = conn.execute(statement, {"skill_ids": skill_ids}).all()
    return [
        RoleSkillRow(
            standard_role=role,
            skill_id=skill_id,
            skill_name=name,
            score_weight=score_weight,
            market_pct=market_pct,
        )
        for role, skill_id, name, score_weight, market_pct in rows
    ]


def get_role_aggregates(engine: Engine, roles: list[str]) -> list[RoleAggregateRow]:
    if not roles:
        return []

    statement = text(
        """
        SELECT standard_role, job_count, is_remote_pct, language_distribution
        FROM role_stats
        WHERE standard_role IN :roles
        """
    ).bindparams(bindparam("roles", expanding=True))
    with engine.connect() as conn:
        rows = conn.execute(statement, {"roles": roles}).all()
    return [
        RoleAggregateRow(
            standard_role=role,
            job_count=job_count,
            is_remote_pct=is_remote_pct,
            language_distribution=language_distribution or {},
        )
        for role, job_count, is_remote_pct, language_distribution in rows
    ]
