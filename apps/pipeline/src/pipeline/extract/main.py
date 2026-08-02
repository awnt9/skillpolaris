import random
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from typing import Protocol

import requests
from rich import print

from pipeline.config import get_configuration
from pipeline.domain.models import RawJobRecord
from pipeline.extract.sources import FranceTravailExtractor, USAJOBExtractor
from pipeline.persistence import PostgresManager


class RawJobStore(Protocol):
    """Storage contract required by the extraction flow."""

    def count_raw_jobs_by_keyword(self, keywords: list[str]) -> dict[str, int]:
        ...

    def filter_new_job_ids(self, source_name: str, raw_ids: list[str]) -> list[str]:
        ...

    def save_raw_job(self, raw_job: RawJobRecord) -> None:
        ...


def human_delay(min_secs=1, max_secs=3):
    """Simulates a human delay with a random distribution."""
    time.sleep(random.uniform(min_secs, max_secs))


def fetch_titles(num):
    params = {
        "uri": f"http://data.europa.eu/esco/isco/C{num}",
        "language": "en",
        "version": "v1.2.1",
    }
    try:
        response = requests.get(
            "https://ec.europa.eu/esco/api/resource/concept", params=params
        )
        if response.status_code == 200:
            return [
                job["title"]
                for job in response.json()["_links"]["narrowerOccupation"]
            ]
    except Exception as e:
        print(e)
    return None


def get_keywords(group_codes: list[int]) -> list[str]:
    codes = []
    for group in group_codes:
        codes.extend(range(group * 100, group * 100 + 100))

    with ThreadPoolExecutor(max_workers=20) as executor:
        results = list(executor.map(fetch_titles, codes))

    return [title for sublist in results if sublist for title in sublist]


def sort_keywords(keywords: list[str], raw_store: RawJobStore) -> list[str]:
    results = raw_store.count_raw_jobs_by_keyword(keywords)
    return sorted(keywords, key=lambda kw: results.get(kw, 0))


def filter_existing_ids(raw_store: RawJobStore, raw_ids, source_name):
    """Checks which IDs already exist in raw_jobs to avoid duplicating records."""
    return raw_store.filter_new_job_ids(source_name, raw_ids)


def get_all_ids(configuration, keywords, extractors, raw_store: RawJobStore):
    all_tasks = []

    for kw in keywords:
        if len(all_tasks) >= configuration.max_total_details:
            break
        for extractor in extractors:
            if len(all_tasks) >= configuration.max_total_details:
                break

            page = 0

            while page < configuration.max_depth:
                print(
                    f"Searching IDs for keyword {kw} in extractor "
                    f"{extractor.source_name} (Page {page})..."
                )

                raw_ids = extractor.search_ids(kw, page)

                if not raw_ids:
                    print(f"No offers found for {kw} in {extractor.source_name}\n")
                    break

                new_ids = filter_existing_ids(
                    raw_store,
                    raw_ids,
                    extractor.source_name,
                )

                if raw_ids and not new_ids:
                    print(
                        f"Page {page} already indexed. Diving deeper to page "
                        f"{page + 1}..."
                    )
                    page += 1
                    human_delay(3, 5)
                    continue

                print(f"[blue]Result: {len(new_ids)} found[/]\n")
                for job_id in new_ids:
                    all_tasks.append(
                        {"id": job_id, "extractor": extractor, "keyword": kw}
                    )
                break

            human_delay(3, 5)

    return all_tasks


def group_tasks_by_source(all_tasks):
    grouped = {}
    for task in all_tasks:
        source_name = task["extractor"].source_name
        if source_name not in grouped:
            grouped[source_name] = []
        grouped[source_name].append(task)

    for source in grouped.keys():
        grouped[source] = grouped[source][:40]

    return grouped


def distribute_tasks(all_ids_by_extractor, configuration):
    final_tasks = []
    sources = list(all_ids_by_extractor.keys())

    while (
        any(all_ids_by_extractor.values())
        and len(final_tasks) < configuration.max_total_details
    ):
        for source in sources:
            if all_ids_by_extractor[source]:
                task = all_ids_by_extractor[source].pop(0)

                if len(final_tasks) < configuration.max_total_details:
                    final_tasks.append(task)
                else:
                    break

    return final_tasks


def print_log_ids_information(all_tasks: list):
    counts = Counter(task["keyword"] for task in all_tasks)
    print(f"\nTotal tasks to process: {len(all_tasks)}")
    print("-" * 30)
    for kw, count in counts.items():
        print(f"  - {kw}: {count} requests")
    print("-" * 30)


def get_all_details(raw_store: RawJobStore, all_tasks):
    for i, task in enumerate(all_tasks, 1):
        extractor = task["extractor"]
        job_id = str(task["id"])
        kw = task["keyword"]

        print(f"[{i}/{len(all_tasks)}] Extracting {job_id} from {extractor.source_name}")

        try:
            detail = extractor.fetch_detail(job_id)
            if detail:
                raw_job = extractor.to_raw_job(detail, keyword=kw)
                raw_store.save_raw_job(raw_job=raw_job)
        except Exception as e:
            print(f"Error extracting {job_id}: {e}")

        human_delay(5, 8)


if __name__ == "__main__":
    configuration = get_configuration()

    with PostgresManager(configuration) as raw_store:
        keywords = get_keywords([21, 25])
        keywords = sort_keywords(keywords, raw_store)

        extractors = [
            FranceTravailExtractor(configuration=configuration),
            USAJOBExtractor(configuration=configuration),
        ]

        all_tasks = get_all_ids(configuration, keywords, extractors, raw_store)
        all_tasks = group_tasks_by_source(all_tasks)
        all_tasks = distribute_tasks(all_tasks, configuration)

        print_log_ids_information(all_tasks)

        get_all_details(raw_store, all_tasks)

    print("\nExtraction process finished.")
