"""Add precomputed role_skill_stats and role_stats tables.

Revision ID: 007_role_stats
Revises: 006_enrich_metadata
Create Date: 2026-08-28
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "007_role_stats"
down_revision: str | None = "006_enrich_metadata"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "role_skill_stats",
        sa.Column("standard_role", sa.Text(), nullable=False),
        sa.Column("skill_id", sa.Integer(), nullable=False),
        sa.Column("score_weight", sa.Float(), nullable=False),
        sa.Column("market_pct", sa.Float(), nullable=False),
        sa.Column("computed_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(["skill_id"], ["skills.id"]),
        sa.PrimaryKeyConstraint("standard_role", "skill_id"),
    )
    op.create_index(
        "ix_role_skill_stats_skill_id",
        "role_skill_stats",
        ["skill_id"],
    )

    op.create_table(
        "role_stats",
        sa.Column("standard_role", sa.Text(), nullable=False),
        sa.Column("job_count", sa.Integer(), nullable=False),
        sa.Column("is_remote_pct", sa.Float(), nullable=True),
        sa.Column(
            "language_distribution",
            JSONB(),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("computed_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint("standard_role"),
    )


def downgrade() -> None:
    op.drop_table("role_stats")
    op.drop_index("ix_role_skill_stats_skill_id", table_name="role_skill_stats")
    op.drop_table("role_skill_stats")
