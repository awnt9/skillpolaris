"""Open role taxonomy: standard_roles table + canonical_jobs.standard_role_id.

Revision ID: 007_open_role_taxonomy
Revises: 006_enrich_metadata
Create Date: 2026-08-28
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "007_open_role_taxonomy"
down_revision: str | None = "006_enrich_metadata"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# The 18 labels the closed StandardRole enum used to enforce. This is the
# only vocabulary that can already exist in canonical_jobs.standard_role, so
# it seeds the open taxonomy without changing any existing job's label.
_SEED_ROLES = [
    "Software Engineer",
    "Backend Developer",
    "Frontend Developer",
    "Full Stack Developer",
    "Mobile Developer",
    "Data Engineer",
    "Data Scientist",
    "Machine Learning Engineer",
    "DevOps Engineer",
    "Site Reliability Engineer",
    "Platform Engineer",
    "Cloud Engineer",
    "Security Engineer",
    "QA Automation Engineer",
    "Embedded Software Engineer",
    "Database Administrator",
    "Technical Lead",
    "Engineering Manager",
]


def upgrade() -> None:
    op.create_table(
        "standard_roles",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("merged_into_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["merged_into_id"], ["standard_roles.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_standard_roles_name"),
    )
    op.execute(
        """
        CREATE UNIQUE INDEX uq_standard_roles_name_ci
            ON standard_roles (lower(name))
        """
    )

    op.add_column(
        "canonical_jobs",
        sa.Column("standard_role_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_canonical_jobs_standard_role_id",
        "canonical_jobs",
        "standard_roles",
        ["standard_role_id"],
        ["id"],
    )
    op.create_index(
        "ix_canonical_jobs_standard_role_id",
        "canonical_jobs",
        ["standard_role_id"],
    )

    seed_table = sa.table(
        "standard_roles",
        sa.column("name", sa.Text()),
    )
    op.bulk_insert(seed_table, [{"name": name} for name in _SEED_ROLES])

    op.execute(
        """
        UPDATE canonical_jobs
        SET standard_role_id = standard_roles.id
        FROM standard_roles
        WHERE canonical_jobs.standard_role = standard_roles.name
        """
    )


def downgrade() -> None:
    op.drop_index("ix_canonical_jobs_standard_role_id", table_name="canonical_jobs")
    op.drop_constraint(
        "fk_canonical_jobs_standard_role_id",
        "canonical_jobs",
        type_="foreignkey",
    )
    op.drop_column("canonical_jobs", "standard_role_id")
    op.execute("DROP INDEX IF EXISTS uq_standard_roles_name_ci")
    op.drop_table("standard_roles")
