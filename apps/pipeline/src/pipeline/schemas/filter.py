"""Schemas for the programmable-market filter stage."""

from typing import Literal

from pydantic import BaseModel, Field

FilterLabel = Literal["accept", "reject", "uncertain"]


class FilterLlmDecision(BaseModel):
    """Minimal LLM gate output — keep tokens low."""

    label: FilterLabel = Field(
        description=(
            "accept if the offer is clearly for a software/data/IT engineering role; "
            "reject if clearly unrelated; uncertain if ambiguous."
        )
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence in the label from 0 to 1.",
    )
