# Database Models Analysis — NISAAB

## Overview

NISAAB uses **PostgreSQL with pgvector** as its sole data store. The ORM is **SQLAlchemy 2.x** with the modern `Mapped`/`mapped_column` typed style and `declarative_base()`. Database sessions are managed via a singleton engine + session factory initialised once at startup (`init_db`), with a small connection pool (5 + 5 overflow) tuned for Cloud SQL's limited connection budget shared across API, worker and jobs.

Migrations are handled by **Alembic**, with **50 migration versions** in total, reflecting a mature schema that has evolved from a generic EduAgent base into a specialised FBISE curriculum platform.

---

## Base & Session Setup

### `base.py`
- Single `Base = declarative_base()` — all models inherit from this.

### `session.py`
- **Singleton pattern**: global `_engine` and `_SessionLocal` initialised once via `init_db(database_url)`.
- **Pool config**: `pool_size=5`, `max_overflow=5`, `pool_recycle=1800`, `pool_pre_ping=True` — conservative, Cloud SQL-appropriate.
- **`get_db()`**: FastAPI dependency yielding a session with proper close-on-exit.
- **`get_session_factory()`**: For manual session use in the worker.
- **`create_db_and_tables()`**: Dev/test convenience using `Base.metadata.create_all`.

---

## All Tables / Entities (27 tables)

### 1. User & Identity (3 tables)

| Table | PK | Purpose |
|---|---|---|
| `users` | `id` (String, Auth UUID) | Core user record with role (student/teacher), suspension fields, teacher approval |
| `student_profiles` | `user_id` (FK → users) | FSc student details: grade (11/12), group (PRE_MED/PRE_ENG/ICS), explanation language, exam year |
| `teacher_profiles` | `user_id` (FK → users) | Teacher details: subjects (JSON list), grades (JSON list), school, about text, application timestamp |

**Key design notes:**
- User PK is a **string** mapped to the auth provider's UUID (Supabase or Firebase Identity Platform), not an auto-increment.
- **Role** (`student`/`teacher`) is stored in DB, not env vars.
- **Admin** status is env-var-only (`ADMIN_EMAILS`), deliberately requiring a deploy to change.
- **Suspension** uses dates only (`banned_at`, `banned_until`) — no boolean flag, avoiding stale-flag bugs on temporary bans.
- **Teacher approval** uses `teacher_approved_at` (datetime, nullable) — the date IS the state.

### 2. Project & Document (3 tables)

| Table | PK | Purpose |
|---|---|---|
| `projects` | `id` (UUID string) | A student's workspace — either `subject_workspace` (auto-created per FBISE subject) or `custom` |
| `documents` | `id` (UUID string) | Uploaded files (PDF, DOCX, etc.) with processing status |
| `document_segments` | `id` (UUID string) | Chunked text from documents with **pgvector embeddings** (3072 dimensions) |

**Key design notes:**
- Projects link to `grade_subjects` (FK), tying each workspace to the FBISE curriculum.
- Projects have `archived_at` for soft-archive when a student drops a subject (not deleted — preserves their work).
- Document segments use `Vector(3072)` from the pgvector extension for RAG retrieval — no external vector DB.

### 3. Chat & Messaging (3 tables)

| Table | PK | Purpose |
|---|---|---|
| `chats` | `id` (UUID string) | A conversation thread within a project |
| `chat_messages` | `id` (UUID string) | Individual messages (user/assistant roles) |
| `chat_message_parts` | `id` (UUID string) | Multi-part message content: text, files, tool calls, source documents |

**Key design notes:**
- Messages are multi-part: each `ChatMessage` has ordered `ChatMessagePart` rows with `part_type` discriminator.
- Tool calls stored with full input/output/state in JSON columns, making the entire agentic conversation replayable.

### 4. Study Content Generation (7 tables)

| Table | PK | Purpose |
|---|---|---|
| `flashcard_groups` | `id` (UUID string) | Named sets of flashcards tied to a project and optionally an SLO |
| `flashcards` | `id` (UUID string) | Individual Q&A flashcards with difficulty, position ordering, SLO code |
| `quizzes` | `id` (UUID string) | Named MCQ quiz sets tied to a project and SLO |
| `quiz_questions` | `id` (UUID string) | MCQ questions with 4 options, images, option images, image credits, cognitive level |
| `notes` | `id` (UUID string) | Markdown notes generated for a project |
| `mind_maps` | `id` (UUID string) | JSON-structured mind map data (nodes/edges) |
| `study_plans` | `id` (UUID string) | JSON study plans with weak topic identification |

**Key design notes:**
- All content generation tables carry `slo_code` for FBISE curriculum alignment.
- Quiz questions support **images**, **option images** (JSON dict), and **image credits** (for openly-licensed sources).
- `cognitive_level` (K/U/A — Knowledge/Understanding/Application) aligns with FBISE's marking scheme.

### 5. FBISE Curriculum (4 tables)

| Table | PK | Purpose |
|---|---|---|
| `subjects` | `id` (UUID string) | FSc subjects (PHY, CHEM, BIO, MATH, CS) with sort order |
| `grade_subjects` | `id` (UUID string) | Subject × grade × scheme (e.g., Physics XI ISS-2024) |
| `curriculum_domains` | `id` (UUID string) | Domains within a grade-subject (e.g., B — Mechanics) |
| `slos` | `id` (UUID string) | Student Learning Outcomes — the atomic unit of the curriculum |

**Key design notes:**
- This is the **core product model** — the entire platform hangs off these rows.
- `Slo` stores `assessment_form` (summative/formative/practical), `cognitive_levels` (JSON array of K/U/A), and `periods`.
- SLO codes follow a systematic pattern: `P-11-B-05` (Physics, grade 11, domain B, SLO 5).
- 869 SLOs seeded for Part 1 across all five subjects.

### 6. Practice & Assessment (5 tables)

| Table | PK | Purpose |
|---|---|---|
| `practice_records` | `id` (UUID string) | Individual practice outcomes — flashcard or quiz answers with correctness and score |
| `flashcard_progress` | `id` (UUID string) | Spaced-repetition-style mastery tracking per flashcard |
| `practice_attempts` | `id` (UUID string) | Completed attempts at a quiz, flashcard set, or paper |
| `srq_questions` | `id` (UUID string) | Short-response questions with rubric (JSON: points + marks) |
| `srq_attempts` | `id` (UUID string) | Student's written answer to an SRQ with AI-estimated marks and detailed result |
| `practice_papers` | `id` (UUID string) | Full FBISE-style practice papers (MCQ + SRQ + ERQ sections in JSON) |
| `content_items` | `id` (UUID string) | Pre-generated, teacher-reviewable content bank (explainers, MCQs, SRQs) |

### 7. Community / Classroom (5 tables)

| Table | PK | Purpose |
|---|---|---|
| `community_posts` | `id` (UUID string) | Posts in grade+group rooms, with AI moderation fields and poll support |
| `community_attachments` | `id` (UUID string) | Media attached to posts (images, audio, files) |
| `community_poll_options` | `id` (UUID string) | Poll answer choices |
| `community_poll_votes` | `id` (UUID string) | One vote per student per poll (enforced by unique constraint) |
| `community_reports` | `id` (UUID string) | Student reports on posts (one per student per post, enforced) |

**Key design notes:**
- Rooms scoped by `(grade, group_code)` — **denormalised onto each post** so moving grade/group doesn't rewrite history.
- Threading is **single-level only** (`parent_id` FK to self).
- **AI moderation** built into `CommunityPost`: `review_finding`, `review_confidence`, `review_why`, `review_severity`.
- Unique constraints enforce one vote per poll and one report per post per student.

### 8. Infrastructure (2 tables)

| Table | PK | Purpose |
|---|---|---|
| `jobs` | `id` (UUID string) | Background job queue with status, retries, locking |
| `user_usage` | `id` (UUID string) | Daily usage counters per user |

---

## Relationship Map (Foreign Keys)

```
users
 ├── projects (1:N, CASCADE)
 │    ├── documents (1:N, CASCADE)
 │    │    └── document_segments (1:N, CASCADE)
 │    ├── chats (1:N, CASCADE)
 │    │    └── chat_messages (1:N, CASCADE)
 │    │         └── chat_message_parts (1:N, CASCADE)
 │    ├── flashcard_groups (1:N, CASCADE)
 │    │    └── flashcards (1:N, CASCADE)
 │    ├── quizzes (1:N, CASCADE)
 │    │    └── quiz_questions (1:N, CASCADE)
 │    ├── notes (1:N, CASCADE)
 │    ├── mind_maps (1:N, CASCADE)
 │    ├── study_plans (1:N, CASCADE)
 │    ├── practice_records (1:N, CASCADE)
 │    ├── practice_attempts (1:N, CASCADE)
 │    ├── practice_papers (1:N, CASCADE)
 │    └── srq_questions (1:N, CASCADE)
 │         └── srq_attempts (1:N, CASCADE)
 ├── student_profiles (1:1, CASCADE)
 ├── teacher_profiles (1:1, CASCADE)
 ├── user_usage (1:1, CASCADE)
 ├── community_posts (1:N, CASCADE)
 │    ├── community_attachments (1:N, CASCADE)
 │    ├── community_poll_options (1:N, CASCADE)
 │    │    └── community_poll_votes (1:N, CASCADE)
 │    ├── community_reports (1:N, CASCADE)
 │    └── community_posts (self-ref, 1:N, CASCADE)
 └── class_sessions (teacher_id → users, SET NULL)

subjects
 └── grade_subjects (1:N, CASCADE)
      ├── curriculum_domains (1:N, CASCADE)
      │    └── slos (1:N, CASCADE)
      └── content_items (1:N, CASCADE)

projects.grade_subject_id → grade_subjects.id (SET NULL)
```

---

## Key Design Patterns

1. **String UUIDs as Primary Keys** — not native Postgres UUID type, ensuring compatibility across auth provider IDs.
2. **Dates as State (No Boolean Flags)** — suspension, teacher approval, archive status all use timestamps.
3. **Denormalisation Where Justified** — community posts carry grade/group; class sessions carry teacher_name.
4. **pgvector for RAG** — `Vector(3072)` in document_segments. No separate vector database.
5. **Database-Backed Job Queue** — `jobs` table replaces external message queues with poll-based processing.
6. **JSON for Structured Payloads** — paper sections, rubrics, SRQ results, mind map data, tool call I/O, image credits.
7. **Cascade Deletes Throughout** — except `ClassSession.teacher_id` (SET NULL, sessions survive teacher removal).
8. **Server Defaults** — ensuring correct values even for raw SQL inserts or migrations.

---

## Migration History

**50 Alembic migrations** trace the evolution from a generic EduAgent to the FBISE-specific platform: initial models → pgvector → FBISE curriculum tables → community + moderation → teacher accounts → class sessions → practice papers + SRQ marking → content bank → user suspension → cleanup (dropped soft-delete, removed old spaced repetition, renamed study_attempt to practice_record).

---

**Total: ~27 tables, 50 migrations, ~250 columns.**
