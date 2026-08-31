"""Landing.Jobs public feed extractor (no auth).

The public listing endpoint has no server-side keyword filter, so
``fetch_batch`` always pulls the full board and paginates via
``limit``/``offset``. A single sentinel keyword
(``tasks.keywords.providers.landing_jobs``) triggers one paginated sweep per
cooldown window instead of one per keyword.
"""

from __future__ import annotations

from typing import Any

from pipeline.schemas.jobs import FeedBatch, RawJobRecord
from pipeline.tasks.extract.sources.base import FeedExtractor, get_extractor_logger

LANDING_JOBS_API_URL = "https://landing.jobs/api/v1/jobs"
USER_AGENT = "SkillPolaris/0.1 (academic research; feed ingest)"
PAGE_SIZE = 50


class LandingJobsExtractor(FeedExtractor):
    """Pulls Landing.Jobs postings, paginating via ``offset``."""

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
        return "landing_jobs"

    def fetch_batch(
        self,
        cursor: str | None = None,
        *,
        keyword: str | None = None,
    ) -> FeedBatch:
        del keyword  # no server-side filter; see module docstring
        offset = int(cursor) if cursor and cursor.isdigit() else 0

        try:
            response = self.session.get(
                LANDING_JOBS_API_URL,
                params={"limit": PAGE_SIZE, "offset": offset},
                timeout=30,
            )
            response.raise_for_status()
            payload = response.json()
        except Exception as exc:  # noqa: BLE001 — feed boundary
            get_extractor_logger().error("[LandingJobsExtractor] fetch failed: %s", exc)
            return FeedBatch(records=[], next_cursor=None)

        if not isinstance(payload, list):
            get_extractor_logger().error("[LandingJobsExtractor] unexpected payload type")
            return FeedBatch(records=[], next_cursor=None)

        records = [
            item for item in payload if isinstance(item, dict) and item.get("id") is not None
        ]
        next_cursor = str(offset + PAGE_SIZE) if len(records) == PAGE_SIZE else None
        return FeedBatch(records=records, next_cursor=next_cursor)

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
            description_raw=payload.get("role_description") or "",
            url=payload.get("url"),
            posted_at_raw=payload.get("published_at"),
            raw_payload=payload,
        )
