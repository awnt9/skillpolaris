FROM python:3.14-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

COPY pyproject.toml uv.lock ./
COPY apps/pipeline/pyproject.toml apps/pipeline/
COPY apps/api/pyproject.toml apps/api/

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --package api

COPY apps/api/src ./apps/api/src

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --package api

EXPOSE 8000
CMD ["uv", "run", "--package", "api", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
