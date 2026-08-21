"""Rename transform columns, store enrichment metadata, add skill tables.

Revision ID: 006_enrich_metadata
Revises: 005_drop_can_geo
Create Date: 2026-08-20
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "006_enrich_metadata"
down_revision: str | None = "005_drop_can_geo"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "canonical_jobs",
        "transform_status",
        new_column_name="enrich_status",
    )
    op.alter_column(
        "canonical_jobs",
        "transformed_at",
        new_column_name="enriched_at",
    )
    op.add_column("canonical_jobs", sa.Column("standard_role", sa.Text(), nullable=True))
    op.add_column("canonical_jobs", sa.Column("is_remote", sa.Boolean(), nullable=True))
    op.add_column(
        "canonical_jobs",
        sa.Column("language_required", sa.Text(), nullable=True),
    )
    op.create_index(
        "ix_canonical_jobs_standard_role",
        "canonical_jobs",
        ["standard_role"],
    )
    op.create_index(
        "ix_canonical_jobs_enrich_status",
        "canonical_jobs",
        ["enrich_status"],
    )

    op.create_table(
        "skills",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_skills_name"),
    )
    op.create_table(
        "canonical_job_skills",
        sa.Column("canonical_job_id", sa.Integer(), nullable=False),
        sa.Column("skill_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["canonical_job_id"], ["canonical_jobs.id"]),
        sa.ForeignKeyConstraint(["skill_id"], ["skills.id"]),
        sa.PrimaryKeyConstraint("canonical_job_id", "skill_id"),
    )


def downgrade() -> None:
    op.drop_table("canonical_job_skills")
    op.drop_table("skills")
    op.drop_index("ix_canonical_jobs_enrich_status", table_name="canonical_jobs")
    op.drop_index("ix_canonical_jobs_standard_role", table_name="canonical_jobs")
    op.drop_column("canonical_jobs", "language_required")
    op.drop_column("canonical_jobs", "is_remote")
    op.drop_column("canonical_jobs", "standard_role")
    op.alter_column(
        "canonical_jobs",
        "enriched_at",
        new_column_name="transformed_at",
    )
    op.alter_column(
        "canonical_jobs",
        "enrich_status",
        new_column_name="transform_status",
    )
