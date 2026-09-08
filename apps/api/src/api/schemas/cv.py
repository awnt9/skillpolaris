"""Pydantic models for the CV matching endpoint."""

from __future__ import annotations

from pydantic import BaseModel, Field


class CVProfile(BaseModel):
    """LLM-extracted skills from a resume."""

    hard_skills: list[str] = Field(
        default_factory=list,
        description=(
            "Technical skills, tools, or methodologies attested in the resume. "
            "Each entry must be 1-3 words and appear literally in the text. "
            "No soft skills."
        ),
    )
    years_experience: int | None = Field(
        default=None,
        ge=0,
        description=(
            "Candidate's total years of professional experience, estimated from "
            "the work history's dates. Null if not enough date information is given."
        ),
    )


class SkillOut(BaseModel):
    name: str
    market_pct: float
    is_matched: bool


class RoleMatchOut(BaseModel):
    standard_role: str
    experience_years: int | None
    score: float
    job_count: int
    is_remote_pct: float | None
    language_distribution: dict[str, float]
    skills: list[SkillOut]


class CVMatchResponse(BaseModel):
    matched_skills: list[str]
    unmatched_skills: list[str]
    candidate_years_experience: int | None
    roles: list[RoleMatchOut]
