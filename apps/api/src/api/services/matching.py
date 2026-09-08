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
    experience_years: int | None
    score: float


@dataclass(frozen=True)
class RoleMatch:
    standard_role: str
    experience_years: int | None
    score: float
    job_count: int
    is_remote_pct: float | None
    language_distribution: dict[str, float]
    skills: list[SkillDisplay]


def rank_roles(
    skill_rows: list[RoleSkillRow],
    *,
    candidate_years: int | None,
    top_n: int,
) -> list[RoleScore]:
    """Score each role by summing score_weight over the candidate's matched
    skills in the bucket matching candidate_years, and return the top_n by
    score. Each role appears at most once — experience_years only selects
    *which* bucket scores the role, it isn't a ranking dimension.

    role_skill_stats bakes postings with no stated years into every numbered
    bucket already (see tasks.enrich.stats.compute_role_stats), so a role
    only misses the exact candidate_years bucket when it has zero postings at
    that year AND zero postings with unstated years — rare in practice. When
    that happens, fall back to the UNSPECIFIED_EXPERIENCE_YEARS bucket
    (experience_years=None here, already translated by the repository layer);
    a role with no data in either bucket is dropped from the ranking.
    """
    rows_by_role: dict[str, list[RoleSkillRow]] = defaultdict(list)
    for row in skill_rows:
        rows_by_role[row.standard_role].append(row)

    scored: list[RoleScore] = []
    for role, rows in rows_by_role.items():
        bucket_years = candidate_years
        bucket_rows = [row for row in rows if row.experience_years == bucket_years]
        if not bucket_rows and bucket_years is not None:
            bucket_years = None
            bucket_rows = [row for row in rows if row.experience_years is None]
        if not bucket_rows:
            continue

        score = sum(row.score_weight for row in bucket_rows)
        scored.append(RoleScore(standard_role=role, experience_years=bucket_years, score=score))

    scored.sort(key=lambda role_score: role_score.score, reverse=True)
    return scored[:top_n]


def build_role_matches(
    ranked_roles: list[RoleScore],
    role_skills: list[RoleSkillRow],
    aggregates: list[RoleAggregateRow],
    matched_skill_ids: set[int],
    *,
    skills_per_role: int,
) -> list[RoleMatch]:
    aggregates_by_bucket = {
        (aggregate.standard_role, aggregate.experience_years): aggregate for aggregate in aggregates
    }

    skills_by_bucket: dict[tuple[str, int | None], list[RoleSkillRow]] = defaultdict(list)
    for row in role_skills:
        skills_by_bucket[(row.standard_role, row.experience_years)].append(row)

    results: list[RoleMatch] = []
    for ranked in ranked_roles:
        bucket = (ranked.standard_role, ranked.experience_years)
        aggregate = aggregates_by_bucket.get(bucket)
        rows = sorted(
            skills_by_bucket.get(bucket, []),
            key=lambda row: row.market_pct,
            reverse=True,
        )[:skills_per_role]

        results.append(
            RoleMatch(
                standard_role=ranked.standard_role,
                experience_years=ranked.experience_years,
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
    candidate_years: int | None,
    top_n: int,
    skills_per_role: int = 20,
) -> CVMatchResult:
    skill_id_by_name = resolve_skill_ids(engine, candidate_names)
    matched_names = sorted(skill_id_by_name)
    unmatched_names = sorted(set(candidate_names) - set(skill_id_by_name))
    matched_skill_ids = set(skill_id_by_name.values())

    candidate_skill_rows = get_role_skill_stats(engine, list(matched_skill_ids))
    ranked_roles = rank_roles(candidate_skill_rows, candidate_years=candidate_years, top_n=top_n)
    role_pairs = [(role.standard_role, role.experience_years) for role in ranked_roles]

    role_skills = get_role_skills(engine, role_pairs)
    aggregates = get_role_aggregates(engine, role_pairs)
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
