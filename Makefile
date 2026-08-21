FILE ?= .
ARGS ?=

.PHONY: lint fix format up down compose compose-pipeline compose-app \
	pipeline-shell extract filter enrich sync-keywords \
	prefect-deploy migrate migrate-docker

lint:
	uv run ruff check $(FILE)

fix:
	uv run ruff check --fix $(FILE)

format:
	uv run ruff format $(FILE)

# Full stack: data plane + Prefect/worker (migrations run in worker entrypoint).
up:
	docker compose -f infra/docker-compose.data.yml --env-file .env up -d --wait
	docker compose -f infra/docker-compose.pipeline.yml --env-file .env up -d --build

down:
	docker compose -f infra/docker-compose.pipeline.yml --env-file .env down
	docker compose -f infra/docker-compose.data.yml --env-file .env down

# Individual planes — e.g. make compose ARGS="ps"
compose:
	docker compose -f infra/docker-compose.data.yml --env-file .env $(ARGS)

compose-pipeline:
	docker compose -f infra/docker-compose.pipeline.yml --env-file .env $(ARGS)

compose-app:
	docker compose -f infra/docker-compose.app.yml --env-file .env $(ARGS)

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
