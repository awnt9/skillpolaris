"""LLM-as-a-judge output and sampling schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class JudgeVerdict(BaseModel):
    score: float = Field(ge=0.0, le=1.0)
    reasoning: str


class JudgeSkillMention(BaseModel):
    name: str
    requirement_level: str
    alt_group: str | None = None


class JudgeEnrichedJob(BaseModel):
    """Row from canonical_jobs, already enriched, sampled for judging."""

    id: int
    title: str
    description: str
    standard_role: str | None = None
    is_remote: bool | None = None
    language_required: str | None = None
    min_years_experience: int | None = None
    hard_skills: list[JudgeSkillMention]
