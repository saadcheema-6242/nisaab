# 4 · Backend

[← Architecture](03-architecture.md) · [Contents](README.md) · [Next: Frontend →](05-frontend.md)

Python 3.12 · FastAPI · SQLAlchemy · PostgreSQL 16 + pgvector · `uv` workspace

---

## The API service — `src/edu-api`

**93 endpoints across 19 routers.** Every one is behind authentication except the
health check.

| Router | Endpoints | Looks after |
|---|---:|---|
| `quizzes` | 16 | Quizzes, questions, generation, attempts, Google Form publishing |
| `flashcard_groups` | 14 | Groups, cards, generation, spaced-repetition progress |
| `documents` | 7 | Upload, processing status, text, deletion |
| `notes` | 7 | Notes and AI note generation |
| `chats` | 6 | Chats, messages, the streaming tutor endpoint |
| `mind_maps` | 5 | Mind maps and their generation |
| `papers` | 5 | Practice papers: create, fetch, submit, mark |
| `projects` | 5 | A student's per-subject workspace |
| `curriculum` | 4 | Subjects, domains, content areas, SLOs |
| `review` | 4 | The teacher review queue |
| `srq` | 4 | Short-response questions and their marking |
| `practice_records` | 3 | What was practised, and how it went |
| `profile` | 3 | Class, group, explanation language |
| `study_plans` | 3 | Generated study plans |
| `users` | 3 | Account and deletion |
| `attempts` · `auth` · `progress` · `usage` | 1 each | History, token check, progress, daily limits |

### Authentication

Production uses **Google Identity Platform**. The browser gets an ID token; the API
verifies it as a JWT against Google's published JWKS for the project, with the key set
cached. Local development falls back to Supabase-issued tokens so the stack can run
without any cloud account.

The API never sees or stores a password.

### Settings

One `pydantic-settings` class in `config.py`, loaded from the environment and `.env`.
Services never read the environment themselves — values are passed in. That is what
keeps business logic testable and the configuration in one discoverable place.

### Error handling

Routers translate domain exceptions into HTTP status codes and nothing else:

| Exception | Status | Meaning |
|---|---|---|
| `NotFoundError` | 404 | No such record, or not this student's |
| `ValueError` | 400 | The request does not make sense |
| `FormsNotConfiguredError` | 503 | A feature is not set up — not the student's fault, not Google's |
| upstream failure | 502 | An external service refused |

The 503/502 split is deliberate. "Google would not create the form" and "nobody has
authorised this yet" are different problems and need different fixes.

---

## The services layer — `src/shared/core`

22 service modules. **All business rules live here**, and nothing here knows about
HTTP.

```
attempts      chats        content       curriculum    document_upload
documents     flashcard_groups           google_forms  mind_maps
notes         papers       practice      profiles      progress
projects      quizzes      search        srq           study_plans
usage         users
```

Both the API and the worker import the same services, so a quiz made by the tutor and a
quiz made by the worker are made by identical code.

### `papers.py` — one source of truth for marks

The most consequential file. It holds the FBISE paper shapes, and one table decides
what every question is worth:

```python
QUESTION_MARKS = {
    "default": {"mcq": 0.5, "srq": 4, "erq": 6},
    "MATH":    {"mcq": 0.75, "srq": 4, "erq": 8},
}
```

**A shorter paper asks fewer questions. It never changes what a question is worth.**
That rule is the reason a mini paper is worth 12 marks rather than some rounded number —
and it is why practising on one teaches the real weights. Full shapes are in
[Curriculum data](08-curriculum-data.md).

---

## The database — `src/shared/db`

**28 models, 41 Alembic migrations.** PostgreSQL 16 with **pgvector** for embeddings.

| Group | Tables |
|---|---|
| **Identity** | `User`, `StudentProfile` |
| **Curriculum** | `Subject`, `GradeSubject`, `CurriculumDomain`, `Slo` |
| **Workspace** | `Project`, `Document`, `DocumentSegment` |
| **Tutor** | `Chat`, `ChatMessage`, `ChatMessagePart` |
| **Study material** | `Quiz`, `QuizQuestion`, `FlashcardGroup`, `Flashcard`, `Note`, `MindMap`, `StudyPlan` |
| **Practice** | `SrqQuestion`, `SrqAttempt`, `PracticePaper`, `PracticeAttempt`, `PracticeRecord`, `FlashcardProgress` |
| **Shared content** | `ContentItem` |
| **Operations** | `Job`, `UserUsage` |

`DocumentSegment` holds the chunk text and its embedding vector — that is the whole of
the RAG index. No separate vector database.

---

## The job queue — `src/shared/queue`

A table, not a broker. The reasoning is in [Architecture](03-architecture.md#why-there-is-no-redis-and-no-celery).

### Seven job types

| Type | Produces |
|---|---|
| `quiz_generation` | A quiz with questions, answers, explanations |
| `flashcard_generation` | A set of cards |
| `note_generation` | A structured note |
| `mind_map_generation` | Nodes and edges |
| `paper_generation` | A full practice paper |
| `document_processing` | Extracted text, OCR if needed, segments, embeddings |
| `chat_title_generation` | A readable title for a chat |

### Lifecycle

```
queued ──claim──► running ──complete──► done
                     │
                     └──fail──► queued (retry, with a delay)
                                  └──► failed (attempts used up)
```

Three properties make this dependable:

- **`FOR UPDATE SKIP LOCKED`** — concurrent workers never claim the same job.
- **`requeue_stale`** — a worker killed mid-job (Cloud Run scaling down, a crash)
  leaves a `running` row with an old `locked_at`; it goes back to `queued`.
- **`run_after`** — retries back off instead of hammering a failing dependency.

---

## The worker — `src/edu-worker`

Polls, claims, dispatches by job type through a processor registry, and reports back.
One processor per job type, each a thin wrapper over the same core services the API
uses.

`WORKER_CONCURRENCY` (default 3) sets how many jobs one instance takes at once.

### Two modes, for cost

| `WORKER_ALWAYS_ON` | Behaviour | Cost |
|---|---|---|
| `false` | Scales to zero. Cloud Scheduler calls `POST /drain` every minute to wake it. Jobs may wait up to ~1 minute | pennies/month |
| `true` | One instance always polling. No wait | ~$1.60/day |

It is `true` for the competition period and should go back to `false` afterwards.

---

[← Architecture](03-architecture.md) · [Contents](README.md) · [Next: Frontend →](05-frontend.md)
