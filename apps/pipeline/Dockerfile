FROM python:3.11-slim

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

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --package pipeline

CMD ["uv", "run", "--package", "pipeline", "python", "-m", "pipeline.flows.ingest"]
