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


class MatchedSkillOut(BaseModel):
    name: str
    market_pct: float


class RoleMatchOut(BaseModel):
    standard_role: str
    score: float
    job_count: int
    is_remote_pct: float | None
    language_distribution: dict[str, float]
    matched_skills: list[MatchedSkillOut]


class CVMatchResponse(BaseModel):
    matched_skills: list[str]
    unmatched_skills: list[str]
    roles: list[RoleMatchOut]
