from typing import Literal

from pydantic import BaseModel

KeywordDimension = Literal["role", "stack", "seniority", "modality", "geo", "other"]
KeywordOrigin = Literal["manual", "esco", "onet", "rome", "remoteok", "other"]


class SearchKeyword(BaseModel):
    id: int
    keyword: str
    dimension: KeywordDimension = "role"
    source_scope: str | None = None
    priority: int = 0
    origin: KeywordOrigin
    active: bool = True
    last_searched_at: str | None = None
    raw_jobs_count: int = 0


class SearchKeywordUpsert(BaseModel):
    keyword: str
    dimension: KeywordDimension = "role"
    source_scope: str | None = None
    priority: int = 0
    origin: KeywordOrigin
    active: bool = True


class SourcePolicy(BaseModel):
    min_interval_seconds: float = 0.5
    max_retries: int = 2


class ExtractRunResult(BaseModel):
    keywords_used: int = 0
    saved: int = 0
    failed: int = 0
