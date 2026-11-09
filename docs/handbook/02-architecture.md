# 2. Architecture

## The shape of it

A uv workspace holding five Python packages and one React application.

```
edu-agent/
  src/
    edu-api/           FastAPI. Every HTTP route. Thin.
    edu-worker/        Background jobs: generation, document processing.
    edu-web/           React 19 + Vite. The only thing a student sees.
    shared/
      core/            Domain logic and services. The centre of gravity.
      db/              SQLAlchemy models, Alembic migrations.
      ai/              Models, prompts, agents, tools.
      queue/           Job queue.
  deploy/gcp/          deploy.sh and its configuration.
  scripts/             Checkers, seeding, the end-to-end suite.
  docs/handbook/       This.
```

`src/eduagent-vibecode` and `deploy/azure` are from the project this was
forked from and are not part of the running system.

## Where the thinking lives

The important thing about this layout is that **the router is thin and
the core is thick**. A route in `edu-api` reads the token, calls one
service method, and returns a DTO. It makes no decisions.

Decisions live in `shared/core`, and they are split in two:

**`edu_core/*.py` — pure modules.** Arithmetic and rules with no database
import at all: `mastery.py`, `grading.py`, `weekly_session.py`,
`roles.py`, `progress_trend.py`, `paper_blueprint.py`,
`community_rules.py` and the rest. Give them values, get values back.

**`edu_core/services/*.py` — services.** These open sessions, read rows,
and call the pure modules to decide what the rows mean.

That split is the single most load-bearing convention in the codebase,
and chapter 13 explains why it exists. The short version: it means the
rules can be checked by a script that runs in two seconds on a laptop
with no Postgres, no pgvector and no API key.

## How a request flows

A student answers a practice question:

1. `edu-web` sends `POST /api/v1/practice-records` with an Identity
   Platform ID token.
2. `edu-api/auth.py` verifies the token against Google's public keys and
   loads (or creates) the `User`.
3. The route calls `PracticeService`.
4. The service writes a `PracticeRecord`, then asks the pure
   `mastery.advance()` what the new estimate is.
5. A DTO goes back. The page updates.

No step 4 happens in the router, and no step 2 happens in the service.

## The two runtimes

**`edu-api`** serves HTTP, synchronously. It never calls a model for
anything slow.

**`edu-worker`** does the slow work: generating quizzes, flashcards, mind
maps and study plans; processing uploaded documents into embedded
segments. Work is handed over through the `jobs` table.

They share the same image build and the same `shared/*` packages, so a
service is callable from either.

## Infrastructure

Everything is Google Cloud, project `fbise-tutor-2026`, region
`asia-south1` (Mumbai — the closest region to Pakistan).

| Piece | Service |
|---|---|
| API and worker | Cloud Run |
| Database | Cloud SQL for PostgreSQL, with pgvector |
| The site | Firebase Hosting |
| Documents and media | Cloud Storage |
| Sign-in | Identity Platform (Firebase Auth) |
| Models | Vertex AI (Gemini) |

One provider, deliberately: see chapter 13.

The frontend is a static bundle on Firebase Hosting calling Cloud Run. It
is not server-rendered, so there is no Node process in production.

## Retrieval

Document segments and syllabus content are embedded and stored in
Postgres with pgvector, in the same database as everything else. There is
no separate vector service. At this scale — one board, two years, nine
subjects — a dedicated vector database would be an extra system to run,
pay for and keep in sync for no gain.

Next: [3. Data model](03-data-model.md)
