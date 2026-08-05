from typing import Any

import requests
from pipeline.schemas.extract_requests import FranceTravailRequestTemplate
from pipeline.schemas.jobs import RawJobRecord
from pipeline.tasks.sources.base import DetailExtractor, handle_api_errors
from rich import print


class FranceTravailExtractor(DetailExtractor):
    def __init__(self, configuration):
        super().__init__(configuration=configuration)
        self.client_id = self.configuration.france_travail_client_id
        self.client_secret = self.configuration.france_travail_client_secret
        self.access_token = self._get_access_token()

        self.session.headers.update({"Authorization": f"Bearer {self.access_token}"})

    @property
    def source_name(self) -> str:
        return "france_travail"

    def _get_access_token(self):
        url = (
            "https://entreprise.francetravail.fr/connexion/oauth2/access_token"
            "?realm=/partenaire"
        )

        payload = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scope": "api_offresdemploiv2 o2dsoffre",
        }

        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        try:
            response = requests.post(url, data=payload, headers=headers, timeout=10)
            response.raise_for_status()

            if response.status_code == 200:
                data = response.json()
                return data.get("access_token")

            raise Exception(
                "ERROR: unable to get access token on FranceTravail\n"
                f" response text: {response.text}"
            )

        except Exception as e:
            print(e)
            return None

    @handle_api_errors
    def search_ids(self, keyword: str, page: int) -> list[str]:
        url = "https://api.francetravail.io/partenaire/offresdemploi/v2/offres/search"
        range_param = f"{20 * page}-{20 * page + 19}"
        params = FranceTravailRequestTemplate(
            motsCles=keyword, range=range_param
        ).model_dump(exclude_none=True)
        self.session.headers.update(
            {
                "Authorization": f"Bearer {self.access_token}",
                "Accept": "application/json",
            }
        )

        res = self.session.get(url, params=params, timeout=10)
        res.raise_for_status()

        if res.status_code == 204:
            return []

        if res.status_code in (200, 206):
            data = res.json()
            return [item["id"] for item in data.get("resultats", [])]

        return []

    @handle_api_errors
    def fetch_detail(self, job_id: str) -> dict[str, Any] | None:
        url = f"https://api.francetravail.io/partenaire/offresdemploi/v2/offres/{job_id}"

        res = self.session.get(url, timeout=10)
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
        location = payload.get("lieuTravail", {})
        company = payload.get("entreprise", {})

        return RawJobRecord(
            source=self.source_name,
            external_id=str(payload["id"]),
            extractor_kind=self.extractor_kind,
            keyword=keyword,
            title_raw=payload["intitule"],
            description_raw=payload["description"],
            url=payload.get("origineOffre", {}).get("urlOrigine"),
            company_raw=company.get("nom"),
            location_raw=location.get("libelle"),
            posted_at_raw=payload.get("dateCreation"),
            raw_payload=payload,
        )
