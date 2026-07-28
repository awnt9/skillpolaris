import random
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from typing import Protocol

import requests
from rich import print

from pipeline.configuration import configuration
from pipeline.database.postgres_manager import PostgresManager
from pipeline.extract.extractors import FranceTravailExtractor, SwissJobRoomExtractor, USAJOBExtractor
from pipeline.extract.models import StagedJobOffer


class StagingJobStore(Protocol):
    """
    Storage contract required by the extraction flow.
    """

    def count_jobs_by_keyword(self, keywords: list[str]) -> dict[str, int]:
        ...

    def filter_new_job_ids(self, source_name: str, raw_ids: list[str]) -> list[str]:
        ...

    def save_to_staging(
        self,
        staged_job: StagedJobOffer,
    ):
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
        response = requests.get("https://ec.europa.eu/esco/api/resource/concept", params=params)
        if response.status_code == 200:
            return [job["title"] for job in response.json()["_links"]["narrowerOccupation"]]
    except Exception as e:
        print(e)
    return None


def get_keywords(group_codes: list[int]) -> list[str]:
    codes = []
    for group in group_codes:
        codes.extend(range(group * 100, group * 100 + 100))

    with ThreadPoolExecutor(max_workers=20) as executor:
        results = list(executor.map(fetch_titles, codes))

    nodes = [title for sublist in results if sublist for title in sublist]

    return nodes


def sort_keywords(keywords: list[str], staging_store: StagingJobStore) -> list[str]:
    results = staging_store.count_jobs_by_keyword(keywords)

    return sorted(keywords, key=lambda kw: results.get(kw, 0))


def filter_existing_ids(staging_store: StagingJobStore, raw_ids, source_name):
    """Checks which IDs already exists in staging to avoid duplicating records."""
    return staging_store.filter_new_job_ids(source_name, raw_ids)


def get_all_ids(configuration, keywords, extractors, staging_store: StagingJobStore):
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
                    staging_store,
                    raw_ids,
                    extractor.source_name,
                )

                if raw_ids and not new_ids:
                    print(f"Page {page} already indexed. Diving deeper to page {page + 1}...")
                    page += 1
                    human_delay(3, 5)
                    continue

                print(f"[blue]Result: {len(new_ids)} found[/]\n")
                for job_id in new_ids:
                    all_tasks.append({"id": job_id, "extractor": extractor, "keyword": kw})
                break

            human_delay(3, 5)

    return all_tasks


def group_tasks_by_source(all_tasks):
    """
    Transforms a list of tasks on a dict grouped by source.
    input: [{'id': '123', 'extractor': <Obj>}, ...]
    output: {'SwissJobRoom': [{'id': '123', 'extractor': <Obj>}, ...], 'USAJobs': [...]}
    """
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
    """
    Takes all_ids_by_extractor dict and reorders it using round robin
    to alternate sources, respecting maximum resquests budget.
    """
    final_tasks = []
    sources = list(all_ids_by_extractor.keys())

    while any(all_ids_by_extractor.values()) and len(final_tasks) < configuration.max_total_details:
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


def get_all_details(staging_store: StagingJobStore, all_tasks):
    for i, task in enumerate(all_tasks, 1):
        extractor = task["extractor"]
        job_id = str(task["id"])
        kw = task["keyword"]

        print(f"[{i}/{len(all_tasks)}] Extracting {job_id} from {extractor.source_name}")

        try:
            detail = extractor.fetch_detail(job_id)
            if detail:
                staged_job = extractor.to_staged_job(detail, keyword=kw)
                staging_store.save_to_staging(staged_job=staged_job)
        except Exception as e:
            print(f"Error extracting {job_id}: {e}")

        human_delay(5, 8)


if __name__ == "__main__":
    configuration = configuration.get_configuration()

    with PostgresManager(configuration) as staging_store:
        keywords = get_keywords([21, 25])
        keywords = sort_keywords(keywords, staging_store)

        extractors = [
            SwissJobRoomExtractor(configuration=configuration),
            FranceTravailExtractor(configuration=configuration),
            USAJOBExtractor(configuration=configuration),
        ]

        all_tasks = get_all_ids(configuration, keywords, extractors, staging_store)
        all_tasks = group_tasks_by_source(all_tasks)
        all_tasks = distribute_tasks(all_tasks, configuration)

        print_log_ids_information(all_tasks)

        get_all_details(staging_store, all_tasks)

    print("\nExtraction process finished.")
