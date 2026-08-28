"""Discover Himalayas top-level job categories for the search_keywords catalog.

``parentCategories`` is a small, bounded taxonomy (unlike the noisy
per-job ``categories`` micro-tags) and the ``/jobs/api/search?q=`` endpoint
genuinely filters by it, so each collected category becomes a real,
distinct query — unlike the sentinel-only providers for feeds without
server-side filtering.
"""

from __future__ import annotations

import requests
from pipeline.schemas.extract import SearchKeywordUpsert
from pipeline.tasks.extract.sources.himalayas import HIMALAYAS_BROWSE_URL, USER_AGENT
from pipeline.tasks.keywords.providers.base import KeywordProvider

SOURCE_SCOPE = "himalayas"


class HimalayasCategoryProvider(KeywordProvider):
    """Collects ``parentCategories`` seen on a sample of live Himalayas jobs."""

    def __init__(self, sample_size: int = 100):
        self.sample_size = sample_size

    @property
    def origin(self) -> str:
        return "himalayas"

    def collect(self) -> list[SearchKeywordUpsert]:
        try:
            response = requests.get(
                HIMALAYAS_BROWSE_URL,
                params={"limit": self.sample_size},
                headers={
                    "User-Agent": USER_AGENT,
                    "Accept": "application/json",
                },
                timeout=30,
            )
            response.raise_for_status()
            payload = response.json()
        except (requests.RequestException, ValueError):
            return []

        jobs = payload.get("jobs") if isinstance(payload, dict) else None
        if not isinstance(jobs, list):
            return []

        categories: set[str] = set()
        for item in jobs:
            if not isinstance(item, dict):
                continue
            for category in item.get("parentCategories") or []:
                if isinstance(category, str) and category.strip():
                    categories.add(category.strip())

        return [
            SearchKeywordUpsert(
                keyword=category,
                source_scope=SOURCE_SCOPE,
                origin="himalayas",
            )
            for category in sorted(categories)
        ]
