"""Add description column to skills, filled in later by the describe-skills flow.

Revision ID: 013_skill_descriptions
Revises: 012_enriched_view_description
Create Date: 2026-09-07
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "013_skill_descriptions"
down_revision: str | None = "012_enriched_view_description"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("skills", sa.Column("description", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("skills", "description")
