FILE := "."

lint file=FILE:
    uv run ruff check {{file}}

fix file=FILE:
    uv run ruff check --fix {{file}}

format file=FILE:
    uv run ruff format {{file}}

# Full stack: data plane + Prefect/worker (migrations run in worker entrypoint).
up:
    docker compose -f infra/docker-compose.data.yml --env-file .env up -d --wait
    docker compose -f infra/docker-compose.pipeline.yml --env-file .env up -d --build

down:
    docker compose -f infra/docker-compose.pipeline.yml --env-file .env down
    docker compose -f infra/docker-compose.data.yml --env-file .env down

# Individual planes — e.g. just compose ps
compose *args:
    docker compose -f infra/docker-compose.data.yml --env-file .env {{args}}

compose-pipeline *args:
    docker compose -f infra/docker-compose.pipeline.yml --env-file .env {{args}}

compose-app *args:
    docker compose -f infra/docker-compose.app.yml --env-file .env {{args}}

pipeline-shell:
    docker compose -f infra/docker-compose.pipeline.yml --env-file .env exec pipeline-worker bash

# Manual runs (one-shot inside the worker container)
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

prefect-deploy:
    docker compose -f infra/docker-compose.pipeline.yml --env-file .env exec pipeline-worker \
        uv run --package pipeline python -m pipeline.deployments

# Schema migrations (Alembic)
migrate:
    uv run --package pipeline alembic -c apps/pipeline/alembic.ini upgrade head

migrate-docker:
    docker compose -f infra/docker-compose.pipeline.yml --env-file .env exec pipeline-worker \
        uv run --package pipeline alembic -c apps/pipeline/alembic.ini upgrade head
