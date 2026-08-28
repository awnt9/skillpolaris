"""Recruitee public offers API extractor (no auth)."""

from __future__ import annotations

from typing import Any

from pipeline.schemas.jobs import RawJobRecord
from pipeline.tasks.extract.sources.base import (
    AtsExtractor,
    get_extractor_logger,
    handle_api_errors,
    html_to_text,
)

RECRUITEE_OFFERS_URL = "https://{company}.recruitee.com/api/offers/"
USER_AGENT = "SkillPolaris/0.1 (academic research; ats ingest)"


class RecruiteeExtractor(AtsExtractor):
    """Syncs all published offers for configured Recruitee company subdomains."""

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
        return "recruitee"

    @handle_api_errors
    def fetch_board(self, company_slug: str) -> list[dict[str, Any]]:
        url = RECRUITEE_OFFERS_URL.format(company=company_slug)
        response = self.session.get(url, timeout=30)
        response.raise_for_status()
        payload = response.json()
        offers = payload.get("offers") or []
        if not isinstance(offers, list):
            get_extractor_logger().error("[RecruiteeExtractor] unexpected offers payload")
            return []
        return [
            offer
            for offer in offers
            if isinstance(offer, dict) and offer.get("id") is not None
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
            external_id=str(payload["id"]),
            extractor_kind=self.extractor_kind,
            keyword=keyword or company_slug,
            title_raw=payload.get("title") or "",
            description_raw=html_to_text(description) if description else "",
            url=payload.get("careers_url") or payload.get("careers_apply_url"),
            posted_at_raw=payload.get("published_at") or payload.get("created_at"),
            raw_payload=payload,
        )
