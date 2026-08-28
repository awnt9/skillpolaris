"""Lever public postings API extractor (no auth)."""

from __future__ import annotations

from typing import Any

from pipeline.schemas.jobs import RawJobRecord
from pipeline.tasks.extract.sources.base import AtsExtractor, handle_api_errors
from rich import print

LEVER_POSTINGS_URL = "https://api.lever.co/v0/postings/{company}"
USER_AGENT = "SkillPolaris/0.1 (academic research; ats ingest)"


class LeverExtractor(AtsExtractor):
    """Syncs all published postings for configured Lever board tokens."""

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
        return "lever"

    @handle_api_errors
    def fetch_board(self, company_slug: str) -> list[dict[str, Any]]:
        url = LEVER_POSTINGS_URL.format(company=company_slug)
        response = self.session.get(
            url,
            params={"mode": "json"},
            timeout=60,
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, list):
            print("[bold red][LeverExtractor] unexpected postings payload[/]")
            return []
        return [item for item in payload if isinstance(item, dict) and item.get("id") is not None]

    def to_raw_job(
        self,
        payload: dict[str, Any],
        *,
        keyword: str | None = None,
        company_slug: str | None = None,
    ) -> RawJobRecord:
        description = payload.get("descriptionPlain") or payload.get("description") or ""
        return RawJobRecord(
            source=self.source_name,
            external_id=str(payload["id"]),
            extractor_kind=self.extractor_kind,
            keyword=keyword or company_slug,
            title_raw=payload.get("text") or "",
            description_raw=description,
            url=payload.get("hostedUrl"),
            posted_at_raw=str(payload.get("createdAt")) if payload.get("createdAt") else None,
            raw_payload=payload,
        )
