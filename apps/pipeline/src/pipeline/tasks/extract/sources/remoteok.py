"""RemoteOK public feed extractor (no auth)."""

from __future__ import annotations

from typing import Any

from pipeline.schemas.jobs import FeedBatch, RawJobRecord
from pipeline.tasks.extract.sources.base import FeedExtractor, get_extractor_logger

REMOTEOK_API_URL = "https://remoteok.com/api"
USER_AGENT = "SkillPolaris/0.1 (academic research; feed ingest)"


class RemoteOkExtractor(FeedExtractor):
    """Pulls RemoteOK JSON windows, optionally filtered by board tag."""

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
        return "remoteok"

    def fetch_batch(
        self,
        cursor: str | None = None,
        *,
        keyword: str | None = None,
    ) -> FeedBatch:
        # RemoteOK returns a flat recent window; no cursor pagination.
        del cursor
        params: dict[str, str] = {}
        if keyword:
            params["tag"] = keyword

        try:
            response = self.session.get(
                REMOTEOK_API_URL,
                params=params or None,
                timeout=30,
            )
            response.raise_for_status()
            payload = response.json()
        except Exception as exc:  # noqa: BLE001 — feed boundary
            get_extractor_logger().error("[RemoteOkExtractor] fetch failed: %s", exc)
            return FeedBatch(records=[], next_cursor=None)

        if not isinstance(payload, list):
            get_extractor_logger().error("[RemoteOkExtractor] unexpected payload type")
            return FeedBatch(records=[], next_cursor=None)

        records = [
            item
            for item in payload
            if isinstance(item, dict) and item.get("id") is not None
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
        description = payload.get("description") or ""
        return RawJobRecord(
            source=self.source_name,
            external_id=str(payload["id"]),
            extractor_kind=self.extractor_kind,
            keyword=keyword,
            title_raw=payload.get("position") or "",
            description_raw=description,
            url=payload.get("url") or payload.get("apply_url"),
            posted_at_raw=payload.get("date"),
            raw_payload=payload,
        )
