"""Add min_years_experience to canonical_jobs, and widen role_skill_stats /
role_stats to group by (standard_role, experience_years) instead of just
standard_role — a role's expected skills differ by seniority.

Both stats tables are fully rebuilt by PostgresManager.replace_role_stats on
every enrich run (delete-all then reinsert, no WHERE clause), so there's no
data to preserve across this migration: drop+recreate with the widened
primary key instead of ALTER-based PK surgery.

Revision ID: 017_min_years_experience
Revises: 016_llm_judge_scores
Create Date: 2026-09-08
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "017_min_years_experience"
down_revision: str | None = "016_llm_judge_scores"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("canonical_jobs", sa.Column("min_years_experience", sa.Integer(), nullable=True))

    op.drop_index("ix_role_skill_stats_skill_id", table_name="role_skill_stats")
    op.drop_table("role_skill_stats")
    op.drop_table("role_stats")

    op.create_table(
        "role_skill_stats",
        sa.Column("standard_role", sa.Text(), nullable=False),
        sa.Column("skill_id", sa.Integer(), nullable=False),
        sa.Column("experience_years", sa.Integer(), nullable=False),
        sa.Column("score_weight", sa.Float(), nullable=False),
        sa.Column("market_pct", sa.Float(), nullable=False),
        sa.Column("computed_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(["skill_id"], ["skills.id"]),
        sa.PrimaryKeyConstraint("standard_role", "skill_id", "experience_years"),
    )
    op.create_index(
        "ix_role_skill_stats_skill_id",
        "role_skill_stats",
        ["skill_id"],
    )

    op.create_table(
        "role_stats",
        sa.Column("standard_role", sa.Text(), nullable=False),
        sa.Column("experience_years", sa.Integer(), nullable=False),
        sa.Column("job_count", sa.Integer(), nullable=False),
        sa.Column("is_remote_pct", sa.Float(), nullable=True),
        sa.Column(
            "language_distribution",
            JSONB(),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("computed_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint("standard_role", "experience_years"),
    )


def downgrade() -> None:
    op.drop_table("role_stats")
    op.drop_index("ix_role_skill_stats_skill_id", table_name="role_skill_stats")
    op.drop_table("role_skill_stats")

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

    op.drop_column("canonical_jobs", "min_years_experience")
