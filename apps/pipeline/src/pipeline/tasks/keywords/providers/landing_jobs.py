"""Sentinel keyword for the Landing.Jobs feed extractor.

The public listing endpoint has no server-side keyword filter (``tags``
in the response do not narrow results when echoed back as a query param),
so a single scoped keyword triggers one full paginated sweep per cooldown
window instead of one identical sweep per keyword.
"""

from __future__ import annotations

from pipeline.schemas.extract import SearchKeywordUpsert
from pipeline.tasks.keywords.providers.base import KeywordProvider

SOURCE_SCOPE = "landing_jobs"


class LandingJobsKeywordProvider(KeywordProvider):
    @property
    def origin(self) -> str:
        return "landing_jobs"

    def collect(self) -> list[SearchKeywordUpsert]:
        return [
            SearchKeywordUpsert(
                keyword="all-jobs",
                source_scope=SOURCE_SCOPE,
                origin="landing_jobs",
            )
        ]
