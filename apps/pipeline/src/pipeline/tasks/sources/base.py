from abc import ABC, abstractmethod
from functools import wraps
from json import JSONDecodeError
from typing import Any

import requests
from pipeline.schemas.jobs import ExtractorKind, FeedBatch, RawJobRecord
from requests import RequestException
from rich import print


def handle_api_errors(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        class_name = self.__class__.__name__

        try:
            return func(self, *args, **kwargs)
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code
            if status == 403:
                print(
                    f"[bold red][{class_name}] Forbidden (403): "
                    f"Possible block of IP or User-Agent.[/]"
                )
            elif status == 429:
                print(f"[bold red][{class_name}] Too Many Requests (429)[/]")
            else:
                print(f"[bold red][{class_name}] HTTP Error {status}: {e}[/]")
            return []
        except JSONDecodeError:
            print(f"[bold red][{class_name}] Error: response is not a valid JSON.[/]")
            return []
        except RequestException as e:
            print(f"[bold red][{class_name}] Error: {e}[/]")
            return []
        except (KeyError, TypeError) as e:
            print(f"[bold red][{class_name}] Error on response structure: {e}[/]")
            return []

    return wrapper


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
    """Feed sources: optional tag/keyword windows and/or cursor pagination."""

    @property
    def extractor_kind(self) -> ExtractorKind:
        return "feed"

    @abstractmethod
    def fetch_batch(
        self,
        cursor: str | None = None,
        *,
        keyword: str | None = None,
    ) -> FeedBatch:
        """Fetch the next feed window, optionally filtered by keyword/tag."""


class AtsExtractor(BaseExtractor):
    """ATS board sync: all jobs for a company slug."""

    @property
    def extractor_kind(self) -> ExtractorKind:
        return "ats"

    @abstractmethod
    def fetch_board(self, company_slug: str) -> list[dict[str, Any]]:
        """Return all postings for a company board."""
