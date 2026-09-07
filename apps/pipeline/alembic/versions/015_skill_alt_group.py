"""Add alt_group to canonical_job_skills: two or more skills sharing a group
label are alternatives ("AWS or GCP") satisfying a single requirement slot,
instead of independent requirements.

Revision ID: 015_skill_alt_group
Revises: 014_skill_requirement_level
Create Date: 2026-09-07
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "015_skill_alt_group"
down_revision: str | None = "014_skill_requirement_level"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("canonical_job_skills", sa.Column("alt_group", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("canonical_job_skills", "alt_group")
