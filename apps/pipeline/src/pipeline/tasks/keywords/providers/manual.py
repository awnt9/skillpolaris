"""Hardcoded keyword seed for extract testing and TFM demos."""

from pipeline.schemas.extract import KeywordDimension, SearchKeywordUpsert
from pipeline.tasks.keywords.providers.base import KeywordProvider

# (keyword, dimension, priority) — higher priority is searched first.
DEFAULT_MANUAL_KEYWORDS: list[tuple[str, KeywordDimension, int]] = [
    ("python", "stack", 10),
    ("javascript", "stack", 10),
    ("typescript", "stack", 10),
    ("java", "stack", 9),
    ("react", "stack", 9),
    ("docker", "stack", 8),
    ("kubernetes", "stack", 8),
    ("backend", "role", 10),
    ("frontend", "role", 10),
    ("devops", "role", 9),
    ("data engineer", "role", 9),
    ("software engineer", "role", 8),
]


class ManualKeywordProvider(KeywordProvider):
    """Upserts a fixed developer-oriented keyword list into search_keywords."""

    def __init__(
        self,
        keywords: list[tuple[str, KeywordDimension, int]] | None = None,
    ):
        self.keywords = keywords or DEFAULT_MANUAL_KEYWORDS

    @property
    def origin(self) -> str:
        return "manual"

    def collect(self) -> list[SearchKeywordUpsert]:
        return [
            SearchKeywordUpsert(
                keyword=keyword,
                dimension=dimension,
                priority=priority,
                origin="manual",
            )
            for keyword, dimension, priority in self.keywords
        ]
