FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

FROM base AS dev
COPY backend/pyproject.toml backend/uv.lock /app/backend/
RUN uv sync --project /app/backend
CMD ["uv", "run", "--project", "/app/backend", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

FROM base AS prod
COPY backend/pyproject.toml backend/uv.lock /app/backend/
RUN uv sync --project /app/backend --frozen --no-dev
COPY backend /app/backend
COPY README.md /app/README.md
EXPOSE 8000
CMD ["uv", "run", "--project", "/app/backend", "python", "-m", "backend.main"]
