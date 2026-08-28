"""Greenhouse public Job Board API extractor (no auth)."""

from __future__ import annotations

import re
from html import unescape
from typing import Any

from pipeline.schemas.jobs import RawJobRecord
from pipeline.tasks.extract.sources.base import (
    AtsExtractor,
    get_extractor_logger,
    handle_api_errors,
)

GREENHOUSE_JOBS_URL = (
    "https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs"
)
USER_AGENT = "SkillPolaris/0.1 (academic research; ats ingest)"

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


def _html_to_text(value: str) -> str:
    # Greenhouse often double-encodes HTML entities in ``content``.
    text = unescape(unescape(value))
    text = _TAG_RE.sub(" ", text)
    return _WS_RE.sub(" ", text).strip()


class GreenhouseExtractor(AtsExtractor):
    """Syncs all published jobs for configured Greenhouse board tokens."""

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
        return "greenhouse"

    @handle_api_errors
    def fetch_board(self, company_slug: str) -> list[dict[str, Any]]:
        url = GREENHOUSE_JOBS_URL.format(board_token=company_slug)
        response = self.session.get(
            url,
            params={"content": "true"},
            timeout=60,
        )
        response.raise_for_status()
        payload = response.json()
        jobs = payload.get("jobs") or []
        if not isinstance(jobs, list):
            get_extractor_logger().error("[GreenhouseExtractor] unexpected jobs payload")
            return []
        return [job for job in jobs if isinstance(job, dict) and job.get("id") is not None]

    def to_raw_job(
        self,
        payload: dict[str, Any],
        *,
        keyword: str | None = None,
        company_slug: str | None = None,
    ) -> RawJobRecord:
        content = payload.get("content") or ""
        description = _html_to_text(content) if content else ""
        return RawJobRecord(
            source=self.source_name,
            external_id=str(payload["id"]),
            extractor_kind=self.extractor_kind,
            keyword=keyword or company_slug,
            title_raw=payload.get("title") or "",
            description_raw=description,
            url=payload.get("absolute_url"),
            posted_at_raw=payload.get("first_published") or payload.get("updated_at"),
            raw_payload=payload,
        )
