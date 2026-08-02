from abc import ABC, abstractmethod
from typing import Any

import requests

from pipeline.domain.models import ExtractorKind, FeedBatch, RawJobRecord


class BaseExtractor(ABC):
    """Shared session/config for all source connectors."""

    def __init__(self, configuration):
        self.session = requests.Session()
        self.configuration = configuration

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Stable source identifier stored in raw_jobs."""

    @property
    @abstractmethod
    def extractor_kind(self) -> ExtractorKind:
        """Acquisition mode: detail, feed, or ats."""

    @abstractmethod
    def to_raw_job(
        self,
        payload: dict[str, Any],
        *,
        keyword: str | None = None,
        company_slug: str | None = None,
    ) -> RawJobRecord:
        """Map a source-specific payload into a RawJobRecord."""


class DetailExtractor(BaseExtractor):
    """Two-step sources: search IDs, then fetch detail."""

    @property
    def extractor_kind(self) -> ExtractorKind:
        return "detail"

    @abstractmethod
    def search_ids(self, keyword: str, page: int) -> list[str]:
        """Return job IDs for a keyword/page."""

    @abstractmethod
    def fetch_detail(self, job_id: str) -> dict[str, Any] | None:
        """Return the full offer payload for a job ID."""


class FeedExtractor(BaseExtractor):
    """Full-feed / cursor-paginated sources (no keyword search)."""

    @property
    def extractor_kind(self) -> ExtractorKind:
        return "feed"

    @abstractmethod
    def fetch_batch(self, cursor: str | None = None) -> FeedBatch:
        """Fetch the next feed window."""


class AtsExtractor(BaseExtractor):
    """ATS board sync: all jobs for a company slug."""

    @property
    def extractor_kind(self) -> ExtractorKind:
        return "ats"

    @abstractmethod
    def fetch_board(self, company_slug: str) -> list[dict[str, Any]]:
        """Return all postings for a company board."""
