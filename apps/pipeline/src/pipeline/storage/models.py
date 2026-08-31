"""SQLModel table definitions for pipeline Postgres storage."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import Boolean, Column, DateTime, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel


class RawJob(SQLModel, table=True):
    __tablename__ = "raw_jobs"
    __table_args__ = (UniqueConstraint("source", "job_id"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    source: str
    job_id: str
    extractor_kind: str
    keyword: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))
    title_raw: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))
    description_raw: Optional[str] = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
    )
    url: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))
    posted_at_raw: Optional[str] = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
    )
    raw_payload: dict[str, Any] = Field(sa_column=Column(JSONB, nullable=False))
    filter_status: str = Field(default="pending")
    filter_method: Optional[str] = None
    filtered_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime, nullable=True),
    )
    extracted_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime, server_default=func.now(), nullable=True),
    )


class CanonicalJob(SQLModel, table=True):
    __tablename__ = "canonical_jobs"
    __table_args__ = (UniqueConstraint("source", "job_id"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    raw_job_id: Optional[int] = Field(default=None, foreign_key="raw_jobs.id")
    source: str = Field(sa_column=Column(Text, nullable=False))
    job_id: str = Field(sa_column=Column(Text, nullable=False))
    title: str = Field(sa_column=Column(Text, nullable=False))
    description: str = Field(sa_column=Column(Text, nullable=False))
    url: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))
    posted_at: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))
    keyword: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))
    enrich_status: str = Field(
        default="pending",
        sa_column=Column(Text, nullable=False, server_default="pending", index=True),
    )
    standard_role: Optional[str] = Field(
        default=None,
        sa_column=Column(Text, nullable=True, index=True),
    )
    is_remote: Optional[bool] = Field(
        default=None,
        sa_column=Column(Boolean, nullable=True),
    )
    language_required: Optional[str] = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
    )
    created_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime, server_default=func.now(), nullable=True),
    )
    enriched_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime, nullable=True),
    )


class SearchKeywordRow(SQLModel, table=True):
    __tablename__ = "search_keywords"
    __table_args__ = (UniqueConstraint("keyword", "source_scope"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    keyword: str
    source_scope: str = Field(default="")
    origin: str
    active: bool = Field(default=True)
    last_searched_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime, nullable=True),
    )
    raw_jobs_count: int = Field(default=0)
    created_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime, server_default=func.now(), nullable=True),
    )


class FeedCursor(SQLModel, table=True):
    __tablename__ = "feed_cursors"

    source_name: str = Field(primary_key=True)
    cursor: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))
    updated_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=True),
    )


class Skill(SQLModel, table=True):
    __tablename__ = "skills"
    __table_args__ = (UniqueConstraint("name", name="uq_skills_name"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(sa_column=Column(Text, nullable=False))


class CanonicalJobSkill(SQLModel, table=True):
    __tablename__ = "canonical_job_skills"

    canonical_job_id: int = Field(foreign_key="canonical_jobs.id", primary_key=True)
    skill_id: int = Field(foreign_key="skills.id", primary_key=True)
