"""Structured metadata extracted from a canonical job offer."""

from __future__ import annotations

from dataclasses import dataclass, field

from pydantic import BaseModel, Field


@dataclass(frozen=True)
class StandardRoleOption:
    """A standard role as shown to the enrich agent: title + description + synonyms."""

    name: str
    description: str | None = None
    synonyms: list[str] = field(default_factory=list)


class JobOfferMetadata(BaseModel):
    """Recruiter-oriented fields stored relationally after enrichment."""

    standard_role: str = Field(
        description=(
            "The standardized job title for this posting. If one of the existing standard "
            "roles listed in the prompt is a good semantic match, output it verbatim. "
            "Otherwise, propose a new standardized title: English, Title Case, the common "
            "industry term for the role, singular, no seniority or company-specific wording "
            "unless essential to the role's meaning."
        ),
    )
    standard_role_description: str | None = Field(
        default=None,
        description=(
            "Required ONLY when standard_role is a NEW title not already in the existing "
            "roles list: one sentence describing the role, in the same style as the "
            "descriptions shown for the existing roles. Leave null when reusing an existing "
            "standard role."
        ),
    )
    standard_role_synonyms: list[str] = Field(
        default_factory=list,
        description=(
            "If standard_role is NEW, list 2-5 common alternative titles for it (same style "
            "as the synonym lists shown for existing roles). If reusing an EXISTING role, "
            "leave this empty — UNLESS this posting's own title is a genuinely useful "
            "alternative label not already listed for that role, in which case add just that "
            "one term."
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


def format_roles_block(roles: list[StandardRoleOption]) -> str:
    if not roles:
        return "(none yet — propose the first one)"
    lines: list[str] = []
    for role in roles:
        line = f"- {role.name}"
        if role.description:
            line += f" — {role.description}"
        if role.synonyms:
            line += f" (also known as: {', '.join(role.synonyms)})"
        lines.append(line)
    return "\n".join(lines)


def normalize_skill_name(name: str) -> str:
    return " ".join(name.strip().lower().split())


def normalize_role_name(name: str) -> str:
    return " ".join(name.strip().split())


def normalize_synonym(name: str) -> str:
    return " ".join(name.strip().split())


def merge_synonyms(
    existing: list[str],
    additions: list[str],
    canonical_name: str,
) -> list[str]:
    """Case-insensitive de-duplicated union, excluding the canonical role name itself."""
    seen = {s.strip().lower() for s in existing}
    seen.add(canonical_name.strip().lower())
    merged = list(existing)
    for raw in additions:
        candidate = normalize_synonym(raw)
        if not candidate:
            continue
        lowered = candidate.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        merged.append(candidate)
    return merged


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
