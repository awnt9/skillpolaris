"""Add requirement_level to canonical_job_skills, so score_weight can be
weighted by how important a posting says a skill is (required/preferred/
nice_to_have) instead of treating every skill in a job as equally important.

Revision ID: 014_skill_requirement_level
Revises: 013_skill_descriptions
Create Date: 2026-09-07
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "014_skill_requirement_level"
down_revision: str | None = "013_skill_descriptions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "canonical_job_skills",
        sa.Column("requirement_level", sa.Text(), nullable=False, server_default="required"),
    )


def downgrade() -> None:
    op.drop_column("canonical_job_skills", "requirement_level")
