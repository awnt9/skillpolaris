"""Jobicy public remote-jobs feed extractor (no auth)."""

from __future__ import annotations

from typing import Any

from pipeline.schemas.jobs import FeedBatch, RawJobRecord
from pipeline.tasks.extract.sources.base import FeedExtractor
from rich import print

JOBICY_API_URL = "https://jobicy.com/api/v2/remote-jobs"
USER_AGENT = "SkillPolaris/0.1 (academic research; feed ingest)"


class JobicyExtractor(FeedExtractor):
    """Pulls Jobicy remote jobs, optionally filtered by ``industry`` slug."""

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
        return "jobicy"

    def fetch_batch(
        self,
        cursor: str | None = None,
        *,
        keyword: str | None = None,
    ) -> FeedBatch:
        # Single-window feed: Jobicy has no page/offset param, only `count`.
        del cursor
        params: dict[str, str] = {"count": "50"}
        if keyword:
            params["industry"] = keyword

        try:
            response = self.session.get(JOBICY_API_URL, params=params, timeout=30)
            response.raise_for_status()
            payload = response.json()
        except Exception as exc:  # noqa: BLE001 — feed boundary
            print(f"[bold red][JobicyExtractor] fetch failed: {exc}[/]")
            return FeedBatch(records=[], next_cursor=None)

        jobs = payload.get("jobs") if isinstance(payload, dict) else None
        if not isinstance(jobs, list):
            print("[bold red][JobicyExtractor] unexpected payload type[/]")
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
            title_raw=payload.get("jobTitle") or "",
            description_raw=payload.get("jobDescription") or payload.get("jobExcerpt") or "",
            url=payload.get("url"),
            posted_at_raw=payload.get("pubDate"),
            raw_payload=payload,
        )
