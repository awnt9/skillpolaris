FILE ?= .
ARGS ?=

.PHONY: lint fix format compose compose-pipeline compose-app \
	pipeline-shell pipeline sync-keywords prefect-deploy migrate migrate-docker

lint:
	uv run ruff check $(FILE)

fix:
	uv run ruff check --fix $(FILE)

format:
	uv run ruff format $(FILE)

# Full Docker stack — e.g. make compose ARGS="up -d"
compose:
	docker compose -f infra/docker-compose.data.yml --env-file .env $(ARGS)

compose-pipeline:
	docker compose -f infra/docker-compose.pipeline.yml --env-file .env $(ARGS)

compose-app:
	docker compose -f infra/docker-compose.app.yml --env-file .env $(ARGS)

pipeline-shell:
	docker compose -f infra/docker-compose.pipeline.yml --env-file .env exec pipeline-worker bash

pipeline:
	docker compose -f infra/docker-compose.pipeline.yml --env-file .env exec pipeline-worker \
		uv run --package pipeline python -m pipeline.flows.ingest

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
