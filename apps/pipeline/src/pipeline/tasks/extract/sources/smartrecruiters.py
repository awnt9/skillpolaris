"""SmartRecruiters public postings API extractor (no auth).

Two-step, like Bundesagentur: the list endpoint only returns stubs (no
description), so ``fetch_board`` pages the list to collect posting IDs and
then does one detail call per ID internally — still exposed as a single
``fetch_board`` call to match the ``AtsExtractor`` interface. A public
postings feed is opt-in per SmartRecruiters customer, so some real company
identifiers return zero results even though the endpoint itself works.
"""

from __future__ import annotations

import time
from typing import Any

from pipeline.schemas.jobs import RawJobRecord
from pipeline.tasks.extract.sources.base import AtsExtractor, get_extractor_logger

POSTINGS_LIST_URL = "https://api.smartrecruiters.com/v1/companies/{company}/postings"
POSTINGS_DETAIL_URL = (
    "https://api.smartrecruiters.com/v1/companies/{company}/postings/{posting_id}"
)
USER_AGENT = "SkillPolaris/0.1 (academic research; ats ingest)"
PAGE_SIZE = 100
DETAIL_CALL_DELAY_SECONDS = 0.2


class SmartRecruitersExtractor(AtsExtractor):
    """Syncs all public postings for configured SmartRecruiters company identifiers."""

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
        return "smartrecruiters"

    def _list_posting_ids(self, company_slug: str) -> list[str]:
        url = POSTINGS_LIST_URL.format(company=company_slug)
        ids: list[str] = []
        offset = 0

        while True:
            response = self.session.get(
                url,
                params={"limit": PAGE_SIZE, "offset": offset},
                timeout=30,
            )
            response.raise_for_status()
            payload = response.json()
            content = payload.get("content") or []
            if not isinstance(content, list) or not content:
                break

            ids.extend(
                str(item["id"])
                for item in content
                if isinstance(item, dict) and item.get("id") is not None
            )
            if len(content) < PAGE_SIZE:
                break
            offset += PAGE_SIZE

        return ids

    def fetch_board(self, company_slug: str) -> list[dict[str, Any]]:
        try:
            posting_ids = self._list_posting_ids(company_slug)
        except Exception as exc:  # noqa: BLE001 — per-board boundary
            get_extractor_logger().error(
                "[SmartRecruitersExtractor] list failed for %s: %s", company_slug, exc
            )
            return []

        postings: list[dict[str, Any]] = []
        for posting_id in posting_ids:
            try:
                url = POSTINGS_DETAIL_URL.format(
                    company=company_slug, posting_id=posting_id
                )
                response = self.session.get(url, timeout=30)
                response.raise_for_status()
                postings.append(response.json())
            except Exception as exc:  # noqa: BLE001 — per-posting boundary
                get_extractor_logger().error(
                    "[SmartRecruitersExtractor] detail failed for %s/%s: %s",
                    company_slug,
                    posting_id,
                    exc,
                )
            time.sleep(DETAIL_CALL_DELAY_SECONDS)

        return postings

    def to_raw_job(
        self,
        payload: dict[str, Any],
        *,
        keyword: str | None = None,
        company_slug: str | None = None,
    ) -> RawJobRecord:
        sections = payload.get("jobAd", {}).get("sections", {}) or {}
        description_parts = [
            section.get("text", "")
            for section in sections.values()
            if isinstance(section, dict) and section.get("text")
        ]
        return RawJobRecord(
            source=self.source_name,
            external_id=str(payload["id"]),
            extractor_kind=self.extractor_kind,
            keyword=keyword or company_slug,
            title_raw=payload.get("name") or payload.get("title") or "",
            description_raw="\n\n".join(description_parts),
            url=payload.get("ref") or payload.get("applyUrl"),
            posted_at_raw=payload.get("releasedDate") or payload.get("createdOn"),
            raw_payload=payload,
        )
