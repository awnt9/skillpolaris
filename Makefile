FILE ?= .
FULL ?=

.PHONY: lint fix format \
	up-data down-data \
	up-pipeline down-pipeline \
	up-app down-app \
	up-langfuse down-langfuse \
	extract filter enrich sync-keywords \
	deploy-flows migrate

lint:
	uv run ruff check $(FILE)

fix:
	uv run ruff check --fix $(FILE)

format:
	uv run ruff format $(FILE)

# Data plane: Postgres + pgweb. Shared network the other planes attach to.
up-data:
	docker compose -f infra/docker-compose.data.yml --env-file .env up -d --wait

down-data:
	docker compose -f infra/docker-compose.data.yml --env-file .env down

# Pipeline plane: Prefect server + worker (migrations run in worker entrypoint).
# make up-pipeline        -> pipeline only (data plane must already be up)
# make up-pipeline FULL=1 -> data + langfuse + pipeline
up-pipeline:
	@if [ "$(FULL)" = "1" ]; then $(MAKE) up-data; fi
	@if [ "$(FULL)" = "1" ]; then $(MAKE) up-langfuse; fi
	docker compose -f infra/docker-compose.pipeline.yml --env-file .env up -d --build

down-pipeline:
	docker compose -f infra/docker-compose.pipeline.yml --env-file .env down
	@if [ "$(FULL)" = "1" ]; then $(MAKE) down-langfuse; fi
	@if [ "$(FULL)" = "1" ]; then $(MAKE) down-data; fi

# App plane: API + web.
# make up-app        -> app only (data plane must already be up)
# make up-app FULL=1 -> data + app
up-app:
	@if [ "$(FULL)" = "1" ]; then $(MAKE) up-data; fi
	docker compose -f infra/docker-compose.app.yml --env-file .env --profile app up -d --build

down-app:
	docker compose -f infra/docker-compose.app.yml --env-file .env --profile app down
	@if [ "$(FULL)" = "1" ]; then $(MAKE) down-data; fi

# Langfuse plane: self-hosted LLM observability for filter/enrich.
# make up-langfuse        -> langfuse only (data plane must already be up)
# make up-langfuse FULL=1 -> data + langfuse
up-langfuse:
	@if [ "$(FULL)" = "1" ]; then $(MAKE) up-data; fi
	docker compose -f infra/docker-compose.langfuse.yml --env-file .env up -d --wait

down-langfuse:
	docker compose -f infra/docker-compose.langfuse.yml --env-file .env down
	@if [ "$(FULL)" = "1" ]; then $(MAKE) down-data; fi

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

# Register/refresh Prefect deployment schedules against the running server.
deploy-flows:
	docker compose -f infra/docker-compose.pipeline.yml --env-file .env exec pipeline-worker \
		uv run --package pipeline python -m pipeline.deployments

# Schema migrations (Alembic), always run inside the pipeline worker container.
migrate:
	docker compose -f infra/docker-compose.pipeline.yml --env-file .env exec pipeline-worker \
		uv run --package pipeline alembic -c apps/pipeline/alembic.ini upgrade head
