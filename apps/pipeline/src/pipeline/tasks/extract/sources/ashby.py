"""Ashby public job board API extractor (no auth)."""

from __future__ import annotations

from typing import Any

from pipeline.schemas.jobs import RawJobRecord
from pipeline.tasks.extract.sources.base import (
    AtsExtractor,
    get_extractor_logger,
    handle_api_errors,
)

ASHBY_JOB_BOARD_URL = "https://api.ashbyhq.com/posting-api/job-board/{board_name}"
USER_AGENT = "SkillPolaris/0.1 (academic research; ats ingest)"


class AshbyExtractor(AtsExtractor):
    """Syncs all listed postings for configured Ashby job board names."""

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
        return "ashby"

    @handle_api_errors
    def fetch_board(self, company_slug: str) -> list[dict[str, Any]]:
        url = ASHBY_JOB_BOARD_URL.format(board_name=company_slug)
        response = self.session.get(url, timeout=60)
        response.raise_for_status()
        payload = response.json()
        jobs = payload.get("jobs") or []
        if not isinstance(jobs, list):
            get_extractor_logger().error("[AshbyExtractor] unexpected jobs payload")
            return []
        return [job for job in jobs if isinstance(job, dict) and job.get("id") is not None]

    def to_raw_job(
        self,
        payload: dict[str, Any],
        *,
        keyword: str | None = None,
        company_slug: str | None = None,
    ) -> RawJobRecord:
        description = payload.get("descriptionPlain") or ""
        return RawJobRecord(
            source=self.source_name,
            external_id=str(payload["id"]),
            extractor_kind=self.extractor_kind,
            keyword=keyword or company_slug,
            title_raw=payload.get("title") or "",
            description_raw=description,
            url=payload.get("jobUrl") or payload.get("applyUrl"),
            posted_at_raw=payload.get("publishedAt"),
            raw_payload=payload,
        )
