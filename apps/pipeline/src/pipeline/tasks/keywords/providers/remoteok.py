"""Discover RemoteOK board tags for the search_keywords catalog."""

from __future__ import annotations

import requests
from pipeline.schemas.extract import SearchKeywordUpsert
from pipeline.tasks.keywords.providers.base import KeywordProvider
from pipeline.tasks.extract.sources.remoteok import REMOTEOK_API_URL, USER_AGENT

SOURCE_SCOPE = "remoteok"


class RemoteOkTagProvider(KeywordProvider):
    """Collects tags present on the current RemoteOK public board feed.

    Tags are market-driven (whatever RemoteOK labels on the live board),
    scoped to ``remoteok`` so they are not reused as France Travail keywords.
    """

    @property
    def origin(self) -> str:
        return "remoteok"

    def collect(self) -> list[SearchKeywordUpsert]:
        try:
            response = requests.get(
                REMOTEOK_API_URL,
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

        if not isinstance(payload, list):
            return []

        tags: set[str] = set()
        for item in payload:
            if not isinstance(item, dict) or item.get("id") is None:
                continue
            for tag in item.get("tags") or []:
                if not isinstance(tag, str):
                    continue
                normalized = tag.strip().lower()
                if normalized:
                    tags.add(normalized)

        return [
            SearchKeywordUpsert(
                keyword=tag,
                source_scope=SOURCE_SCOPE,
                origin="remoteok",
            )
            for tag in sorted(tags)
        ]
