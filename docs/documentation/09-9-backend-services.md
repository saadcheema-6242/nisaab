> **Superseded.** This describes an earlier version of NISAAB and is no
> longer maintained. The current documentation is
> [docs/handbook](../handbook/README.md), written 9 November 2026.
> This file is kept only so older links still resolve.

# 9. Backend Services

## 9.1 edu-api

| Component | Detail |
|---|---|
| Framework | FastAPI 0.124 on Uvicorn |
| Validation | Pydantic v2 models for every request and response |
| Settings | `pydantic-settings`, reading environment variables and `.env` files |
| Documentation | Scalar, served from the generated OpenAPI schema |
| Uploads | `python-multipart`, streamed to Cloud Storage instead of held in memory |
| Authentication | PyJWT with `cryptography`, verifying Google Identity Platform tokens |

Nineteen routers divide the API by domain: projects, chats, documents, quizzes, flashcards, notes, mind maps, papers, short-response questions, attempts, curriculum, profile, progress, study plans, practice records, usage, review, users and authentication. Together they expose 93 endpoints.

## 9.2 edu-worker

Generation that takes longer than a web request is done in the background. The worker claims jobs from PostgreSQL and passes each to a processor from a registry.

| Processor | Work it performs |
|---|---|
| `document` | Extract text from a PDF or DOCX, split it, embed it and store the segments |
| `quiz` | Generate quiz questions for a topic or outcome |
| `flashcard` | Generate a flashcard set |
| `note` | Generate structured notes |
| `mind_map` | Generate a mind-map graph |
| `paper` | Build a full board-pattern examination paper |
| `chat_title` | Name a conversation from its first exchange |

## 9.3 The job queue

There is no Redis, Celery or other broker. The queue is a table in the same PostgreSQL database. This keeps the deployment to one stateful dependency and makes job state transactional with the data it concerns.

```sql
jobs(id, type, payload JSONB, status, attempts, max_attempts,
     run_after TIMESTAMPTZ, error, created_at, updated_at)
INDEX ix_jobs_status_run_after ON jobs(status, run_after)
```

| Behaviour | How it works |
|---|---|
| Claiming | A worker selects due queued rows and marks them running in one statement, so two workers cannot take the same job. |
| Retry | A failed job records its error, increases `attempts` and is queued again with a later `run_after` until `max_attempts` is reached. |
| Delayed work | `run_after` also allows a job to be scheduled for later. |
| Recovery | `requeue_stale` returns jobs abandoned by a worker that stopped in the middle of a task. |

## 9.4 Scaling behaviour

The worker scales to zero when idle. Cloud Scheduler calls a drain endpoint every minute, which wakes the service, processes everything that is due and returns. A polling mode is also available for demonstration days, when the worker is kept running.
