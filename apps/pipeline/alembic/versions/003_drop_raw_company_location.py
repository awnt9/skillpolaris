"""Drop unused company_raw and location_raw from raw_jobs.

Revision ID: 003_drop_raw_geo
Revises: 002_drop_staging
Create Date: 2026-08-07
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "003_drop_raw_geo"
down_revision: str | None = "002_drop_staging"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_column("raw_jobs", "company_raw")
    op.drop_column("raw_jobs", "location_raw")


def downgrade() -> None:
    op.add_column(
        "raw_jobs",
        sa.Column("location_raw", sa.Text(), nullable=True),
    )
    op.add_column(
        "raw_jobs",
        sa.Column("company_raw", sa.Text(), nullable=True),
    )
