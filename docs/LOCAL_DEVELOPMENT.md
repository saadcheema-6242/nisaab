# Local Development Guide

Everything runs on your machine except the AI, which uses a free Gemini API key.
Production runs the same code on Google Cloud; see [deploy/gcp/README.md](../deploy/gcp/README.md).

| Piece | Local | Production |
|---|---|---|
| Database (Postgres + pgvector), file storage, logins | Supabase CLI in Docker | Supabase project |
| API (FastAPI) | `uv run`, port 8010 | Cloud Run `edu-api` |
| Worker (background jobs) | `uv run`, polls the `jobs` table | Cloud Run `edu-worker` |
| Web (React + Vite) | `pnpm dev`, port 3000 | Cloud Run `edu-web` |
| AI | Gemini API (free AI Studio key) | Vertex AI Gemini |

## Prerequisites

- Python 3.12 via [uv](https://docs.astral.sh/uv/) (`pip install uv`, then use `uv` or `python -m uv`)
- Node.js 20+ and pnpm 10
- Docker Desktop (for the Supabase CLI)
- A Gemini API key from https://aistudio.google.com/apikey

## First-time setup

```bash
# 1. Dependencies
uv sync --all-packages
(cd src/edu-web && pnpm install)

# 2. Local Supabase (any folder outside the repo, e.g. ../local-supabase)
npx supabase init          # once
npx supabase start         # prints the URLs and keys used below

# 3. Settings: copy the template and fill in the keys printed by `supabase start`
cp .env.example .env
#   VITE_SUPABASE_ANON_KEY    = ANON_KEY
#   SUPABASE_SERVICE_ROLE_KEY = SERVICE_ROLE_KEY
#   SUPABASE_JWT_SECRET       = JWT_SECRET
#   LLM_API_KEY               = your Gemini key

# 4. Tables (also locks them away from Supabase's public REST API)
DATABASE_URL="postgresql+psycopg2://postgres:postgres@127.0.0.1:54322/postgres" uv run alembic upgrade head
```

The Supabase CLI config must have `[storage] enabled = true` (it is by default). Services the app
does not use (realtime, studio, edge runtime, analytics) can be disabled in its `config.toml`.

## Run

Each in its own terminal, from the repository root:

```bash
# API on http://127.0.0.1:8010 (docs at /)
cd src/edu-api && PYTHONUTF8=1 uv run --package edu-api python main.py

# Worker (processes uploads and generation jobs)
cd src/edu-worker && PYTHONUTF8=1 uv run --package edu-worker python main.py

# Web on http://localhost:3000
cd src/edu-web && pnpm dev
```

`PYTHONUTF8=1` avoids a Windows console encoding crash in the worker's log output.
Port and worker settings can be overridden per service in `src/edu-api/.env` and `src/edu-worker/.env`
(e.g. `PORT=8010`, `WORKER_CONCURRENCY=1`); shared settings live in the root `.env`.

Sign up in the web app with any email; the local Supabase does not send confirmation emails.

## Checks

```bash
# AI provider: models, chat, tool calling, embeddings
uv run --package edu-api python scripts/check_llm.py

# End to end (worker must be running): upload -> index -> search -> chat -> quiz, flashcards, note, mind map
uv run --package edu-api python scripts/e2e_ai_check.py            # sample Word document
uv run --package edu-api python scripts/e2e_ai_check.py --pdf file.pdf
```

## How background jobs work

The API writes a row to the `jobs` table (`edu_queue.QueueService.send_message`). The worker claims due jobs
with `SELECT … FOR UPDATE SKIP LOCKED`, runs them, and retries failures up to 3 times (30 s, then 60 s later)
before marking them `failed` with the error in `last_error`. Jobs left `running` by a crashed worker are
requeued after 30 minutes.

On Cloud Run the worker usually scales to zero: it serves `POST /drain` (with `WORKER_POLL=false` and `PORT`
set), and Cloud Scheduler calls it every minute.

## AI providers

`LLM_PROVIDER` in `.env` selects `gemini` (local), `vertex` (production), `openai` or `azure`.
Models can be set per task: `LLM_TUTOR_MODEL`, `LLM_GENERATION_MODEL`, `LLM_MARKING_MODEL`, `LLM_OCR_MODEL`
(default `LLM_CHAT_MODEL`). `LLM_FALLBACK_MODELS` lists models to try when one hits a rate limit or quota;
on the free tier each model has its own daily quota (`gemini-3.5-flash` only ~20 requests/day).

Documents are read locally (PDF, Word, text, Markdown, HTML); scanned PDFs and photos are transcribed by Gemini.

## Database changes

```bash
# after editing src/shared/db/src/edu_db/models.py
DATABASE_URL="postgresql+psycopg2://postgres:postgres@127.0.0.1:54322/postgres" \
  uv run alembic revision --autogenerate -m "describe the change"
DATABASE_URL="postgresql+psycopg2://postgres:postgres@127.0.0.1:54322/postgres" uv run alembic upgrade head
```

New tables are covered by the lock-down migration's default privileges, but enable row level security
on them in the migration as well (`ALTER TABLE … ENABLE ROW LEVEL SECURITY`).

## Troubleshooting

- **Port 8000 in use**: set `PORT=8010` in `src/edu-api/.env` and `VITE_SERVER_URL=http://127.0.0.1:8010` in `.env`.
- **Web shows "Invalid environment variables"**: the web app reads the **root** `.env` (`envDir` in `vite.config.ts`).
- **429 / quota errors**: free-tier limits; add fallback models or wait for the daily reset.
- **Documents stuck in "processing"**: the worker is not running; check its terminal, or the `jobs` table
  (`status`, `last_error`).
