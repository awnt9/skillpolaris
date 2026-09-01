from typing import Literal

from pydantic import BaseModel

KeywordOrigin = Literal[
    "onet",
    "rome",
    "remoteok",
    "remotive",
    "arbeitnow",
    "himalayas",
    "jobicy",
    "landing_jobs",
    "the_muse",
    "other",
]


class SearchKeyword(BaseModel):
    id: int
    keyword: str
    source_scope: str | None = None
    origin: KeywordOrigin
    active: bool = True
    last_searched_at: str | None = None
    raw_jobs_count: int = 0


class SearchKeywordUpsert(BaseModel):
    keyword: str
    source_scope: str | None = None
    origin: KeywordOrigin
    active: bool = True


class KeywordUpsertResult(BaseModel):
    upserted: int
    new_keywords: list[str] = []


class SourcePolicy(BaseModel):
    min_interval_seconds: float = 0.5
    max_retries: int = 2


class ExtractRunResult(BaseModel):
    keywords_used: int = 0
    saved: int = 0
    failed: int = 0
    skipped: int = 0
