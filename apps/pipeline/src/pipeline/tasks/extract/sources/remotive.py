"""Remotive public feed extractor (no auth).

Remotive's own API terms ask callers not to hit the endpoint more than a
handful of times a day. The extractor always pulls the full unfiltered feed
(no ``category``/``search`` query) and relies on a single sentinel keyword
(``tasks.keywords.providers.remotive``) plus the shared extract cooldown to
cap this to roughly one call per cooldown window, instead of one call per
scoped keyword.
"""

from __future__ import annotations

from typing import Any

from pipeline.schemas.jobs import FeedBatch, RawJobRecord
from pipeline.tasks.extract.sources.base import FeedExtractor
from rich import print

REMOTIVE_API_URL = "https://remotive.com/api/remote-jobs"
USER_AGENT = "SkillPolaris/0.1 (academic research; feed ingest)"


class RemotiveExtractor(FeedExtractor):
    """Pulls the full Remotive remote-jobs feed (unfiltered, no cursor)."""

    def __init__(self, configuration):
        super().__init__(configuration=configuration)
        self.session.headers.update(
            {
                "User-Agent": USER_AGENT,
                "Accept": "application/json",
            }
        )

    @property
    def source_name(self) -> str:
        return "remotive"

    def fetch_batch(
        self,
        cursor: str | None = None,
        *,
        keyword: str | None = None,
    ) -> FeedBatch:
        del cursor, keyword  # single unfiltered pull; see module docstring

        try:
            response = self.session.get(REMOTIVE_API_URL, timeout=30)
            response.raise_for_status()
            payload = response.json()
        except Exception as exc:  # noqa: BLE001 — feed boundary
            print(f"[bold red][RemotiveExtractor] fetch failed: {exc}[/]")
            return FeedBatch(records=[], next_cursor=None)

        jobs = payload.get("jobs") if isinstance(payload, dict) else None
        if not isinstance(jobs, list):
            print("[bold red][RemotiveExtractor] unexpected payload type[/]")
            return FeedBatch(records=[], next_cursor=None)

        records = [
            item for item in jobs if isinstance(item, dict) and item.get("id") is not None
        ]
        return FeedBatch(records=records, next_cursor=None)

    def to_raw_job(
        self,
        payload: dict[str, Any],
        *,
        keyword: str | None = None,
        company_slug: str | None = None,
    ) -> RawJobRecord:
        del company_slug
        return RawJobRecord(
            source=self.source_name,
            external_id=str(payload["id"]),
            extractor_kind=self.extractor_kind,
            keyword=keyword,
            title_raw=payload.get("title") or "",
            description_raw=payload.get("description") or "",
            url=payload.get("url"),
            posted_at_raw=payload.get("publication_date"),
            raw_payload=payload,
        )
