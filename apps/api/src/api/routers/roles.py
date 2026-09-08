from collections import defaultdict

from fastapi import APIRouter, HTTPException

from api.db import get_engine
from api.repositories.role_stats import (
    RoleSkillRow,
    get_role_aggregates_all_years,
    get_role_skills_all_years,
)
from api.schemas.roles import ExperienceBucketOut, RoleExperienceBreakdownOut, SkillMarketOut

router = APIRouter()

SKILLS_PER_BUCKET = 20


@router.get(
    "/roles/{standard_role}/experience-breakdown",
    response_model=RoleExperienceBreakdownOut,
)
def get_role_experience_breakdown(standard_role: str) -> RoleExperienceBreakdownOut:
    engine = get_engine()
    aggregates = get_role_aggregates_all_years(engine, standard_role)
    if not aggregates:
        raise HTTPException(status_code=404, detail="Role not found.")

    skills_by_years: dict[int | None, list[RoleSkillRow]] = defaultdict(list)
    for row in get_role_skills_all_years(engine, standard_role):
        skills_by_years[row.experience_years].append(row)

    buckets = [
        ExperienceBucketOut(
            experience_years=aggregate.experience_years,
            job_count=aggregate.job_count,
            skills=[
                SkillMarketOut(name=row.skill_name, market_pct=row.market_pct)
                for row in sorted(
                    skills_by_years.get(aggregate.experience_years, []),
                    key=lambda row: row.market_pct,
                    reverse=True,
                )[:SKILLS_PER_BUCKET]
            ],
        )
        for aggregate in sorted(
            aggregates,
            key=lambda aggregate: (
                aggregate.experience_years is None,
                aggregate.experience_years or 0,
            ),
        )
    ]

    return RoleExperienceBreakdownOut(standard_role=standard_role, buckets=buckets)
