FILE := "."

lint file=FILE:
    uv run ruff check {{file}}

fix file=FILE:
    uv run ruff check --fix {{file}}

format file=FILE:
    uv run ruff format {{file}}

# Data plane: Postgres + pgweb. Shared network the other planes attach to.
up-data:
    docker compose -f infra/docker-compose.data.yml --env-file .env up -d --wait

down-data:
    docker compose -f infra/docker-compose.data.yml --env-file .env down

# Pipeline plane: Prefect server + worker (migrations run in worker entrypoint).
# just up-pipeline        -> pipeline only (data plane must already be up)
# just up-pipeline --full -> data + langfuse + pipeline
up-pipeline flag="":
    @if [ "{{flag}}" = "--full" ]; then just up-data; fi
    @if [ "{{flag}}" = "--full" ]; then just up-langfuse; fi
    docker compose -f infra/docker-compose.pipeline.yml --env-file .env up -d --build

down-pipeline flag="":
    docker compose -f infra/docker-compose.pipeline.yml --env-file .env down
    @if [ "{{flag}}" = "--full" ]; then just down-langfuse; fi
    @if [ "{{flag}}" = "--full" ]; then just down-data; fi

# App plane: API + web.
# just up-app        -> app only (data plane must already be up)
# just up-app --full -> data + app
up-app flag="":
    @if [ "{{flag}}" = "--full" ]; then just up-data; fi
    docker compose -f infra/docker-compose.app.yml --env-file .env --profile app up -d --build

down-app flag="":
    docker compose -f infra/docker-compose.app.yml --env-file .env --profile app down
    @if [ "{{flag}}" = "--full" ]; then just down-data; fi

# Langfuse plane: self-hosted LLM observability for filter/enrich.
# just up-langfuse        -> langfuse only (data plane must already be up)
# just up-langfuse --full -> data + langfuse
up-langfuse flag="":
    @if [ "{{flag}}" = "--full" ]; then just up-data; fi
    docker compose -f infra/docker-compose.langfuse.yml --env-file .env up -d --wait

down-langfuse flag="":
    docker compose -f infra/docker-compose.langfuse.yml --env-file .env down
    @if [ "{{flag}}" = "--full" ]; then just down-data; fi

# One-shot flow runs (pipeline plane must be up)
extract:
    docker compose -f infra/docker-compose.pipeline.yml --env-file .env exec pipeline-worker \
        uv run --package pipeline python -m pipeline.flows.extract

filter:
    docker compose -f infra/docker-compose.pipeline.yml --env-file .env exec pipeline-worker \
        uv run --package pipeline python -m pipeline.flows.filter

enrich:
    docker compose -f infra/docker-compose.pipeline.yml --env-file .env exec pipeline-worker \
        uv run --package pipeline python -m pipeline.flows.enrich

sync-keywords:
    docker compose -f infra/docker-compose.pipeline.yml --env-file .env exec pipeline-worker \
        uv run --package pipeline python -m pipeline.flows.sync_keywords

describe-skills:
    docker compose -f infra/docker-compose.pipeline.yml --env-file .env exec pipeline-worker \
        uv run --package pipeline python -m pipeline.flows.describe_skills

judge:
    docker compose -f infra/docker-compose.pipeline.yml --env-file .env exec pipeline-worker \
        uv run --package pipeline python -m pipeline.flows.judge

# Calibration only, runs on the host (not in a container): LLM-as-a-judge over
# local CV PDFs, for manually tuning apps/api/src/api/prompts/cv_extract.md.
# Never wired into /cv/upload. Usage: just judge-cv "path/to/cv1.pdf path/to/cv2.pdf"
judge-cv pdfs:
    uv run --package api python -m api.scripts.judge_cv {{pdfs}}

prune:
    docker compose -f infra/docker-compose.pipeline.yml --env-file .env exec pipeline-worker \
        uv run --package pipeline python -m pipeline.flows.prune

# Register/refresh Prefect deployment schedules against the running server.
deploy-flows:
    docker compose -f infra/docker-compose.pipeline.yml --env-file .env exec pipeline-worker \
        uv run --package pipeline python -m pipeline.deployments

# Schema migrations (Alembic), always run inside the pipeline worker container.
migrate:
    docker compose -f infra/docker-compose.pipeline.yml --env-file .env exec pipeline-worker \
        uv run --package pipeline alembic -c apps/pipeline/alembic.ini upgrade head
