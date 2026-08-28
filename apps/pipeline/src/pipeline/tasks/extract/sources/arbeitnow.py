"""Arbeitnow public job-board feed extractor (no auth).

The API has no server-side keyword filter (``tags`` are informational only),
so ``fetch_batch`` always pulls the full board and paginates via ``page``.
A single sentinel keyword (``tasks.keywords.providers.arbeitnow``) triggers
one paginated sweep per cooldown window instead of one per keyword.
"""

from __future__ import annotations

from typing import Any

from pipeline.schemas.jobs import FeedBatch, RawJobRecord
from pipeline.tasks.extract.sources.base import FeedExtractor, get_extractor_logger

ARBEITNOW_API_URL = "https://www.arbeitnow.com/api/job-board-api"
USER_AGENT = "SkillPolaris/0.1 (academic research; feed ingest)"


class ArbeitnowExtractor(FeedExtractor):
    """Pulls Arbeitnow job-board pages, following ``links.next`` for cursors."""

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
        return "arbeitnow"

    def fetch_batch(
        self,
        cursor: str | None = None,
        *,
        keyword: str | None = None,
    ) -> FeedBatch:
        del keyword  # no server-side filter; see module docstring
        params = {"page": cursor} if cursor else None

        try:
            response = self.session.get(ARBEITNOW_API_URL, params=params, timeout=30)
            response.raise_for_status()
            payload = response.json()
        except Exception as exc:  # noqa: BLE001 — feed boundary
            get_extractor_logger().error("[ArbeitnowExtractor] fetch failed: %s", exc)
            return FeedBatch(records=[], next_cursor=None)

        data = payload.get("data") if isinstance(payload, dict) else None
        if not isinstance(data, list):
            get_extractor_logger().error("[ArbeitnowExtractor] unexpected payload type")
            return FeedBatch(records=[], next_cursor=None)

        records = [
            item for item in data if isinstance(item, dict) and item.get("slug") is not None
        ]
        next_url = (payload.get("links") or {}).get("next")
        next_page = None
        if next_url:
            meta = payload.get("meta") or {}
            current_page = meta.get("current_page")
            if isinstance(current_page, int):
                next_page = str(current_page + 1)

        return FeedBatch(records=records, next_cursor=next_page)

    def to_raw_job(
        self,
        payload: dict[str, Any],
        *,
        keyword: str | None = None,
        company_slug: str | None = None,
    ) -> RawJobRecord:
        del company_slug
        created_at = payload.get("created_at")
        return RawJobRecord(
            source=self.source_name,
            external_id=str(payload["slug"]),
            extractor_kind=self.extractor_kind,
            keyword=keyword,
            title_raw=payload.get("title") or "",
            description_raw=payload.get("description") or "",
            url=payload.get("url"),
            posted_at_raw=str(created_at) if created_at is not None else None,
            raw_payload=payload,
        )
