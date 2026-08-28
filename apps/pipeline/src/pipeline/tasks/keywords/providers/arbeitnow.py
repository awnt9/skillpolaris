"""Sentinel keyword for the Arbeitnow feed extractor.

The job-board-api has no server-side keyword filter, so a single scoped
keyword triggers one full paginated sweep per cooldown window instead of
one identical sweep per keyword.
"""

from __future__ import annotations

from pipeline.schemas.extract import SearchKeywordUpsert
from pipeline.tasks.keywords.providers.base import KeywordProvider

SOURCE_SCOPE = "arbeitnow"


class ArbeitnowKeywordProvider(KeywordProvider):
    @property
    def origin(self) -> str:
        return "arbeitnow"

    def collect(self) -> list[SearchKeywordUpsert]:
        return [
            SearchKeywordUpsert(
                keyword="job-board",
                source_scope=SOURCE_SCOPE,
                origin="arbeitnow",
            )
        ]
