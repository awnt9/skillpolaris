"""Register Prefect deployments (schedules) against the work pool."""

from __future__ import annotations

import logging
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request

from pipeline.flows.ingest import ingest_flow
from pipeline.flows.sync_keywords import sync_keywords_flow
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


def register_deployments(
    *,
    pool_name: str | None = None,
    ingest_cron: str | None = None,
    sync_keywords_cron: str | None = None,
) -> None:
    pool = pool_name or require_env("PREFECT_WORK_POOL")
    ingest_cron = ingest_cron or require_env("INGEST_CRON")
    sync_cron = sync_keywords_cron or require_env("SYNC_KEYWORDS_CRON")

    wait_for_prefect_api()
    ensure_work_pool(pool)

    ingest_flow.deploy(
        name="scheduled",
        work_pool_name=pool,
        cron=ingest_cron,
        build=False,
        push=False,
        print_next_steps=False,
        entrypoint_type=EntrypointType.MODULE_PATH,
        tags=["skillpolaris", "ingest"],
        concurrency_limit=1,
        description="Scheduled ingest (extract → filter → transform).",
    )
    logger.info("Registered ingest-jobs/scheduled cron=%r", ingest_cron)

    sync_keywords_flow.deploy(
        name="scheduled",
        work_pool_name=pool,
        cron=sync_cron,
        build=False,
        push=False,
        print_next_steps=False,
        entrypoint_type=EntrypointType.MODULE_PATH,
        tags=["skillpolaris", "keywords"],
        concurrency_limit=1,
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
