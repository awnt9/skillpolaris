"""WeWorkRemotely public RSS feed extractor (no auth)."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Any

from pipeline.schemas.jobs import FeedBatch, RawJobRecord
from pipeline.tasks.extract.sources.base import FeedExtractor, get_extractor_logger, html_to_text

FEED_URL = "https://weworkremotely.com/remote-jobs.rss"
USER_AGENT = "SkillPolaris/0.1 (academic research; feed ingest)"


class WeWorkRemotelyExtractor(FeedExtractor):
    """Pulls the current open-listings RSS feed in a single unscoped batch."""

    def __init__(self, configuration):
        super().__init__(configuration=configuration)
        self.session.headers.update({"User-Agent": USER_AGENT})

    @property
    def source_name(self) -> str:
        return "weworkremotely"

    def fetch_batch(
        self,
        cursor: str | None = None,
        *,
        keyword: str | None = None,
    ) -> FeedBatch:
        del keyword
        if cursor is not None:
            # Flat feed, no pagination — everything comes back in one batch.
            return FeedBatch(records=[], next_cursor=None)

        try:
            response = self.session.get(FEED_URL, timeout=30)
            response.raise_for_status()
            root = ET.fromstring(response.content)
        except Exception as exc:  # noqa: BLE001 — feed boundary
            get_extractor_logger().error("[WeWorkRemotelyExtractor] fetch failed: %s", exc)
            return FeedBatch(records=[], next_cursor=None)

        records = []
        for item in root.iter("item"):
            guid = item.findtext("guid") or item.findtext("link")
            if not guid:
                continue
            records.append(
                {
                    "guid": guid,
                    "title": item.findtext("title") or "",
                    "description": item.findtext("description") or "",
                    "link": item.findtext("link"),
                    "pubDate": item.findtext("pubDate"),
                }
            )

        return FeedBatch(records=records, next_cursor=None)

    def to_raw_job(
        self,
        payload: dict[str, Any],
        *,
        keyword: str | None = None,
        company_slug: str | None = None,
    ) -> RawJobRecord:
        del company_slug
        description = payload.get("description") or ""
        return RawJobRecord(
            source=self.source_name,
            external_id=str(payload["guid"]),
            extractor_kind=self.extractor_kind,
            keyword=keyword,
            title_raw=payload.get("title") or "",
            description_raw=html_to_text(description) if description else "",
            url=payload.get("link"),
            posted_at_raw=payload.get("pubDate"),
            raw_payload=payload,
        )
