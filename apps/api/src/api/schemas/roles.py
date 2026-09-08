"""Pydantic models for the per-role experience breakdown endpoint."""

from __future__ import annotations

from pydantic import BaseModel


class SkillMarketOut(BaseModel):
    name: str
    market_pct: float


class ExperienceBucketOut(BaseModel):
    experience_years: int | None
    job_count: int
    skills: list[SkillMarketOut]


class RoleExperienceBreakdownOut(BaseModel):
    standard_role: str
    buckets: list[ExperienceBucketOut]
