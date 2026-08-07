from typing import Any, Literal, TypedDict

from pydantic import BaseModel, Field

ExtractorKind = Literal["detail", "feed", "ats"]
FilterStatus = Literal["pending", "accepted", "rejected", "uncertain", "failed"]
TransformStatus = Literal["pending", "processed", "failed"]


class DetailTask(TypedDict):
    """Serializable unit of work for a detail fetch."""

    id: str
    source_name: str
    keyword: str


class RawJobRecord(BaseModel):
    """Normalized extract output written to raw_jobs before filtering."""

    source: str
    external_id: str
    extractor_kind: ExtractorKind
    keyword: str | None = None
    title_raw: str
    description_raw: str
    url: str | None = None
    posted_at_raw: str | None = None
    raw_payload: dict[str, Any]


class PendingRawJob(BaseModel):
    """Row from raw_jobs awaiting filter."""

    id: int
    source: str
    job_id: str
    keyword: str | None = None
    title_raw: str
    description_raw: str
    url: str | None = None
    posted_at_raw: str | None = None


class CanonicalJobOffer(BaseModel):
    """Offer accepted by the programmable-market filter."""

    raw_job_id: int
    source: str
    job_id: str
    title: str
    description: str
    url: str | None = None
    posted_at: str | None = None
    keyword: str | None = None


class PendingCanonicalJob(BaseModel):
    """Row from canonical_jobs awaiting transform."""

    id: int
    raw_job_id: int
    source: str
    job_id: str
    title: str
    description: str
    keyword: str | None = None


class FeedBatch(BaseModel):
    """Page/window returned by a feed-style extractor."""

    records: list[dict[str, Any]] = Field(default_factory=list)
    next_cursor: str | None = None
