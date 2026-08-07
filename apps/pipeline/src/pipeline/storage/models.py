"""SQLModel table definitions for pipeline Postgres storage."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import Column, DateTime, Text, UniqueConstraint, func
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
    transform_status: str = Field(
        default="pending",
        sa_column=Column(Text, nullable=False, server_default="pending"),
    )
    created_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime, server_default=func.now(), nullable=True),
    )
    transformed_at: Optional[datetime] = Field(
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
