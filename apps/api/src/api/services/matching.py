"""Pure scoring: candidate's matched skills -> ranked role fit.

score(role) = sum of score_weight over the candidate's matched skills for that
role (see pipeline.storage.models.RoleSkillStat for how score_weight is
precomputed). No DB access and no LLM calls here — inputs are already-resolved
rows, so this is trivial to reason about and test in isolation.
"""

from __future__ import annotations

from dataclasses import dataclass


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
