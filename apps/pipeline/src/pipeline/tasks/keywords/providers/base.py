from abc import ABC, abstractmethod

from pipeline.schemas.extract import SearchKeywordUpsert


class KeywordProvider(ABC):
    """Produces keyword records for the search_keywords catalog."""

    @property
    @abstractmethod
    def origin(self) -> str:
        """Value stored in search_keywords.origin."""

    @abstractmethod
    def collect(self) -> list[SearchKeywordUpsert]:
        """Return keywords to upsert into Postgres."""
