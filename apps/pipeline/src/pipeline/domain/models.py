from typing import Any, Literal

from pydantic import BaseModel, Field

ExtractorKind = Literal["detail", "feed", "ats"]
FilterStatus = Literal["pending", "accepted", "rejected", "uncertain", "failed"]


class RawJobRecord(BaseModel):
    """Normalized extract output written to raw_jobs before filtering."""

    source: str
    external_id: str
    extractor_kind: ExtractorKind
    keyword: str | None = None
    title_raw: str
    description_raw: str
    url: str | None = None
    company_raw: str | None = None
    location_raw: str | None = None
    posted_at_raw: str | None = None
    raw_payload: dict[str, Any]


class CanonicalJobOffer(BaseModel):
    """Offer accepted by the programmable-market filter (post-raw)."""

    raw_job_id: int
    source: str
    job_id: str
    title: str
    description: str
    url: str | None = None
    company: str | None = None
    location: str | None = None
    posted_at: str | None = None
    keyword: str | None = None


class FeedBatch(BaseModel):
    """Page/window returned by a feed-style extractor."""

    records: list[dict[str, Any]] = Field(default_factory=list)
    next_cursor: str | None = None
