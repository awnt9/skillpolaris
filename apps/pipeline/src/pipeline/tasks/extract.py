"""Extract task: plan detail fetches and persist raw offers."""

from __future__ import annotations

import random
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from typing import Protocol

import requests
from pipeline.config import Settings, get_configuration
from pipeline.schemas.jobs import DetailTask, RawJobRecord
from pipeline.storage.postgres import PostgresManager
from pipeline.tasks.sources.base import DetailExtractor
from pipeline.tasks.sources.france_travail import FranceTravailExtractor
from prefect import get_run_logger, task
from rich import print


class RawJobStore(Protocol):
    def count_raw_jobs_by_keyword(self, keywords: list[str]) -> dict[str, int]:
        ...

    def filter_new_job_ids(self, source_name: str, raw_ids: list[str]) -> list[str]:
        ...

    def save_raw_job(self, raw_job: RawJobRecord) -> None:
        ...


def human_delay(min_secs: float = 1, max_secs: float = 3) -> None:
    time.sleep(random.uniform(min_secs, max_secs))


def build_detail_extractors(configuration: Settings) -> dict[str, DetailExtractor]:
    extractors = [
        FranceTravailExtractor(configuration=configuration),
    ]
    return {extractor.source_name: extractor for extractor in extractors}


def fetch_titles(num: int) -> list[str] | None:
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
    codes: list[int] = []
    for group in group_codes:
        codes.extend(range(group * 100, group * 100 + 100))

    with ThreadPoolExecutor(max_workers=20) as executor:
        results = list(executor.map(fetch_titles, codes))

    return [title for sublist in results if sublist for title in sublist]


def sort_keywords(keywords: list[str], raw_store: RawJobStore) -> list[str]:
    results = raw_store.count_raw_jobs_by_keyword(keywords)
    return sorted(keywords, key=lambda kw: results.get(kw, 0))


def collect_detail_tasks(
    configuration: Settings,
    keywords: list[str],
    extractors: dict[str, DetailExtractor],
    raw_store: RawJobStore,
) -> list[DetailTask]:
    all_tasks: list[DetailTask] = []

    for kw in keywords:
        if len(all_tasks) >= configuration.max_total_details:
            break
        for extractor in extractors.values():
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

                new_ids = raw_store.filter_new_job_ids(extractor.source_name, raw_ids)

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
                        {
                            "id": str(job_id),
                            "source_name": extractor.source_name,
                            "keyword": kw,
                        }
                    )
                break

            human_delay(3, 5)

    return all_tasks


def group_tasks_by_source(all_tasks: list[DetailTask]) -> dict[str, list[DetailTask]]:
    grouped: dict[str, list[DetailTask]] = {}
    for task_item in all_tasks:
        grouped.setdefault(task_item["source_name"], []).append(task_item)

    for source in grouped:
        grouped[source] = grouped[source][:40]

    return grouped


def distribute_tasks(
    all_ids_by_source: dict[str, list[DetailTask]],
    configuration: Settings,
) -> list[DetailTask]:
    final_tasks: list[DetailTask] = []
    sources = list(all_ids_by_source.keys())
    buckets = {source: list(tasks) for source, tasks in all_ids_by_source.items()}

    while any(buckets.values()) and len(final_tasks) < configuration.max_total_details:
        for source in sources:
            if buckets[source]:
                task_item = buckets[source].pop(0)
                if len(final_tasks) < configuration.max_total_details:
                    final_tasks.append(task_item)
                else:
                    break

    return final_tasks


def print_log_ids_information(all_tasks: list[DetailTask]) -> None:
    counts = Counter(task_item["keyword"] for task_item in all_tasks)
    print(f"\nTotal tasks to process: {len(all_tasks)}")
    print("-" * 30)
    for kw, count in counts.items():
        print(f"  - {kw}: {count} requests")
    print("-" * 30)


def fetch_and_persist_detail(
    *,
    extractor: DetailExtractor,
    job_id: str,
    keyword: str,
    raw_store: RawJobStore,
) -> bool:
    detail = extractor.fetch_detail(job_id)
    if not detail:
        return False
    raw_job = extractor.to_raw_job(detail, keyword=keyword)
    raw_store.save_raw_job(raw_job=raw_job)
    return True


def plan_detail_tasks(
    configuration: Settings,
    raw_store: RawJobStore,
    extractors: dict[str, DetailExtractor],
    esco_groups: list[int] | None = None,
) -> list[DetailTask]:
    groups = esco_groups or [21, 25]
    keywords = get_keywords(groups)
    keywords = sort_keywords(keywords, raw_store)
    tasks = collect_detail_tasks(configuration, keywords, extractors, raw_store)
    tasks = distribute_tasks(group_tasks_by_source(tasks), configuration)
    print_log_ids_information(tasks)
    return tasks


def run_extract(
    configuration: Settings,
    esco_groups: list[int] | None = None,
) -> dict[str, int]:
    extractors = build_detail_extractors(configuration)

    with PostgresManager(configuration) as raw_store:
        planned = plan_detail_tasks(
            configuration=configuration,
            raw_store=raw_store,
            extractors=extractors,
            esco_groups=esco_groups,
        )

        if not planned:
            return {"planned": 0, "saved": 0, "failed": 0}

        saved = 0
        failed = 0
        for i, detail_task in enumerate(planned, 1):
            extractor = extractors.get(detail_task["source_name"])
            print(
                f"[{i}/{len(planned)}] Extracting {detail_task['id']} "
                f"from {detail_task['source_name']}"
            )

            if extractor is None:
                failed += 1
                continue

            try:
                ok = fetch_and_persist_detail(
                    extractor=extractor,
                    job_id=detail_task["id"],
                    keyword=detail_task["keyword"],
                    raw_store=raw_store,
                )
                if ok:
                    saved += 1
                else:
                    failed += 1
            except Exception as e:
                print(f"Error extracting {detail_task['id']}: {e}")
                failed += 1

            human_delay(5, 8)

    return {"planned": len(planned), "saved": saved, "failed": failed}


@task(name="extract", retries=1)
def extract_task(esco_groups: list[int] | None = None) -> dict[str, int]:
    logger = get_run_logger()
    configuration = get_configuration()
    result = run_extract(configuration, esco_groups=esco_groups)
    logger.info(
        "Extract finished. planned=%s saved=%s failed=%s",
        result["planned"],
        result["saved"],
        result["failed"],
    )
    return result
