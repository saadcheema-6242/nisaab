# NISAAB — Complete Project Overview

## What NISAAB Is

**NISAAB** (نصاب — "curriculum" in Urdu) is an AI-powered tutor built specifically for Pakistani students preparing for the **FBISE FSc Intermediate examination** (grades 11–12). It covers three streams: Pre-Medical, Pre-Engineering, and ICS (Computer Science), across 9 subjects with 869 Student Learning Outcomes (SLOs) drawn directly from the FBISE national curriculum.

Unlike general-purpose education platforms, NISAAB is built around the actual exam: its practice papers follow the real FBISE cognitive distribution (Knowledge 30%, Understanding 50%, Application 20%), its mastery tracking maps to individual SLOs, and its content generation is constrained to the official syllabus.

---

## Project Scale

| Metric | Count |
|--------|-------|
| Python source files | 213 |
| Python lines of code | ~33,000 |
| TypeScript/TSX files | 274 |
| TypeScript lines of code | ~46,000 |
| Total lines of code | ~79,000 |
| API endpoints | 121 |
| Database tables | 27 |
| Alembic migrations | 50 |
| Database columns | ~250 |
| AI tools | 11 |
| Git commits | 291 |
| Contributors | 2 (Richard Amare: 212, Muhammad Saad Cheema: 79) |

---

## Architecture Summary

### Monorepo Structure (uv workspace)
```
edu-agent/
├── src/
│   ├── edu-api/          # FastAPI REST API (25 routers, 121 endpoints)
│   ├── edu-worker/       # Background job processor
│   ├── edu-web/          # React 19 SPA (TanStack Router, Effect atoms)
│   └── shared/
│       ├── ai/           # LLM abstraction, chatbot, tools, agents
│       ├── core/         # Domain logic, services, schemas (no DB imports)
│       ├── db/           # SQLAlchemy models, Alembic migrations
│       └── queue/        # Job queue (PostgreSQL-backed)
├── scripts/
│   ├── seed/             # Curriculum data (JSON → DB)
│   ├── checks/           # 22 domain logic verification scripts
│   └── docs/             # Documentation build tools
└── deploy/
    ├── gcp/              # Google Cloud deployment (production)
    └── azure/            # Azure deployment (legacy)
```

### Key Technology Choices
| Layer | Choice | Rationale |
|-------|--------|-----------|
| LLM | Gemini on Vertex AI | Cost-effective, native file/code execution, Google Cloud integration |
| Agent framework | LangChain/LangGraph | ReAct agent with tool calling, streaming, middleware |
| Database | PostgreSQL + pgvector | Single DB for everything including vectors; no separate vector DB at this scale |
| Auth | Google Identity Platform | Firebase Auth SDK for frontend, Admin SDK for backend verification |
| Frontend | React 19 + Vite + TanStack Router | Type-safe routing, file-based, fast HMR |
| State | Effect Atoms | Lightweight reactive state, composable |
| Hosting | Cloud Run + Firebase Hosting | Scale-to-zero API, CDN for static SPA |
| Job queue | PostgreSQL `jobs` table | No external broker; simple poll/drain model |

---

## Core Features

### 1. AI Tutor (Chatbot)
- LangGraph ReAct agent with 11 tools
- Syllabus-aware: knows which SLOs the student is studying
- RAG over student-uploaded documents (pgvector similarity search)
- Streaming responses via SSE
- Tool call loop detection (prevents 5x repeated syllabus lookups)
- Multi-language support: English, Urdu, Roman Urdu

### 2. Practice System
- **Quizzes**: MCQ with instant feedback, AI-generated from SLOs
- **Flashcards**: Flip-card study with self-rating (Knew it / Still learning)
- **Mind Maps**: Zoomable node-edge graphs (XY Flow)
- **Practice Papers**: Full FBISE-style papers (mini 20min → board 3hr/80 marks)
  - MCQ + SRQ + ERQ sections
  - Cognitive level distribution matching real exam blueprint
  - Bresenham-style level ordering (no three consecutive blocks of same type)
- **SRQ Marking**: AI-powered rubric-based marking of written answers
- **Study Plans**: Personalised plans based on mastery gaps

### 3. Mastery Tracking
- Per-SLO exponentially weighted accuracy
- Every answer moves the estimate by at least 30%
- Self-rated flashcards count half as much (0.5 weight)
- Single `advance()` function used everywhere (prevents disagreement)
- Progress trend graphs with cognitive level breakdown
- Activity calendar

### 4. Content Bank
- Pre-generated, teacher-reviewable content
- Explainers, MCQs, SRQs per SLO
- Practice tools check bank before generating new content
- Teacher review workflow (approve/reject/edit)

### 5. Community
- Discussion posts with file attachments
- Polls with voting
- AI moderation (contact detail detection, content review)
- Report/flag system
- Admin moderation queue

### 6. Weekly Sessions
- Admin-scheduled video call sessions
- Meeting link validation (Google Meet, Zoom, Teams, WebEx only)
- Anti-phishing: rejects credential tricks in URLs
- Join window: 15 minutes before start
- Groups per subject (Physics → all 3; Biology → Pre-Med only)
- Pakistan timezone handling (UTC+5)

### 7. Document Upload & RAG
- Students upload study materials (PDF, images, text)
- Worker processes: OCR (Gemini for PDFs/images) → chunking → embedding
- 3072-dimensional Gemini embeddings stored in pgvector
- Query-time: cosine similarity with absolute floor (0.45) + relative cut (75%)

---

## User Roles

### Student
- Picks grade (11/12) and group (Pre-Med/Pre-Eng/ICS) at onboarding
- Access to AI tutor, practice tools, documents, community
- Daily usage limits (chat: 100, quizzes: 30, flashcards: 20, uploads: 10, posts: 40)
- Can change group (with data migration implications)

### Teacher
- Applies at signup → awaits admin approval
- Reviews AI-generated content (approve/reject)
- Has own dashboard with upcoming sessions
- Can teach specific subjects and grades

### Administrator
- Defined by env var email list (not a database flag — requires redeploy)
- Is also student and teacher (every cohort)
- Manages accounts (ban/unban/delete), moderation queue, class sessions
- Batch operations (delete never-onboarded accounts before a date)

---

## Database Design

### 27 Tables
- **Users & Auth**: `users` (with onboarding state, ban dates, group/grade)
- **Curriculum**: `subjects`, `grade_subjects`, `domains`, `slos` (869 rows)
- **Content**: `chats`, `messages`, `tool_calls`, `quizzes`, `quiz_questions`, `flashcard_groups`, `flashcards`, `notes`, `mind_maps`, `papers`, `paper_sections`, `srq_questions`
- **Practice**: `quiz_attempts`, `flashcard_attempts`, `paper_attempts`, `srq_attempts`, `practice_records`
- **Documents**: `documents`, `document_segments` (with pgvector embedding column)
- **Community**: `community_posts`, `community_attachments`, `community_poll_options`, `community_votes`
- **Infrastructure**: `jobs` (queue), `projects`, `content_items` (review bank), `class_sessions`

### Key Patterns
- UUIDs as primary keys (string, not native UUID)
- `created_at` / `updated_at` on all tables
- Soft references (user_id as string, not FK in some cases)
- Ban state as dates, not boolean flags
- Job queue in same database (no external broker)

---

## Curriculum Data Model

The FBISE curriculum is stored as database rows, not prompts:

```
Subject (e.g. Physics)
└── GradeSubject (Physics XI)
    └── Domain (e.g. Measurements)
        └── SLO (e.g. P-XI-A-01: "Define physics and its scope")
            ├── code: unique identifier
            ├── content_area: topic grouping
            ├── description: learning outcome text
            ├── assessment_form: how it's tested (MCQ, SRQ, ERQ)
            ├── cognitive_levels: K/U/A distribution
            └── periods: teaching periods allocated
```

**869 SLOs** across 9 subjects, seeded from JSON files derived from official FBISE curriculum documents.

---

## Security Model

1. **Authentication**: Firebase ID tokens verified on every API call
2. **Authorization**: Resource ownership enforced at service layer
3. **Admin discovery**: 404 (not 403) on unauthorized admin access
4. **Meeting links**: Validated against allowlist, anti-phishing checks
5. **Community**: AI moderation + personal detail detection + report system
6. **Ban system**: Date-based (no boolean flag disagreement)
7. **Email verification**: Reads claims from both Identity Platform and Supabase formats
8. **Cloud SQL**: Private IP only, no public access
9. **Admin via env var**: No database flag that could be set by SQL injection

---

## Deployment

- **Region**: `asia-south1` (Mumbai) — lowest latency to Pakistan
- **API + Worker**: Cloud Run (scale-to-zero)
- **Database**: Cloud SQL PostgreSQL with pgvector
- **Frontend**: Firebase Hosting with CDN
- **AI**: Vertex AI (Gemini) in same region
- **Storage**: Cloud Storage (GCS)
- **CI/CD**: Cloud Build (parallel Docker builds)
- **Automation**: Single `deploy.sh` script with subcommands

---

## What Makes NISAAB Distinctive

1. **Curriculum as data, not prompts**: 869 SLOs as database rows enable syllabus-aware AI that stays within the actual FBISE scope
2. **Exam-faithful practice**: Papers follow the real cognitive distribution (K:30%, U:50%, A:20%) with Bresenham-style ordering
3. **Single-source mastery**: One `advance()` function used everywhere prevents the overview and trend graph from disagreeing
4. **Teacher-in-the-loop**: AI-generated content goes through teacher review before entering the content bank
5. **Cost-optimised for education**: Scale-to-zero Cloud Run, no separate vector DB, no external message broker, PostgreSQL does everything
6. **Domain logic without database**: Pure functions in `edu-core` — testable offline with 22 check scripts
7. **Anti-phishing in meeting links**: Every URL students click is validated against known meeting hosts
8. **Dates as state**: Ban system uses timestamps as truth, not boolean flags that can disagree
