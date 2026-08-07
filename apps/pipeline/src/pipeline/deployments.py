"""Register Prefect deployments (schedules) against the work pool."""

from __future__ import annotations

import logging
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request

from pipeline.flows.extract import extract_flow
from pipeline.flows.filter import filter_flow
from pipeline.flows.sync_keywords import sync_keywords_flow
from pipeline.flows.transform import transform_flow
from prefect.types.entrypoint import EntrypointType

logger = logging.getLogger(__name__)


def prefect_cmd(*args: str) -> list[str]:
    return [sys.executable, "-m", "prefect", *args]


def require_env(name: str) -> str:
    value = os.environ.get(name)
    if value is None or value.strip() == "":
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def _api_url() -> str:
    return require_env("PREFECT_API_URL").rstrip("/")


def wait_for_prefect_api(timeout_seconds: int = 180) -> None:
    health_url = f"{_api_url()}/health"
    deadline = time.monotonic() + timeout_seconds
    last_error: Exception | None = None

    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(health_url, timeout=5) as response:
                if 200 <= response.status < 300:
                    logger.info("Prefect API ready at %s", _api_url())
                    return
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last_error = exc
            time.sleep(2)

    raise RuntimeError(f"Prefect API not ready at {health_url}: {last_error}")


def ensure_work_pool(pool_name: str) -> None:
    result = subprocess.run(
        prefect_cmd(
            "work-pool",
            "create",
            pool_name,
            "--type",
            "process",
            "--overwrite",
        ),
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        logger.info("Work pool ready: %s", pool_name)
        return

    combined = f"{result.stdout}\n{result.stderr}".lower()
    if "already exists" in combined:
        logger.info("Work pool already exists: %s", pool_name)
        return

    fallback = subprocess.run(
        prefect_cmd("work-pool", "create", pool_name, "--type", "process"),
        check=False,
        capture_output=True,
        text=True,
    )
    fallback_out = f"{fallback.stdout}\n{fallback.stderr}".lower()
    if fallback.returncode == 0 or "already exists" in fallback_out:
        logger.info("Work pool ready: %s", pool_name)
        return

    logger.error("work-pool create stdout: %s", result.stdout)
    logger.error("work-pool create stderr: %s", result.stderr)
    logger.error("work-pool create fallback stdout: %s", fallback.stdout)
    logger.error("work-pool create fallback stderr: %s", fallback.stderr)
    raise RuntimeError(f"Could not create work pool {pool_name}")


def _deploy_scheduled(
    *,
    flow,
    name: str,
    pool: str,
    cron: str,
    tags: list[str],
    description: str,
) -> None:
    flow.deploy(
        name=name,
        work_pool_name=pool,
        cron=cron,
        build=False,
        push=False,
        print_next_steps=False,
        entrypoint_type=EntrypointType.MODULE_PATH,
        tags=tags,
        concurrency_limit=1,
        description=description,
    )


def register_deployments(
    *,
    pool_name: str | None = None,
    extract_cron: str | None = None,
    filter_cron: str | None = None,
    transform_cron: str | None = None,
    sync_keywords_cron: str | None = None,
) -> None:
    pool = pool_name or require_env("PREFECT_WORK_POOL")
    extract_cron = extract_cron or require_env("EXTRACT_CRON")
    filter_cron = filter_cron or require_env("FILTER_CRON")
    transform_cron = transform_cron or require_env("TRANSFORM_CRON")
    sync_cron = sync_keywords_cron or require_env("SYNC_KEYWORDS_CRON")

    wait_for_prefect_api()
    ensure_work_pool(pool)

    _deploy_scheduled(
        flow=extract_flow,
        name="scheduled",
        pool=pool,
        cron=extract_cron,
        tags=["skillpolaris", "extract"],
        description="Scheduled extract: sources → raw_jobs.",
    )
    logger.info("Registered extract-jobs/scheduled cron=%r", extract_cron)

    _deploy_scheduled(
        flow=filter_flow,
        name="scheduled",
        pool=pool,
        cron=filter_cron,
        tags=["skillpolaris", "filter"],
        description="Scheduled filter: raw_jobs (pending) → canonical_jobs.",
    )
    logger.info("Registered filter-jobs/scheduled cron=%r", filter_cron)

    _deploy_scheduled(
        flow=transform_flow,
        name="scheduled",
        pool=pool,
        cron=transform_cron,
        tags=["skillpolaris", "transform"],
        description="Scheduled transform: canonical_jobs (pending) → Qdrant.",
    )
    logger.info("Registered transform-jobs/scheduled cron=%r", transform_cron)

    _deploy_scheduled(
        flow=sync_keywords_flow,
        name="scheduled",
        pool=pool,
        cron=sync_cron,
        tags=["skillpolaris", "keywords"],
        description="Scheduled keyword catalog sync.",
    )
    logger.info("Registered sync-keywords/scheduled cron=%r", sync_cron)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
    register_deployments()


if __name__ == "__main__":
    main()
