"""Hardcoded keyword seed for extract testing and TFM demos."""

from pipeline.schemas.extract import SearchKeywordUpsert
from pipeline.tasks.keywords.providers.base import KeywordProvider

DEFAULT_MANUAL_KEYWORDS: list[str] = [
    "python",
    "javascript",
    "typescript",
    "java",
    "react",
    "docker",
    "kubernetes",
    "backend",
    "frontend",
    "devops",
    "data engineer",
    "software engineer",
]


class ManualKeywordProvider(KeywordProvider):
    """Upserts a fixed developer-oriented keyword list into search_keywords."""

    def __init__(self, keywords: list[str] | None = None):
        self.keywords = keywords or DEFAULT_MANUAL_KEYWORDS

    @property
    def origin(self) -> str:
        return "manual"

    def collect(self) -> list[SearchKeywordUpsert]:
        return [
            SearchKeywordUpsert(keyword=keyword, origin="manual")
            for keyword in self.keywords
        ]
