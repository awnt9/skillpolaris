"""Structured metadata extracted from a canonical job offer."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class StandardRole(StrEnum):
    """Closed role vocabulary. Coverage is defined per these labels."""

    SOFTWARE_ENGINEER = "Software Engineer"
    BACKEND_DEVELOPER = "Backend Developer"
    FRONTEND_DEVELOPER = "Frontend Developer"
    FULL_STACK_DEVELOPER = "Full Stack Developer"
    MOBILE_DEVELOPER = "Mobile Developer"
    DATA_ENGINEER = "Data Engineer"
    DATA_SCIENTIST = "Data Scientist"
    MACHINE_LEARNING_ENGINEER = "Machine Learning Engineer"
    DEVOPS_ENGINEER = "DevOps Engineer"
    SITE_RELIABILITY_ENGINEER = "Site Reliability Engineer"
    PLATFORM_ENGINEER = "Platform Engineer"
    CLOUD_ENGINEER = "Cloud Engineer"
    SECURITY_ENGINEER = "Security Engineer"
    QA_AUTOMATION_ENGINEER = "QA Automation Engineer"
    EMBEDDED_SOFTWARE_ENGINEER = "Embedded Software Engineer"
    DATABASE_ADMINISTRATOR = "Database Administrator"
    TECHNICAL_LEAD = "Technical Lead"
    ENGINEERING_MANAGER = "Engineering Manager"


class JobOfferMetadata(BaseModel):
    """Recruiter-oriented fields stored relationally after enrichment."""

    standard_role: StandardRole = Field(
        description=(
            "Map the employer title onto exactly one label from the closed role vocabulary. "
            "Do not invent a new title."
        ),
    )
    hard_skills: list[str] = Field(
        default_factory=list,
        description=(
            "Technical skills, tools, or methodologies attested in the posting. "
            "Each entry must be 1-3 words and appear literally in the text. "
            "No soft skills."
        ),
    )
    is_remote: bool | None = Field(
        default=None,
        description=(
            "True if the posting states remote or hybrid work. "
            "False if it states on-site only. "
            "Null if modality is not stated."
        ),
    )
    language_required: str | None = Field(
        default=None,
        description=(
            "Primary language required for the role, as an English name "
            "(Spanish, French, English). Null if not specified."
        ),
    )


def roles_prompt_block() -> str:
    return "\n".join(f"- {role.value}" for role in StandardRole)


def normalize_skill_name(name: str) -> str:
    return " ".join(name.strip().lower().split())


def normalized_skills(skills: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for raw in skills:
        normalized = normalize_skill_name(raw)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        ordered.append(normalized)
    return ordered
