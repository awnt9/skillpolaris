"""Workable public account jobs API extractor (no auth)."""

from __future__ import annotations

from typing import Any

from pipeline.schemas.jobs import RawJobRecord
from pipeline.tasks.extract.sources.base import (
    AtsExtractor,
    get_extractor_logger,
    handle_api_errors,
    html_to_text,
)

WORKABLE_ACCOUNT_URL = "https://www.workable.com/api/accounts/{account}"
USER_AGENT = "SkillPolaris/0.1 (academic research; ats ingest)"


class WorkableExtractor(AtsExtractor):
    """Syncs all public jobs for configured Workable account subdomains."""

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
        return "workable"

    @handle_api_errors
    def fetch_board(self, company_slug: str) -> list[dict[str, Any]]:
        url = WORKABLE_ACCOUNT_URL.format(account=company_slug)
        # `details=true` is required to get full job descriptions back.
        response = self.session.get(url, params={"details": "true"}, timeout=30)
        response.raise_for_status()
        payload = response.json()
        jobs = payload.get("jobs") or []
        if not isinstance(jobs, list):
            get_extractor_logger().error("[WorkableExtractor] unexpected jobs payload")
            return []
        return [
            job
            for job in jobs
            if isinstance(job, dict) and job.get("shortcode") is not None
        ]

    def to_raw_job(
        self,
        payload: dict[str, Any],
        *,
        keyword: str | None = None,
        company_slug: str | None = None,
    ) -> RawJobRecord:
        description = payload.get("description") or ""
        return RawJobRecord(
            source=self.source_name,
            external_id=str(payload["shortcode"]),
            extractor_kind=self.extractor_kind,
            keyword=keyword or company_slug,
            title_raw=payload.get("title") or "",
            description_raw=html_to_text(description) if description else "",
            url=payload.get("url") or payload.get("application_url"),
            posted_at_raw=payload.get("published_on") or payload.get("created_at"),
            raw_payload=payload,
        )
