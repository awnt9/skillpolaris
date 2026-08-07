from concurrent.futures import ThreadPoolExecutor

import requests
from pipeline.schemas.extract import SearchKeywordUpsert
from pipeline.tasks.keywords.providers.base import KeywordProvider


def _fetch_esco_titles(group_code: int) -> list[str]:
    params = {
        "uri": f"http://data.europa.eu/esco/isco/C{group_code}",
        "language": "en",
        "version": "v1.2.1",
    }
    try:
        response = requests.get(
            "https://ec.europa.eu/esco/api/resource/concept",
            params=params,
            timeout=15,
        )
        if response.status_code == 200:
            return [
                job["title"]
                for job in response.json()["_links"]["narrowerOccupation"]
            ]
    except (requests.RequestException, KeyError, TypeError):
        return []
    return []


class EscoKeywordProvider(KeywordProvider):
    """Loads ISCO subgroup occupations from the ESCO API."""

    def __init__(self, group_codes: list[int] | None = None):
        self.group_codes = group_codes or [21, 25]

    @property
    def origin(self) -> str:
        return "esco"

    def collect(self) -> list[SearchKeywordUpsert]:
        codes: list[int] = []
        for group in self.group_codes:
            codes.extend(range(group * 100, group * 100 + 100))

        with ThreadPoolExecutor(max_workers=20) as executor:
            results = list(executor.map(_fetch_esco_titles, codes))

        titles = sorted({title for sublist in results if sublist for title in sublist})
        return [
            SearchKeywordUpsert(
                keyword=title,
                origin="esco",
            )
            for title in titles
        ]
