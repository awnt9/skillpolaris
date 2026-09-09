FILE ?= .
FULL ?=
VOLUMES ?=

.PHONY: lint fix format \
	up-data down-data \
	up-pipeline down-pipeline \
	up-app down-app \
	up-langfuse down-langfuse \
	extract filter enrich sync-keywords describe-skills judge prune \
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

# make down-data           -> stop containers, keep volumes (data survives)
# make down-data VOLUMES=1 -> also delete volumes (wipes the database)
down-data:
	docker compose -f infra/docker-compose.data.yml --env-file .env down $(if $(filter 1,$(VOLUMES)),-v,)

# Pipeline plane: Prefect server + worker + langfuse (langfuse is exclusive
# to pipeline, so it's not gated behind FULL). Applies migrations
# automatically once the worker is up (see `migrate`) — every deploy lands
# on head schema.
# make up-pipeline        -> pipeline + langfuse (data plane must already be up)
# make up-pipeline FULL=1 -> data + pipeline + langfuse
up-pipeline:
	@if [ "$(FULL)" = "1" ]; then $(MAKE) up-data; fi
	$(MAKE) up-langfuse
	docker compose -f infra/docker-compose.pipeline.yml --env-file .env up -d --build --wait
	$(MAKE) migrate

# make down-pipeline                     -> stop pipeline + langfuse, keep volumes
# make down-pipeline FULL=1               -> also stop data
# make down-pipeline VOLUMES=1            -> also delete volumes (pipeline + langfuse)
# make down-pipeline FULL=1 VOLUMES=1     -> stop everything and delete all volumes
down-pipeline:
	docker compose -f infra/docker-compose.pipeline.yml --env-file .env down $(if $(filter 1,$(VOLUMES)),-v,)
	$(MAKE) down-langfuse
	@if [ "$(FULL)" = "1" ]; then $(MAKE) down-data; fi

# App plane: API + web.
# make up-app        -> app only (data plane must already be up)
# make up-app FULL=1 -> data + app
up-app:
	@if [ "$(FULL)" = "1" ]; then $(MAKE) up-data; fi
	docker compose -f infra/docker-compose.app.yml --env-file .env --profile app up -d --build

down-app:
	docker compose -f infra/docker-compose.app.yml --env-file .env --profile app down $(if $(filter 1,$(VOLUMES)),-v,)
	@if [ "$(FULL)" = "1" ]; then $(MAKE) down-data; fi

# Langfuse plane: self-hosted LLM observability for filter/enrich.
# make up-langfuse        -> langfuse only (data plane must already be up)
# make up-langfuse FULL=1 -> data + langfuse
up-langfuse:
	@if [ "$(FULL)" = "1" ]; then $(MAKE) up-data; fi
	docker compose -f infra/docker-compose.langfuse.yml --env-file .env up -d --wait

down-langfuse:
	docker compose -f infra/docker-compose.langfuse.yml --env-file .env down $(if $(filter 1,$(VOLUMES)),-v,)
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

describe-skills:
	docker compose -f infra/docker-compose.pipeline.yml --env-file .env exec pipeline-worker \
		uv run --package pipeline python -m pipeline.flows.describe_skills

judge:
	docker compose -f infra/docker-compose.pipeline.yml --env-file .env exec pipeline-worker \
		uv run --package pipeline python -m pipeline.flows.judge

prune:
	docker compose -f infra/docker-compose.pipeline.yml --env-file .env exec pipeline-worker \
		uv run --package pipeline python -m pipeline.flows.prune

# Register/refresh Prefect deployment schedules against the running server.
deploy-flows:
	docker compose -f infra/docker-compose.pipeline.yml --env-file .env exec pipeline-worker \
		uv run --package pipeline python -m pipeline.deployments

# Schema migrations (Alembic). Runs automatically at the end of `up-pipeline`;
# call directly to re-apply after pulling new migrations into an
# already-running worker, without restarting it.
migrate:
	docker compose -f infra/docker-compose.pipeline.yml --env-file .env exec pipeline-worker \
		uv run --package pipeline alembic -c apps/pipeline/alembic.ini upgrade head
