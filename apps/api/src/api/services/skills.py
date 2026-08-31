"""Skill-name normalization.

Must stay behaviorally identical to pipeline.schemas.enrich.normalize_skill_name:
the skills table is populated by the pipeline using that exact rule, and a
candidate's extracted skill only counts as a match when its normalized form is
byte-for-byte equal to a stored skill name.
"""

from __future__ import annotations


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
