"""Add min_years_experience to canonical_jobs_enriched view.

Revision ID: 018_enriched_view_min_years
Revises: 017_min_years_experience
Create Date: 2026-09-09
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "018_enriched_view_min_years"
down_revision: str | None = "017_min_years_experience"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_VIEW_NAME = "canonical_jobs_enriched"

_CREATE_VIEW_WITH_YEARS = f"""
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

_CREATE_VIEW_WITHOUT_YEARS = f"""
CREATE VIEW {_VIEW_NAME} AS
SELECT
    cj.id,
    cj.source,
    cj.job_id,
    cj.title,
    cj.description,
    cj.standard_role,
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
    op.execute(_CREATE_VIEW_WITH_YEARS)


def downgrade() -> None:
    op.execute(f"DROP VIEW {_VIEW_NAME}")
    op.execute(_CREATE_VIEW_WITHOUT_YEARS)
