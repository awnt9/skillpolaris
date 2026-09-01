"""Candidate skills -> ranked role fit.

score(role) = sum of score_weight over the candidate's matched skills for that
role (see pipeline.storage.models.RoleSkillStat for how score_weight is
precomputed).

rank_roles() is pure scoring: no DB access, inputs are already-resolved rows,
trivial to reason about and test in isolation. match_cv_to_roles() is the
orchestration entrypoint routers should call — it owns the repository calls
so routers never talk to api.repositories directly.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import Engine

from api.repositories.role_stats import (
    RoleAggregateRow,
    RoleSkillRow,
    get_role_aggregates,
    get_role_skill_stats,
    resolve_skill_ids,
)


@dataclass(frozen=True)
class MatchedSkill:
    name: str
    market_pct: float


@dataclass(frozen=True)
class RoleMatch:
    standard_role: str
    score: float
    job_count: int
    is_remote_pct: float | None
    language_distribution: dict[str, float]
    matched_skills: list[MatchedSkill]


def rank_roles(
    skill_rows: list[RoleSkillRow],
    aggregates: list[RoleAggregateRow],
    *,
    top_n: int,
) -> list[RoleMatch]:
    aggregates_by_role = {aggregate.standard_role: aggregate for aggregate in aggregates}

    rows_by_role: dict[str, list[RoleSkillRow]] = {}
    for row in skill_rows:
        rows_by_role.setdefault(row.standard_role, []).append(row)

    results: list[RoleMatch] = []
    for role, rows in rows_by_role.items():
        aggregate = aggregates_by_role.get(role)
        matched_skills = sorted(
            (MatchedSkill(name=row.skill_name, market_pct=row.market_pct) for row in rows),
            key=lambda skill: skill.market_pct,
            reverse=True,
        )
        results.append(
            RoleMatch(
                standard_role=role,
                score=sum(row.score_weight for row in rows),
                job_count=aggregate.job_count if aggregate else 0,
                is_remote_pct=aggregate.is_remote_pct if aggregate else None,
                language_distribution=aggregate.language_distribution if aggregate else {},
                matched_skills=matched_skills,
            )
        )

    results.sort(key=lambda role: role.score, reverse=True)
    return results[:top_n]


@dataclass(frozen=True)
class CVMatchResult:
    matched_skills: list[str]
    unmatched_skills: list[str]
    roles: list[RoleMatch]


def match_cv_to_roles(
    engine: Engine,
    candidate_names: list[str],
    *,
    top_n: int,
) -> CVMatchResult:
    skill_id_by_name = resolve_skill_ids(engine, candidate_names)
    matched_names = sorted(skill_id_by_name)
    unmatched_names = sorted(set(candidate_names) - set(skill_id_by_name))

    skill_rows = get_role_skill_stats(engine, list(skill_id_by_name.values()))
    aggregates = get_role_aggregates(
        engine,
        list({row.standard_role for row in skill_rows}),
    )
    roles = rank_roles(skill_rows, aggregates, top_n=top_n)

    return CVMatchResult(
        matched_skills=matched_names,
        unmatched_skills=unmatched_names,
        roles=roles,
    )
