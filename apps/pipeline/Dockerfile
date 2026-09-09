FROM python:3.14-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml uv.lock ./
COPY apps/pipeline/pyproject.toml apps/pipeline/
COPY apps/api/pyproject.toml apps/api/

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --package pipeline

COPY apps/pipeline/src ./apps/pipeline/src
COPY apps/pipeline/alembic.ini apps/pipeline/alembic.ini
COPY apps/pipeline/alembic ./apps/pipeline/alembic

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --package pipeline

# Registers deployments and polls the work pool. Migrations are applied
# manually: `just migrate` / `make migrate`.
CMD ["uv", "run", "--package", "pipeline", "python", "-m", "pipeline.worker"]
