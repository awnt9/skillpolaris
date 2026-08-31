"""Adzuna public search API extractor (free app_id/app_key, self-serve).

Unscoped, no keyword: pages through each configured country in turn. Cursor
is ``"{country}|{page}"``. Each country gets a fixed page share per run
(``MAX_BATCHES_PER_RUN`` split across countries) so a big market can't hog
every batch and starve the rest; a country also rolls over early if it runs
out of results first.
"""

from __future__ import annotations

from typing import Any

from pipeline.schemas.jobs import FeedBatch, RawJobRecord
from pipeline.tasks.extract.sources.base import FeedExtractor, get_extractor_logger

SEARCH_URL = "https://api.adzuna.com/v1/api/jobs/{country}/search/{page}"
RESULTS_PER_PAGE = 20
USER_AGENT = "SkillPolaris/0.1 (academic research; feed ingest)"
# Mirrors feed_runner's max_batches_per_tag default: how many pages a single
# unscoped sweep gets per run, split evenly across countries so the first
# country in the list can't burn the whole sweep and starve the rest.
MAX_BATCHES_PER_RUN = 10


def _countries(configuration) -> list[str]:
    return [c.strip() for c in configuration.adzuna_countries.split(",") if c.strip()]


def _pages_per_country(countries: list[str]) -> int:
    if not countries:
        return 1
    return max(1, MAX_BATCHES_PER_RUN // len(countries))


class AdzunaExtractor(FeedExtractor):
    """Pulls Adzuna job search results, unscoped, rotating through countries."""

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
        return "adzuna"

    def _parse_cursor(self, cursor: str | None) -> tuple[str, int] | None:
        countries = _countries(self.configuration)
        if not countries:
            return None
        if cursor is None:
            return countries[0], 1

        country, _, page_raw = cursor.partition("|")
        page = int(page_raw) if page_raw.isdigit() else 1
        return country, page

    def fetch_batch(
        self,
        cursor: str | None = None,
        *,
        keyword: str | None = None,
    ) -> FeedBatch:
        del keyword
        app_id = (self.configuration.adzuna_app_id or "").strip()
        app_key = (self.configuration.adzuna_app_key or "").strip()
        if not app_id or not app_key:
            return FeedBatch(records=[], next_cursor=None)

        position = self._parse_cursor(cursor)
        if position is None:
            return FeedBatch(records=[], next_cursor=None)
        country, page = position

        url = SEARCH_URL.format(country=country, page=page)
        params = {
            "app_id": app_id,
            "app_key": app_key,
            "results_per_page": RESULTS_PER_PAGE,
            "content-type": "application/json",
        }

        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
        except Exception as exc:  # noqa: BLE001 — feed boundary
            get_extractor_logger().error("[AdzunaExtractor] fetch failed: %s", exc)
            return FeedBatch(records=[], next_cursor=None)

        records = data.get("results") or []

        countries = _countries(self.configuration)
        pages_cap = _pages_per_country(countries)

        next_cursor: str | None
        if len(records) == RESULTS_PER_PAGE and page < pages_cap:
            next_cursor = f"{country}|{page + 1}"
        else:
            try:
                next_index = countries.index(country) + 1
            except ValueError:
                next_index = len(countries)
            next_cursor = f"{countries[next_index]}|1" if next_index < len(countries) else None

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
            title_raw=payload.get("title") or "",
            description_raw=payload.get("description") or "",
            url=payload.get("redirect_url"),
            posted_at_raw=payload.get("created"),
            raw_payload=payload,
        )
