"""Sentinel keyword for The Muse feed extractor.

The Muse supports a ``category`` filter, but publishes no reliable catalog
of valid values, so a single scoped keyword triggers one full paginated
sweep per cooldown window instead of guessing a category list.
"""

from __future__ import annotations

from pipeline.schemas.extract import SearchKeywordUpsert
from pipeline.tasks.keywords.providers.base import KeywordProvider

SOURCE_SCOPE = "the_muse"


class TheMuseKeywordProvider(KeywordProvider):
    @property
    def origin(self) -> str:
        return "the_muse"

    def collect(self) -> list[SearchKeywordUpsert]:
        return [
            SearchKeywordUpsert(
                keyword="all-jobs",
                source_scope=SOURCE_SCOPE,
                origin="the_muse",
            )
        ]
