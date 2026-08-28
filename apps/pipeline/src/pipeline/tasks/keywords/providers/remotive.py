"""Sentinel keyword for the Remotive feed extractor.

Remotive's own API terms ask callers not to hit the endpoint more than a
handful of times a day. A single scoped keyword (combined with the shared
extract cooldown) triggers one unfiltered feed pull per cooldown window
instead of one call per keyword, so we intentionally avoid seeding a
per-category catalog here.
"""

from __future__ import annotations

from pipeline.schemas.extract import SearchKeywordUpsert
from pipeline.tasks.keywords.providers.base import KeywordProvider

SOURCE_SCOPE = "remotive"


class RemotiveKeywordProvider(KeywordProvider):
    @property
    def origin(self) -> str:
        return "remotive"

    def collect(self) -> list[SearchKeywordUpsert]:
        return [
            SearchKeywordUpsert(
                keyword="remote-jobs",
                source_scope=SOURCE_SCOPE,
                origin="remotive",
            )
        ]
