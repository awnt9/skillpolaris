"""Bundesagentur fuer Arbeit "Jobsuche" public API extractor.

Community-documented API (no official Bundesagentur support/SLA) covering
German job postings from private employers, mirroring the France Travail
two-step pattern: search returns a ``refnr`` per hit, and the detail
endpoint takes that ``refnr`` base64-encoded. Auth is a static, publicly
documented client key (not a per-user account) — see
https://github.com/bundesAPI/jobsuche-api
"""

from __future__ import annotations

from base64 import b64encode
from typing import Any

from pipeline.schemas.jobs import RawJobRecord
from pipeline.tasks.extract.sources.base import DetailExtractor, handle_api_errors

JOBSUCHE_SEARCH_URL = (
    "https://rest.arbeitsagentur.de/jobboerse/jobsuche-service/pc/v6/jobs"
)
JOBSUCHE_DETAIL_URL = (
    "https://rest.arbeitsagentur.de/jobboerse/jobsuche-service/pc/v4/jobdetails/{ref}"
)
API_KEY = "jobboerse-jobsuche"
PAGE_SIZE = 25


class BundesagenturExtractor(DetailExtractor):
    def __init__(self, configuration):
        super().__init__(configuration=configuration)
        self.session.headers.update(
            {
                "X-API-Key": API_KEY,
                "Accept": "application/json",
            }
        )

    @property
    def source_name(self) -> str:
        return "bundesagentur"

    @handle_api_errors
    def search_ids(self, keyword: str, page: int) -> list[str]:
        params = {
            "was": keyword,
            "page": page + 1,
            "size": PAGE_SIZE,
        }
        res = self.session.get(JOBSUCHE_SEARCH_URL, params=params, timeout=10)
        res.raise_for_status()
        data = res.json()
        offers = data.get("ergebnisliste") or []
        return [item["referenznummer"] for item in offers if item.get("referenznummer")]

    @handle_api_errors
    def fetch_detail(self, job_id: str) -> dict[str, Any] | None:
        encoded_ref = b64encode(job_id.encode()).decode()
        url = JOBSUCHE_DETAIL_URL.format(ref=encoded_ref)
        res = self.session.get(url, timeout=10)
        res.raise_for_status()
        return res.json()

    def to_raw_job(
        self,
        payload: dict[str, Any],
        *,
        keyword: str | None = None,
        company_slug: str | None = None,
    ) -> RawJobRecord:
        del company_slug
        refnr = payload.get("refnr") or payload.get("referenznummer") or ""
        title = payload.get("stellenangebotsTitel") or payload.get("titel") or ""
        description = (
            payload.get("stellenangebotsBeschreibung")
            or payload.get("stellenbeschreibung")
            or ""
        )
        posted_at = (
            payload.get("aktuelleVeroeffentlichungsdatum")
            or payload.get("ersteVeroeffentlichungsdatum")
        )
        return RawJobRecord(
            source=self.source_name,
            external_id=str(refnr),
            extractor_kind=self.extractor_kind,
            keyword=keyword,
            title_raw=title,
            description_raw=description,
            url=f"https://www.arbeitsagentur.de/jobsuche/jobdetail/{refnr}" if refnr else None,
            posted_at_raw=posted_at,
            raw_payload=payload,
        )
