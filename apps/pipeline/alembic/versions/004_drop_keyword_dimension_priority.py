"""Drop dimension and priority from search_keywords.

Revision ID: 004_drop_kw_meta
Revises: 003_drop_raw_geo
Create Date: 2026-08-07
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "004_drop_kw_meta"
down_revision: str | None = "003_drop_raw_geo"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_search_keywords_active")
    op.drop_constraint(
        "search_keywords_keyword_dimension_source_scope_key",
        "search_keywords",
        type_="unique",
    )
    op.drop_column("search_keywords", "priority")
    op.drop_column("search_keywords", "dimension")
    op.create_unique_constraint(
        "search_keywords_keyword_source_scope_key",
        "search_keywords",
        ["keyword", "source_scope"],
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_search_keywords_active
            ON search_keywords (
                active,
                raw_jobs_count ASC,
                last_searched_at ASC NULLS FIRST
            )
            WHERE active = TRUE
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_search_keywords_active")
    op.drop_constraint(
        "search_keywords_keyword_source_scope_key",
        "search_keywords",
        type_="unique",
    )
    op.add_column(
        "search_keywords",
        sa.Column(
            "dimension",
            sa.String(),
            server_default="role",
            nullable=False,
        ),
    )
    op.add_column(
        "search_keywords",
        sa.Column(
            "priority",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
    )
    op.create_unique_constraint(
        "search_keywords_keyword_dimension_source_scope_key",
        "search_keywords",
        ["keyword", "dimension", "source_scope"],
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
