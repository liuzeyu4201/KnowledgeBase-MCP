FROM python:3.13-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:${PATH}"

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

COPY pyproject.toml README.md ./
COPY knowledgebase ./knowledgebase
COPY sql ./sql

FROM base AS dev

RUN uv sync --no-dev

CMD ["sh", "-c", "uv sync --no-dev && python -m knowledgebase.mcp.server"]

FROM base AS prod

RUN uv sync --no-dev

CMD ["python", "-m", "knowledgebase.mcp.server"]
