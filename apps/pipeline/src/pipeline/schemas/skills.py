"""Structured types for the describe-skills flow."""

from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel, Field


@dataclass(frozen=True)
class PendingSkill:
    id: int
    name: str


class SkillDescriptionOut(BaseModel):
    """One-sentence, LLM-generated description of a technical skill."""

    description: str = Field(
        description=(
            "One sentence, plain English, describing what the skill is and how it's "
            "used professionally. Neutral and factual, no marketing language."
        ),
    )
