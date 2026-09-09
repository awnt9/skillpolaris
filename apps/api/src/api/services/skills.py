"""Skill-name normalization.

Reuses pipeline.schemas.enrich.normalize_skill_name directly rather than a
hand-copied duplicate: the skills table is populated by the pipeline using
that exact rule, and a candidate's extracted skill only counts as a match
when its normalized form is byte-for-byte equal to a stored skill name.
"""

from __future__ import annotations

from pipeline.schemas.enrich import normalize_skill_name

__all__ = ["normalize_skill_name", "normalized_skills"]


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
