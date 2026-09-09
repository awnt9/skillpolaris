"""Show requirement_level and alt_group per skill in canonical_jobs_enriched.

Revision ID: 019_enriched_view_skill_level
Revises: 018_enriched_view_min_years
Create Date: 2026-09-09
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "019_enriched_view_skill_level"
down_revision: str | None = "018_enriched_view_min_years"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_VIEW_NAME = "canonical_jobs_enriched"

_SKILL_EXPR = (
    "s.name || ' (' || cjs.requirement_level"
    " || CASE WHEN cjs.alt_group IS NOT NULL THEN ', alt:' || cjs.alt_group ELSE '' END"
    " || ')'"
)

_CREATE_VIEW_WITH_SKILL_LEVEL = f"""
CREATE VIEW {_VIEW_NAME} AS
SELECT
    cj.id,
    cj.source,
    cj.job_id,
    cj.title,
    cj.description,
    cj.standard_role,
    cj.min_years_experience,
    cj.is_remote,
    cj.language_required,
    cj.enrich_status,
    cj.url,
    string_agg({_SKILL_EXPR}, ', ' ORDER BY s.name) AS skills
FROM canonical_jobs cj
LEFT JOIN canonical_job_skills cjs ON cjs.canonical_job_id = cj.id
LEFT JOIN skills s ON s.id = cjs.skill_id
GROUP BY cj.id
ORDER BY cj.id;
"""

_CREATE_VIEW_WITHOUT_SKILL_LEVEL = f"""
CREATE VIEW {_VIEW_NAME} AS
SELECT
    cj.id,
    cj.source,
    cj.job_id,
    cj.title,
    cj.description,
    cj.standard_role,
    cj.min_years_experience,
    cj.is_remote,
    cj.language_required,
    cj.enrich_status,
    cj.url,
    string_agg(s.name, ', ' ORDER BY s.name) AS skills
FROM canonical_jobs cj
LEFT JOIN canonical_job_skills cjs ON cjs.canonical_job_id = cj.id
LEFT JOIN skills s ON s.id = cjs.skill_id
GROUP BY cj.id
ORDER BY cj.id;
"""


def upgrade() -> None:
    op.execute(f"DROP VIEW {_VIEW_NAME}")
    op.execute(_CREATE_VIEW_WITH_SKILL_LEVEL)


def downgrade() -> None:
    op.execute(f"DROP VIEW {_VIEW_NAME}")
    op.execute(_CREATE_VIEW_WITHOUT_SKILL_LEVEL)
