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

# just down-data      -> stop containers, keep volumes (data survives)
# just down-data -v   -> also delete volumes (wipes the database)
down-data volumes="":
    docker compose -f infra/docker-compose.data.yml --env-file .env down {{ if volumes == "-v" { "-v" } else { "" } }}

# Pipeline plane: Prefect server + worker + langfuse (langfuse is exclusive
# to pipeline, so it's not gated behind --full). Applies migrations
# automatically once the worker is up (see `migrate`) — every deploy lands
# on head schema.
# just up-pipeline        -> pipeline + langfuse (data plane must already be up)
# just up-pipeline --full -> data + pipeline + langfuse
up-pipeline flag="":
    @if [ "{{flag}}" = "--full" ]; then just up-data; fi
    just up-langfuse
    docker compose -f infra/docker-compose.pipeline.yml --env-file .env up -d --build --wait
    just migrate

# just down-pipeline            -> stop pipeline + langfuse, keep volumes
# just down-pipeline --full     -> also stop data
# just down-pipeline "" -v      -> also delete volumes (pipeline + langfuse)
# just down-pipeline --full -v  -> stop everything and delete all volumes
down-pipeline flag="" volumes="":
    docker compose -f infra/docker-compose.pipeline.yml --env-file .env down {{ if volumes == "-v" { "-v" } else { "" } }}
    just down-langfuse "" {{volumes}}
    @if [ "{{flag}}" = "--full" ]; then just down-data {{volumes}}; fi

# App plane: API + web.
# just up-app        -> app only (data plane must already be up)
# just up-app --full -> data + app
up-app flag="":
    @if [ "{{flag}}" = "--full" ]; then just up-data; fi
    docker compose -f infra/docker-compose.app.yml --env-file .env --profile app up -d --build

down-app flag="" volumes="":
    docker compose -f infra/docker-compose.app.yml --env-file .env --profile app down {{ if volumes == "-v" { "-v" } else { "" } }}
    @if [ "{{flag}}" = "--full" ]; then just down-data {{volumes}}; fi

# Langfuse plane: self-hosted LLM observability for filter/enrich.
# just up-langfuse        -> langfuse only (data plane must already be up)
# just up-langfuse --full -> data + langfuse
up-langfuse flag="":
    @if [ "{{flag}}" = "--full" ]; then just up-data; fi
    docker compose -f infra/docker-compose.langfuse.yml --env-file .env up -d --wait

down-langfuse flag="" volumes="":
    docker compose -f infra/docker-compose.langfuse.yml --env-file .env down {{ if volumes == "-v" { "-v" } else { "" } }}
    @if [ "{{flag}}" = "--full" ]; then just down-data {{volumes}}; fi

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
