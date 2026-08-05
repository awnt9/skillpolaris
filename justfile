lint file=".":
    @uv run ruff check {{file}}

fix file=".":
    @uv run ruff check --fix {{file}}

format file=".":
    @uv run ruff format {{file}}

pipeline:
    uv run --package pipeline python -m pipeline.flows.ingest

compose *args:
    docker compose -f infra/docker-compose.data.yml --env-file .env {{args}}

compose-pipeline *args:
    docker compose -f infra/docker-compose.pipeline.yml --env-file .env {{args}}

compose-app *args:
    docker compose -f infra/docker-compose.app.yml --env-file .env {{args}}
