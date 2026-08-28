"""Discover Jobicy's official industry catalog for the search_keywords catalog.

``?get=industries`` returns Jobicy's own predefined ``industrySlug`` values,
which the feed's ``industry`` query param genuinely filters by.
"""

from __future__ import annotations

import requests
from pipeline.schemas.extract import SearchKeywordUpsert
from pipeline.tasks.extract.sources.jobicy import JOBICY_API_URL, USER_AGENT
from pipeline.tasks.keywords.providers.base import KeywordProvider

SOURCE_SCOPE = "jobicy"


class JobicyIndustryProvider(KeywordProvider):
    """Collects Jobicy's predefined ``industrySlug`` catalog."""

    @property
    def origin(self) -> str:
        return "jobicy"

    def collect(self) -> list[SearchKeywordUpsert]:
        try:
            response = requests.get(
                JOBICY_API_URL,
                params={"get": "industries"},
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

        industries = payload.get("industries") if isinstance(payload, dict) else None
        if not isinstance(industries, list):
            return []

        slugs: set[str] = set()
        for item in industries:
            if not isinstance(item, dict):
                continue
            slug = item.get("industrySlug")
            if isinstance(slug, str) and slug.strip():
                slugs.add(slug.strip())

        return [
            SearchKeywordUpsert(
                keyword=slug,
                source_scope=SOURCE_SCOPE,
                origin="jobicy",
            )
            for slug in sorted(slugs)
        ]
