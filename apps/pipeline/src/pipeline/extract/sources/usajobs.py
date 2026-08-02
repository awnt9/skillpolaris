from typing import Any

from pipeline.domain.models import RawJobRecord
from pipeline.extract.base import DetailExtractor
from pipeline.extract.errors import handle_api_errors
from pipeline.extract.models import USAJOBSRequestTemplate


class USAJOBExtractor(DetailExtractor):
    def __init__(self, configuration):
        super().__init__(configuration=configuration)
        self.api_key = self.configuration.usajobs_api_key
        self.email = self.configuration.usajobs_email

        self.session.headers.update(
            {
                "Host": "data.usajobs.gov",
                "User-Agent": self.email,
                "Authorization-Key": self.api_key,
                "Accept": "application/json",
            }
        )

    @property
    def source_name(self) -> str:
        return "usajobs"

    @handle_api_errors
    def search_ids(self, keyword: str, page: int) -> list[str]:
        url = "https://data.usajobs.gov/api/search"
        params = USAJOBSRequestTemplate(
            Keyword=keyword,
            ResultsPerPage=20,
            WhoMayApply="Public",
            Page=page + 1,
        ).model_dump(exclude_none=True)

        res = self.session.get(url, params=params, timeout=10)
        res.raise_for_status()
        data = res.json()

        return [
            job["MatchedObjectId"]
            for job in data["SearchResult"]["SearchResultItems"]
        ]

    @handle_api_errors
    def fetch_detail(self, job_id: str) -> dict[str, Any] | None:
        url = "https://data.usajobs.gov/api/search"
        params = USAJOBSRequestTemplate(Keyword=job_id).model_dump(exclude_none=True)

        res = self.session.get(url, params=params, timeout=10)
        res.raise_for_status()
        if res.status_code == 204:
            return None
        return res.json()

    def to_raw_job(
        self,
        payload: dict[str, Any],
        *,
        keyword: str | None = None,
        company_slug: str | None = None,
    ) -> RawJobRecord:
        del company_slug
        descriptor = payload["SearchResult"]["SearchResultItems"][0][
            "MatchedObjectDescriptor"
        ]
        position_locations = descriptor.get("PositionLocation", [])
        organization = descriptor.get("OrganizationName")
        apply_uri = descriptor.get("PositionURI")
        details = descriptor.get("UserArea", {}).get("Details", {})

        return RawJobRecord(
            source=self.source_name,
            external_id=str(descriptor["PositionID"]),
            extractor_kind=self.extractor_kind,
            keyword=keyword,
            title_raw=descriptor["PositionTitle"],
            description_raw=(
                descriptor.get("QualificationSummary")
                or details.get("JobSummary", "")
            ),
            url=apply_uri,
            company_raw=organization,
            location_raw=(
                position_locations[0].get("LocationName") if position_locations else None
            ),
            posted_at_raw=descriptor.get("PublicationStartDate"),
            raw_payload=payload,
        )
