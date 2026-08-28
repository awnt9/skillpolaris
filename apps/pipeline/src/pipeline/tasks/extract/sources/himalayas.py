"""Himalayas public jobs feed extractor (no auth)."""

from __future__ import annotations

from typing import Any

from pipeline.schemas.jobs import FeedBatch, RawJobRecord
from pipeline.tasks.extract.sources.base import FeedExtractor
from rich import print

HIMALAYAS_BROWSE_URL = "https://himalayas.app/jobs/api"
HIMALAYAS_SEARCH_URL = "https://himalayas.app/jobs/api/search"
USER_AGENT = "SkillPolaris/0.1 (academic research; feed ingest)"


class HimalayasExtractor(FeedExtractor):
    """Browses the full feed (cursor) or searches by keyword (page)."""

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
        return "himalayas"

    def fetch_batch(
        self,
        cursor: str | None = None,
        *,
        keyword: str | None = None,
    ) -> FeedBatch:
        try:
            if keyword:
                response = self.session.get(
                    HIMALAYAS_SEARCH_URL,
                    params={"q": keyword, "page": cursor or "1"},
                    timeout=30,
                )
            else:
                params: dict[str, str] = {"limit": "20"}
                if cursor:
                    params["cursor"] = cursor
                response = self.session.get(HIMALAYAS_BROWSE_URL, params=params, timeout=30)
            response.raise_for_status()
            payload = response.json()
        except Exception as exc:  # noqa: BLE001 — feed boundary
            print(f"[bold red][HimalayasExtractor] fetch failed: {exc}[/]")
            return FeedBatch(records=[], next_cursor=None)

        jobs = payload.get("jobs") if isinstance(payload, dict) else None
        if not isinstance(jobs, list):
            print("[bold red][HimalayasExtractor] unexpected payload type[/]")
            return FeedBatch(records=[], next_cursor=None)

        records = [
            item for item in jobs if isinstance(item, dict) and item.get("guid") is not None
        ]

        if keyword:
            offset = payload.get("offset")
            limit = payload.get("limit")
            total_count = payload.get("totalCount")
            next_cursor = None
            if isinstance(offset, int) and isinstance(limit, int) and isinstance(total_count, int):
                if offset + limit < total_count:
                    current_page = int(cursor) if cursor and cursor.isdigit() else 1
                    next_cursor = str(current_page + 1)
        else:
            next_cursor = payload.get("nextCursor")

        return FeedBatch(records=records, next_cursor=next_cursor)

    def to_raw_job(
        self,
        payload: dict[str, Any],
        *,
        keyword: str | None = None,
        company_slug: str | None = None,
    ) -> RawJobRecord:
        del company_slug
        pub_date = payload.get("pubDate")
        return RawJobRecord(
            source=self.source_name,
            external_id=str(payload["guid"]),
            extractor_kind=self.extractor_kind,
            keyword=keyword,
            title_raw=payload.get("title") or "",
            description_raw=payload.get("description") or payload.get("excerpt") or "",
            url=payload.get("applicationLink") or payload.get("guid"),
            posted_at_raw=str(pub_date) if pub_date is not None else None,
            raw_payload=payload,
        )
