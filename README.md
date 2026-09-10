# SkillPolaris

A pipeline that turns real software job postings into an enriched, queryable picture of the labor market, plus an API/web app that matches a candidate's CV against it.

## Getting Started

### Prerequisites

- Docker + Docker Compose
- [`just`](https://github.com/casey/just) or `make` (optional, both wrap the same `docker compose` commands below)

### 1. Configure

```bash
cp .env.example .env
```

Fill in `.env` — at minimum `POSTGRES_*`, `LLM_BASE_URL`/`LLM_API_KEY`/`LLM_MODEL`/`FILTER_LLM_MODEL` (any OpenAI-compatible endpoint), and the `LANGFUSE_*` secrets (`openssl rand -hex 16` / `-hex 32` as noted inline). Every required variable is listed there with a comment; extractor credentials (France Travail, Adzuna, etc.) are optional, only needed for the sources that require them.

### 2. Bring up the stack

**With `just`:**

```bash
just up-pipeline --full   # Postgres + Langfuse + Prefect server/worker (runs migrations)
just up-app               # API + web
```

**With `make`:**

```bash
make up-pipeline FULL=1   # Postgres + Langfuse + Prefect server/worker (runs migrations)
make up-app                # API + web
```

**With plain `docker compose`:**

```bash
docker compose -f infra/docker-compose.data.yml --env-file .env up -d --wait
docker compose -f infra/docker-compose.langfuse.yml --env-file .env up -d --wait
docker compose -f infra/docker-compose.pipeline.yml --env-file .env up -d --build --wait
docker compose -f infra/docker-compose.pipeline.yml --env-file .env exec pipeline-worker \
  uv run --package pipeline alembic -c apps/pipeline/alembic.ini upgrade head
docker compose -f infra/docker-compose.app.yml --env-file .env --profile app up -d --build
```

### 3. Open it

| Service | URL |
|---|---|
| Web app | http://localhost:3000 |
| API docs | http://localhost:8000/docs |
| Prefect UI | http://localhost:4200 |
| Langfuse (LLM traces) | http://localhost:3001 |
| pgweb (DB browser) | http://localhost:8081 |

`extract` and `sync-keywords` run on their own schedule once the pipeline is up (see `EXTRACT_CRON`/`SYNC_KEYWORDS_CRON` in `.env`). To run any flow on demand, see the one-shot targets in the `justfile`/`Makefile` (`extract`, `filter`, `enrich`, `judge`, `describe-skills`, `prune`).
