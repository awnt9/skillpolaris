"""Initial pipeline schema.

Revision ID: 001_initial
Revises:
Create Date: 2026-08-05
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "raw_jobs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("job_id", sa.String(), nullable=False),
        sa.Column("extractor_kind", sa.String(), nullable=False),
        sa.Column("keyword", sa.Text(), nullable=True),
        sa.Column("title_raw", sa.Text(), nullable=True),
        sa.Column("description_raw", sa.Text(), nullable=True),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("company_raw", sa.Text(), nullable=True),
        sa.Column("location_raw", sa.Text(), nullable=True),
        sa.Column("posted_at_raw", sa.Text(), nullable=True),
        sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "filter_status",
            sa.String(),
            server_default="pending",
            nullable=False,
        ),
        sa.Column("filter_method", sa.String(), nullable=True),
        sa.Column("filtered_at", sa.DateTime(), nullable=True),
        sa.Column("extracted_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source", "job_id"),
    )

    op.create_table(
        "canonical_jobs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("raw_job_id", sa.Integer(), nullable=True),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("job_id", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("company", sa.Text(), nullable=True),
        sa.Column("location", sa.Text(), nullable=True),
        sa.Column("posted_at", sa.Text(), nullable=True),
        sa.Column("keyword", sa.Text(), nullable=True),
        sa.Column(
            "transform_status",
            sa.Text(),
            server_default="pending",
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
        sa.Column("transformed_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["raw_job_id"], ["raw_jobs.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source", "job_id"),
    )

    op.create_table(
        "search_keywords",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("keyword", sa.String(), nullable=False),
        sa.Column("dimension", sa.String(), server_default="role", nullable=False),
        sa.Column("source_scope", sa.String(), server_default="", nullable=False),
        sa.Column("priority", sa.Integer(), server_default="0", nullable=False),
        sa.Column("origin", sa.String(), nullable=False),
        sa.Column("active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("last_searched_at", sa.DateTime(), nullable=True),
        sa.Column("raw_jobs_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("keyword", "dimension", "source_scope"),
    )

    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_search_keywords_active
            ON search_keywords (
                active,
                priority DESC,
                raw_jobs_count ASC,
                last_searched_at ASC NULLS FIRST
            )
            WHERE active = TRUE
        """
    )

    op.create_table(
        "staging_jobs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("job_id", sa.String(), nullable=False),
        sa.Column("raw_content", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("keyword", sa.String(), nullable=True),
        sa.Column("status", sa.String(), server_default="pending", nullable=False),
        sa.Column("extracted_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
        sa.Column("processed_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source", "job_id"),
    )


def downgrade() -> None:
    op.drop_table("staging_jobs")
    op.execute("DROP INDEX IF EXISTS idx_search_keywords_active")
    op.drop_table("search_keywords")
    op.drop_table("canonical_jobs")
    op.drop_table("raw_jobs")
