"""Add llm_judge_scores: async, sampled LLM-as-a-judge quality scores for
filter and enrich outputs (own storage — not dependent on Langfuse's native
Evaluators/Rules, which don't reliably trigger on this self-hosted instance).

Revision ID: 016_llm_judge_scores
Revises: 015_skill_alt_group
Create Date: 2026-09-08
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "016_llm_judge_scores"
down_revision: str | None = "015_skill_alt_group"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "llm_judge_scores",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("judge_type", sa.Text(), nullable=False),
        sa.Column("target_id", sa.Integer(), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("reasoning", sa.Text(), nullable=False),
        sa.Column("judge_model", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_llm_judge_scores_judge_type",
        "llm_judge_scores",
        ["judge_type"],
    )


def downgrade() -> None:
    op.drop_index("ix_llm_judge_scores_judge_type", table_name="llm_judge_scores")
    op.drop_table("llm_judge_scores")
