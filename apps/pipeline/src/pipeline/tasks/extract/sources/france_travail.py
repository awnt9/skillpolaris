from typing import Any

import requests
from pipeline.schemas.extract_requests import FranceTravailRequestTemplate
from pipeline.schemas.jobs import FeedBatch, RawJobRecord
from pipeline.tasks.extract.sources.base import FeedExtractor, get_extractor_logger

SEARCH_URL = "https://api.francetravail.io/partenaire/offresdemploi/v2/offres/search"
# API-enforced cap: range's second element maxes out at 1149 per unique query.
MAX_RANGE_END = 1149


class FranceTravailExtractor(FeedExtractor):
    """Pulls France Travail offers straight from /offres/search.

    Search results already carry the full offer (description included), so
    unlike Bundesagentur there is no separate detail call.
    """

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
            get_extractor_logger().error("[FranceTravailExtractor] token fetch failed: %s", e)
            return None

    def fetch_batch(
        self,
        cursor: str | None = None,
        *,
        keyword: str | None = None,
    ) -> FeedBatch:
        del keyword  # unscoped: pulls the full catalog, no keyword filter
        page_size = self.configuration.france_travail_page_size
        start = int(cursor) if cursor is not None else 0
        end = min(start + page_size - 1, MAX_RANGE_END)
        range_param = f"{start}-{end}"

        params = FranceTravailRequestTemplate(range=range_param).model_dump(
            exclude_none=True
        )
        self.session.headers.update(
            {
                "Authorization": f"Bearer {self.access_token}",
                "Accept": "application/json",
            }
        )

        try:
            res = self.session.get(SEARCH_URL, params=params, timeout=10)
            res.raise_for_status()
            if res.status_code == 204:
                return FeedBatch(records=[], next_cursor=None)
            data = res.json()
        except Exception as exc:  # noqa: BLE001 — feed boundary
            get_extractor_logger().error("[FranceTravailExtractor] fetch failed: %s", exc)
            return FeedBatch(records=[], next_cursor=None)

        records = data.get("resultats", [])

        next_start = end + 1
        next_cursor = (
            str(next_start)
            if records and len(records) == (end - start + 1) and next_start <= MAX_RANGE_END
            else None
        )
        return FeedBatch(records=records, next_cursor=next_cursor)

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
            title_raw=payload["intitule"],
            description_raw=payload["description"],
            url=payload.get("origineOffre", {}).get("urlOrigine"),
            posted_at_raw=payload.get("dateCreation"),
            raw_payload=payload,
        )
