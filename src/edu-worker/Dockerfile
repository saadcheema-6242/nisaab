# Same base as API
FROM python:3.12-slim-bookworm
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app

# 1. Copy Monorepo Metadata
COPY pyproject.toml uv.lock /app/

# 2. Copy Source Code, plus what the migration and e2e Cloud Run jobs use
COPY src /app/src
COPY alembic.ini /app/alembic.ini
COPY scripts /app/scripts

# 3. Install Dependencies
WORKDIR /app/src/edu-worker
ENV UV_PROJECT_ENVIRONMENT=/app/.venv
RUN uv sync --frozen

# 4. Run Worker Script
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1
# Polls the jobs table, or serves POST /drain when WORKER_POLL=false (Cloud Run)
CMD ["python", "main.py"]
