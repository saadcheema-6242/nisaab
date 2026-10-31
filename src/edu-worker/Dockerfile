# Same base as API
FROM python:3.12-slim-bookworm
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app

# Diagrams are drawn with Pillow, and the slim image ships no fonts at all.
# DejaVu carries the Greek, the subscripts and the ohm sign the labels need.
RUN apt-get update && apt-get install -y --no-install-recommends fonts-dejavu-core && rm -rf /var/lib/apt/lists/*

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
# Pillow draws the question diagrams. It goes in on top of the frozen lock
# rather than through it, because uv could not write a new uv.lock on the
# machine this was built from. Fold it into the lock with `uv lock` when that
# is possible; installing it here changes nothing else that is already pinned.
RUN uv pip install --python /app/.venv/bin/python "pillow>=11,<12"

# 4. Run Worker Script
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1
# Polls the jobs table, or serves POST /drain when WORKER_POLL=false (Cloud Run)
CMD ["python", "main.py"]
