"""Add canonical_jobs_enriched view: one row per job with role + skills.

Revision ID: 011_canonical_jobs_enriched_view
Revises: 010_role_stats
Create Date: 2026-09-01
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "011_canonical_jobs_enriched_view"
down_revision: str | None = "010_role_stats"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_VIEW_NAME = "canonical_jobs_enriched"

_CREATE_VIEW = f"""
CREATE VIEW {_VIEW_NAME} AS
SELECT
    cj.id,
    cj.source,
    cj.job_id,
    cj.title,
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
    op.execute(_CREATE_VIEW)


def downgrade() -> None:
    op.execute(f"DROP VIEW {_VIEW_NAME}")
