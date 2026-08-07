"""Discover popular Stack Overflow tags for the search_keywords catalog."""

from __future__ import annotations

import re

import requests
from pipeline.schemas.extract import SearchKeywordUpsert
from pipeline.tasks.keywords.providers.base import KeywordProvider

STACKOVERFLOW_TAGS_URL = "https://api.stackexchange.com/2.3/tags"
USER_AGENT = "SkillPolaris/0.1 (keyword-sync)"

_VERSION_SUFFIX = re.compile(
    r"-(?:[0-9]+(?:\.[0-9x]+)*|x)$",
    re.IGNORECASE,
)


def _normalize_tag(name: str) -> str | None:
    raw = name.strip().lower()
    if not raw:
        return None
    # Drop versioned variants (python-3.x); the base tag is collected separately.
    if _VERSION_SUFFIX.search(raw):
        return None
    return raw


class StackOverflowTagProvider(KeywordProvider):
    """Collects popular Stack Overflow tags as global search keywords.

    Filtering is popularity-only (``min_count`` / pages). Fine-tuning is via
    ``search_keywords.active`` (HITL), not hardcoded lists.
    """

    def __init__(
        self,
        *,
        pages: int = 2,
        page_size: int = 100,
        min_count: int = 50_000,
        api_key: str | None = None,
    ):
        self.pages = max(1, pages)
        self.page_size = min(100, max(1, page_size))
        self.min_count = min_count
        self.api_key = api_key

    @property
    def origin(self) -> str:
        return "stackoverflow"

    def collect(self) -> list[SearchKeywordUpsert]:
        keywords: set[str] = set()

        for page in range(1, self.pages + 1):
            params: dict[str, str | int] = {
                "site": "stackoverflow",
                "order": "desc",
                "sort": "popular",
                "pagesize": self.page_size,
                "page": page,
            }
            if self.api_key:
                params["key"] = self.api_key

            try:
                response = requests.get(
                    STACKOVERFLOW_TAGS_URL,
                    params=params,
                    headers={
                        "User-Agent": USER_AGENT,
                        "Accept": "application/json",
                    },
                    timeout=30,
                )
                response.raise_for_status()
                payload = response.json()
            except (requests.RequestException, ValueError):
                break

            items = payload.get("items") or []
            if not isinstance(items, list):
                break

            for item in items:
                if not isinstance(item, dict):
                    continue
                name = item.get("name")
                count = item.get("count") or 0
                if not isinstance(name, str) or count < self.min_count:
                    continue
                normalized = _normalize_tag(name)
                if normalized:
                    keywords.add(normalized)

            if not payload.get("has_more"):
                break

        return [
            SearchKeywordUpsert(keyword=keyword, origin="stackoverflow")
            for keyword in sorted(keywords)
        ]
