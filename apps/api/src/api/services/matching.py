"""Candidate skills -> ranked role fit.

score(role) = sum of score_weight over the candidate's matched skills for that
role (see pipeline.storage.models.RoleSkillStat for how score_weight is
precomputed). Role selection and ranking is driven by this candidate-specific
score, but the skills displayed for each selected role are the full market
list (top skills_per_role by market_pct), with the candidate's own skills
flagged via `is_matched` rather than filtered down to them.

rank_roles() is pure scoring: no DB access, inputs are already-resolved rows,
trivial to reason about and test in isolation. match_cv_to_roles() is the
orchestration entrypoint routers should call — it owns the repository calls
so routers never talk to api.repositories directly.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from sqlalchemy import Engine

from api.repositories.role_stats import (
    RoleAggregateRow,
    RoleSkillRow,
    get_role_aggregates,
    get_role_skill_stats,
    get_role_skills,
    resolve_skill_ids,
)


@dataclass(frozen=True)
class SkillDisplay:
    name: str
    market_pct: float
    is_matched: bool


@dataclass(frozen=True)
class RoleScore:
    standard_role: str
    score: float


@dataclass(frozen=True)
class RoleMatch:
    standard_role: str
    score: float
    job_count: int
    is_remote_pct: float | None
    language_distribution: dict[str, float]
    skills: list[SkillDisplay]


def rank_roles(skill_rows: list[RoleSkillRow], *, top_n: int) -> list[RoleScore]:
    """Score each role by summing score_weight over the candidate's matched
    skills for that role, and return the top_n roles by score."""
    scores: dict[str, float] = defaultdict(float)
    for row in skill_rows:
        scores[row.standard_role] += row.score_weight

    ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    return [RoleScore(standard_role=role, score=score) for role, score in ranked[:top_n]]


def build_role_matches(
    ranked_roles: list[RoleScore],
    role_skills: list[RoleSkillRow],
    aggregates: list[RoleAggregateRow],
    matched_skill_ids: set[int],
    *,
    skills_per_role: int,
) -> list[RoleMatch]:
    aggregates_by_role = {aggregate.standard_role: aggregate for aggregate in aggregates}

    skills_by_role: dict[str, list[RoleSkillRow]] = defaultdict(list)
    for row in role_skills:
        skills_by_role[row.standard_role].append(row)

    results: list[RoleMatch] = []
    for ranked in ranked_roles:
        aggregate = aggregates_by_role.get(ranked.standard_role)
        rows = sorted(
            skills_by_role.get(ranked.standard_role, []),
            key=lambda row: row.market_pct,
            reverse=True,
        )[:skills_per_role]

        results.append(
            RoleMatch(
                standard_role=ranked.standard_role,
                score=ranked.score,
                job_count=aggregate.job_count if aggregate else 0,
                is_remote_pct=aggregate.is_remote_pct if aggregate else None,
                language_distribution=aggregate.language_distribution if aggregate else {},
                skills=[
                    SkillDisplay(
                        name=row.skill_name,
                        market_pct=row.market_pct,
                        is_matched=row.skill_id in matched_skill_ids,
                    )
                    for row in rows
                ],
            )
        )

    return results


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
    skills_per_role: int = 20,
) -> CVMatchResult:
    skill_id_by_name = resolve_skill_ids(engine, candidate_names)
    matched_names = sorted(skill_id_by_name)
    unmatched_names = sorted(set(candidate_names) - set(skill_id_by_name))
    matched_skill_ids = set(skill_id_by_name.values())

    candidate_skill_rows = get_role_skill_stats(engine, list(matched_skill_ids))
    ranked_roles = rank_roles(candidate_skill_rows, top_n=top_n)
    role_names = [role.standard_role for role in ranked_roles]

    role_skills = get_role_skills(engine, role_names)
    aggregates = get_role_aggregates(engine, role_names)
    roles = build_role_matches(
        ranked_roles,
        role_skills,
        aggregates,
        matched_skill_ids,
        skills_per_role=skills_per_role,
    )

    return CVMatchResult(
        matched_skills=matched_names,
        unmatched_skills=unmatched_names,
        roles=roles,
    )
