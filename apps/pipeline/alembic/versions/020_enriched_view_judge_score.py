"""Add latest enrich-judge score/reasoning to canonical_jobs_enriched.

Revision ID: 020_enriched_view_judge_score
Revises: 019_enriched_view_skill_level
Create Date: 2026-09-09
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "020_enriched_view_judge_score"
down_revision: str | None = "019_enriched_view_skill_level"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_VIEW_NAME = "canonical_jobs_enriched"

_SKILL_EXPR = (
    "s.name || ' (' || cjs.requirement_level"
    " || CASE WHEN cjs.alt_group IS NOT NULL THEN ', alt:' || cjs.alt_group ELSE '' END"
    " || ')'"
)

_CREATE_VIEW_WITH_JUDGE_SCORE = f"""
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
    string_agg({_SKILL_EXPR}, ', ' ORDER BY s.name) AS skills,
    js.score AS judge_score,
    js.reasoning AS judge_reasoning
FROM canonical_jobs cj
LEFT JOIN canonical_job_skills cjs ON cjs.canonical_job_id = cj.id
LEFT JOIN skills s ON s.id = cjs.skill_id
LEFT JOIN LATERAL (
    SELECT score, reasoning
    FROM llm_judge_scores
    WHERE judge_type = 'enrich' AND target_id = cj.id
    ORDER BY created_at DESC
    LIMIT 1
) js ON true
GROUP BY cj.id, js.score, js.reasoning
ORDER BY cj.id;
"""

_CREATE_VIEW_WITHOUT_JUDGE_SCORE = f"""
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


def upgrade() -> None:
    op.execute(f"DROP VIEW {_VIEW_NAME}")
    op.execute(_CREATE_VIEW_WITH_JUDGE_SCORE)


def downgrade() -> None:
    op.execute(f"DROP VIEW {_VIEW_NAME}")
    op.execute(_CREATE_VIEW_WITHOUT_JUDGE_SCORE)
