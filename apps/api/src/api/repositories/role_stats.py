"""Read-only access to skills / role_skill_stats / role_stats.

No scoring logic here — see api.services.matching for that. This module only
turns rows into plain dataclasses.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import Engine, bindparam, text

# Postgres primary keys can't be NULL, so role_skill_stats/role_stats use -1 as
# a non-null stand-in for "posting didn't state a number of years" (mirrors
# pipeline.schemas.stats.UNSPECIFIED_EXPERIENCE_YEARS — apps/api has no
# dependency on apps/pipeline, so this sentinel is duplicated by necessity;
# keep both in sync). Translated back to None right below, in RoleSkillRow/
# RoleAggregateRow construction — nothing past this module ever sees -1.
UNSPECIFIED_EXPERIENCE_YEARS = -1


@dataclass(frozen=True)
class RoleSkillRow:
    standard_role: str
    experience_years: int | None
    skill_id: int
    skill_name: str
    score_weight: float
    market_pct: float


@dataclass(frozen=True)
class RoleAggregateRow:
    standard_role: str
    experience_years: int | None
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
    """Every (role, experience_years) bucket where any of these skills appear.

    Filters by skill_ids only — api.services.matching.rank_roles picks the
    bucket matching the candidate's own years (falling back to the
    unspecified-years bucket) per role from this result, rather than this
    query filtering by years itself."""
    if not skill_ids:
        return []

    statement = text(
        """
        SELECT rss.standard_role, rss.experience_years, rss.skill_id, s.name,
               rss.score_weight, rss.market_pct
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
            experience_years=None if years == UNSPECIFIED_EXPERIENCE_YEARS else years,
            skill_id=skill_id,
            skill_name=name,
            score_weight=score_weight,
            market_pct=market_pct,
        )
        for role, years, skill_id, name, score_weight, market_pct in rows
    ]


def get_role_skills(
    engine: Engine,
    role_experience_pairs: list[tuple[str, int | None]],
) -> list[RoleSkillRow]:
    """All skills tracked for the given (role, experience_years) pairs,
    regardless of whether the candidate has them. Used to render the full
    market ranking, with the candidate's own skills highlighted separately."""
    if not role_experience_pairs:
        return []

    clauses: list[str] = []
    params: dict[str, object] = {}
    for i, (role, years) in enumerate(role_experience_pairs):
        clauses.append(f"(rss.standard_role = :role_{i} AND rss.experience_years = :exp_{i})")
        params[f"role_{i}"] = role
        params[f"exp_{i}"] = years if years is not None else UNSPECIFIED_EXPERIENCE_YEARS

    statement = text(
        f"""
        SELECT rss.standard_role, rss.experience_years, rss.skill_id, s.name,
               rss.score_weight, rss.market_pct
        FROM role_skill_stats rss
        JOIN skills s ON s.id = rss.skill_id
        WHERE {" OR ".join(clauses)}
        """
    )
    with engine.connect() as conn:
        rows = conn.execute(statement, params).all()
    return [
        RoleSkillRow(
            standard_role=role,
            experience_years=None if years == UNSPECIFIED_EXPERIENCE_YEARS else years,
            skill_id=skill_id,
            skill_name=name,
            score_weight=score_weight,
            market_pct=market_pct,
        )
        for role, years, skill_id, name, score_weight, market_pct in rows
    ]


def get_role_aggregates(
    engine: Engine,
    role_experience_pairs: list[tuple[str, int | None]],
) -> list[RoleAggregateRow]:
    if not role_experience_pairs:
        return []

    clauses: list[str] = []
    params: dict[str, object] = {}
    for i, (role, years) in enumerate(role_experience_pairs):
        clauses.append(f"(standard_role = :role_{i} AND experience_years = :exp_{i})")
        params[f"role_{i}"] = role
        params[f"exp_{i}"] = years if years is not None else UNSPECIFIED_EXPERIENCE_YEARS

    statement = text(
        f"""
        SELECT standard_role, experience_years, job_count, is_remote_pct, language_distribution
        FROM role_stats
        WHERE {" OR ".join(clauses)}
        """
    )
    with engine.connect() as conn:
        rows = conn.execute(statement, params).all()
    return [
        RoleAggregateRow(
            standard_role=role,
            experience_years=None if years == UNSPECIFIED_EXPERIENCE_YEARS else years,
            job_count=job_count,
            is_remote_pct=is_remote_pct,
            language_distribution=language_distribution or {},
        )
        for role, years, job_count, is_remote_pct, language_distribution in rows
    ]


def get_role_skills_all_years(engine: Engine, standard_role: str) -> list[RoleSkillRow]:
    """Every experience_years bucket's skills for one role — the experience
    breakdown endpoint's data source, not scoped to any candidate."""
    statement = text(
        """
        SELECT rss.standard_role, rss.experience_years, rss.skill_id, s.name,
               rss.score_weight, rss.market_pct
        FROM role_skill_stats rss
        JOIN skills s ON s.id = rss.skill_id
        WHERE rss.standard_role = :role
        """
    )
    with engine.connect() as conn:
        rows = conn.execute(statement, {"role": standard_role}).all()
    return [
        RoleSkillRow(
            standard_role=role,
            experience_years=None if years == UNSPECIFIED_EXPERIENCE_YEARS else years,
            skill_id=skill_id,
            skill_name=name,
            score_weight=score_weight,
            market_pct=market_pct,
        )
        for role, years, skill_id, name, score_weight, market_pct in rows
    ]


def get_role_aggregates_all_years(engine: Engine, standard_role: str) -> list[RoleAggregateRow]:
    """Every experience_years bucket's aggregate for one role."""
    statement = text(
        """
        SELECT standard_role, experience_years, job_count, is_remote_pct, language_distribution
        FROM role_stats
        WHERE standard_role = :role
        """
    )
    with engine.connect() as conn:
        rows = conn.execute(statement, {"role": standard_role}).all()
    return [
        RoleAggregateRow(
            standard_role=role,
            experience_years=None if years == UNSPECIFIED_EXPERIENCE_YEARS else years,
            job_count=job_count,
            is_remote_pct=is_remote_pct,
            language_distribution=language_distribution or {},
        )
        for role, years, job_count, is_remote_pct, language_distribution in rows
    ]
