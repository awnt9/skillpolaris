"""ESCO computer-programming languages for the search_keywords catalog."""

from __future__ import annotations

import re

import requests
from pipeline.schemas.extract import SearchKeywordUpsert
from pipeline.tasks.keywords.providers.base import KeywordProvider

ESCO_SKILL_URL = "https://ec.europa.eu/esco/api/resource/skill"
# Hub skill whose narrowerSkill list is programming languages / related tech.
COMPUTER_PROGRAMMING_URI = (
    "http://data.europa.eu/esco/skill/21d2f96d-35f7-4e3f-9745-c533d2dd6e97"
)

_COMPUTER_PROGRAMMING_SUFFIX = re.compile(
    r"\s*\(computer programming\)\s*$",
    re.IGNORECASE,
)

# Phrases that are not useful as board search keywords.
_SKIP_TITLES: frozenset[str] = frozenset(
    {
        "web programming",
        "visual studio .net",
        "sap r3",
        "openedge advanced business language",
    }
)


def _normalize_language_title(title: str) -> str | None:
    cleaned = _COMPUTER_PROGRAMMING_SUFFIX.sub("", title).strip()
    if not cleaned:
        return None
    if cleaned.lower() in _SKIP_TITLES:
        return None
    # Prefer lowercase for extract consistency with SO / RemoteOK tags.
    return cleaned.lower()


class EscoProgrammingProvider(KeywordProvider):
    """Loads programming-language skills under ESCO ``computer programming``.

    Complements :class:`EscoKeywordProvider` (ISCO occupations) with a stable
    official language list. Modern tools missing from ESCO (Docker, React, …)
    are expected from Stack Overflow / RemoteOK providers.
    """

    def __init__(self, hub_uri: str = COMPUTER_PROGRAMMING_URI):
        self.hub_uri = hub_uri

    @property
    def origin(self) -> str:
        return "esco"

    def collect(self) -> list[SearchKeywordUpsert]:
        try:
            response = requests.get(
                ESCO_SKILL_URL,
                params={"uri": self.hub_uri, "language": "en"},
                timeout=30,
            )
            response.raise_for_status()
            payload = response.json()
        except (requests.RequestException, ValueError):
            return []

        narrower = payload.get("_links", {}).get("narrowerSkill") or []
        if isinstance(narrower, dict):
            narrower = [narrower]

        keywords: set[str] = set()
        for item in narrower:
            if not isinstance(item, dict):
                continue
            title = item.get("title")
            if not isinstance(title, str):
                continue
            normalized = _normalize_language_title(title)
            if normalized:
                keywords.add(normalized)

        return [
            SearchKeywordUpsert(keyword=keyword, origin="esco")
            for keyword in sorted(keywords)
        ]
