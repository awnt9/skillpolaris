"""Always-on Prefect process worker for SkillPolaris pipeline flows."""

from __future__ import annotations

import logging
import subprocess
import sys

from pipeline.deployments import prefect_cmd, register_deployments, require_env

logger = logging.getLogger(__name__)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
    pool = require_env("PREFECT_WORK_POOL")
    register_deployments(pool_name=pool)

    logger.info("Starting Prefect worker on pool %r", pool)
    result = subprocess.run(
        prefect_cmd("worker", "start", "--pool", pool, "--type", "process"),
        check=False,
    )
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
