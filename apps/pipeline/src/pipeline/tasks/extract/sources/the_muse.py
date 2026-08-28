"""The Muse public jobs feed extractor (no auth for light usage).

The API supports a ``category`` filter, but The Muse publishes no reliable
catalog of valid category values, so ``fetch_batch`` always pulls the full
unfiltered feed and paginates via ``page``. A single sentinel keyword
(``tasks.keywords.providers.the_muse``) triggers one paginated sweep per
cooldown window instead of one per keyword.
"""

from __future__ import annotations

from typing import Any

from pipeline.schemas.jobs import FeedBatch, RawJobRecord
from pipeline.tasks.extract.sources.base import FeedExtractor
from rich import print

THE_MUSE_API_URL = "https://www.themuse.com/api/public/jobs"
USER_AGENT = "SkillPolaris/0.1 (academic research; feed ingest)"


class TheMuseExtractor(FeedExtractor):
    """Pulls The Muse job pages (0-indexed ``page`` param)."""

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
        return "the_muse"

    def fetch_batch(
        self,
        cursor: str | None = None,
        *,
        keyword: str | None = None,
    ) -> FeedBatch:
        del keyword  # no reliable category catalog; see module docstring
        page = int(cursor) if cursor and cursor.isdigit() else 0

        try:
            response = self.session.get(
                THE_MUSE_API_URL,
                params={"page": page},
                timeout=30,
            )
            response.raise_for_status()
            payload = response.json()
        except Exception as exc:  # noqa: BLE001 — feed boundary
            print(f"[bold red][TheMuseExtractor] fetch failed: {exc}[/]")
            return FeedBatch(records=[], next_cursor=None)

        results = payload.get("results") if isinstance(payload, dict) else None
        if not isinstance(results, list):
            print("[bold red][TheMuseExtractor] unexpected payload type[/]")
            return FeedBatch(records=[], next_cursor=None)

        records = [
            item for item in results if isinstance(item, dict) and item.get("id") is not None
        ]
        page_count = payload.get("page_count")
        next_cursor = (
            str(page + 1) if isinstance(page_count, int) and page + 1 < page_count else None
        )
        return FeedBatch(records=records, next_cursor=next_cursor)

    def to_raw_job(
        self,
        payload: dict[str, Any],
        *,
        keyword: str | None = None,
        company_slug: str | None = None,
    ) -> RawJobRecord:
        del company_slug
        refs = payload.get("refs") or {}
        return RawJobRecord(
            source=self.source_name,
            external_id=str(payload["id"]),
            extractor_kind=self.extractor_kind,
            keyword=keyword,
            title_raw=payload.get("name") or "",
            description_raw=payload.get("contents") or "",
            url=refs.get("landing_page"),
            posted_at_raw=payload.get("publication_date"),
            raw_payload=payload,
        )
