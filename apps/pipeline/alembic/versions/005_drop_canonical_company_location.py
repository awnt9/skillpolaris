"""Drop company and location from canonical_jobs.

Revision ID: 005_drop_can_geo
Revises: 004_drop_kw_meta
Create Date: 2026-08-07
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "005_drop_can_geo"
down_revision: str | None = "004_drop_kw_meta"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_column("canonical_jobs", "company")
    op.drop_column("canonical_jobs", "location")


def downgrade() -> None:
    op.add_column(
        "canonical_jobs",
        sa.Column("location", sa.Text(), nullable=True),
    )
    op.add_column(
        "canonical_jobs",
        sa.Column("company", sa.Text(), nullable=True),
    )
