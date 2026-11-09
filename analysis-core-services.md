# Core Business Logic Analysis — NISAAB

## Overview

The `edu-core` package contains all domain logic, services, and schemas. It imports **no database models**, making it testable offline — the 22 check scripts verify domain rules without a database or model key.

---

## Domain Modules (Pure Logic, No DB)

### Roles (`roles.py`)
Three account types:
- **Student**: picks grade (11/12) and group (PRE_MED/PRE_ENG/ICS) at onboarding
- **Teacher**: claims role at signup → waits for admin approval → gets dashboard
- **Administrator**: on env-var email list; is also student (every cohort) and teacher

Key rules:
- `is_approved_teacher()`: role == TEACHER AND approved_at is not None (both halves required)
- `can_teach()`: approved teacher OR admin
- `needs_onboarding()`: returns route ("/onboarding", "/awaiting-approval") or None
- `teaches()`: checks subject_code ∈ teacher's subjects AND grade ∈ teacher's grades

### Mastery (`mastery.py`)
Exponentially weighted accuracy per SLO:
- First answer sets starting point; each subsequent answer moves estimate by ≥30%
- Written answers count as share of marks (0..1)
- Flashcards (self-rated) move estimate half as much (`SELF_RATED_WEIGHT = 0.5`)
- Single `advance()` function used by both overview and trend graph (prevents disagreement)

### Paper Blueprint (`paper_blueprint.py`)
FBISE Assessment Framework:
- **Cognitive levels**: K (Knowledge) 30%, U (Understanding) 50%, A (Application) 20%
- `cognitive_targets(total)`: Largest-remainder allocation (always sums exactly)
- `level_order()`: Bresenham-style distribution (no three blocks of K/U/A)
- `assign_levels()`: SLO × level pairing, rotating across domains, capped per SLO
- `choice_pairs()`: Internal choice options from same domain and level
- `dedupe()`: Prevents duplicate questions across parallel generation batches

### Weekly Sessions (`weekly_session.py`)
- Meeting link validation against allowed hosts (Google Meet, Zoom, Teams, WebEx)
- Rejects credential tricks (`user@host` in URL)
- Join window: 15 minutes before start until end
- Groups for subject: Physics serves all 3 groups; Biology serves Pre-Medical only
- Times stored UTC, displayed in PKT (UTC+5)

### Moderation (`moderation.py`)
Account suspension system:
- Three states: active / temporary / permanent
- Dates are the state (no boolean flags)
- `is_banned()`: checks banned_at + expired temporary bans
- `ban_message()`: tells the person when it ends and why
- Email verification: reads claims from both Identity Platform and Supabase formats

### Community Rules (`community_rules.py`)
- Contact detail detection (prevents sharing phone numbers, emails in posts)
- Upload rules (file types, sizes)
- Poll rules (option limits)
- AI review integration

### Grading (`grading.py`)
- Point-by-point marking against rubric schemes
- Score normalization

### Answer Check (`answer_check.py`)
- Written answer validation and AI-estimated marking
- SRQ rubric evaluation

### Progress Trend (`progress_trend.py`)
- Mastery over time graphs
- Activity calendar
- Cognitive level breakdown
- Pakistan timezone handling (UTC+5)

### Other Domain Modules
- `personal_details.py` — PII detection in posts
- `group_change.py` — GROUP_SUBJECTS mapping (which subjects each stream takes)
- `code_run.py` — Code execution result parsing
- `plain_math.py` — LaTeX to plain text for accessibility
- `openly_licensed.py` — Image credit/attribution handling
- `community_media.py` — Media upload rules for posts
- `community_poll.py` — Poll validation
- `community_review.py` — Review verdict handling
- `chat_attachments.py` — Chat file upload handling
- `practice_options.py` — Practice configuration options
- `tool_loops.py` — Tool call loop detection (prevents repeating same tool call)
- `study_plan_blueprint.py` — Study plan generation logic
- `storage.py` — Storage abstraction (GCS or Supabase)
- `exceptions.py` — NotFoundError, UsageLimitExceededError

---

## Services Layer (Database Access)

### Content Services
- **ChatsService** — conversation CRUD, message streaming, tool call persistence
- **QuizService** — quiz generation (from AI or content bank), question management
- **FlashcardGroupService** — flashcard set generation and management
- **NotesService** — note generation and storage
- **MindMapService** — mind map generation and storage
- **PaperService** — practice paper orchestration (MCQ + SRQ + ERQ sections)
- **SrqService** — short-response question generation and AI marking
- **StudyPlanService** — study plan generation from mastery data
- **ContentService** — teacher-reviewable content bank management

### User & Account Services
- **UsersService** — account CRUD, onboarding
- **ProfileService** — student/teacher profile management
- **TeachersService** — teacher approval workflow
- **AdminService** — account management, suspension, moderation queue

### Curriculum Services
- **CurriculumService** — FBISE curriculum CRUD (subjects, domains, SLOs)
- **SearchService** — RAG search over document embeddings

### Community Services
- **CommunityService** — posts, replies, polls, votes, reports, media
- **ModerationQueueService** — AI-flagged posts for admin review
- **ClassSessionService** — weekly session scheduling and management

### Infrastructure Services
- **UsageService** — per-user daily rate limiting
- **DocumentUploadService** — file upload processing pipeline
- **ProgressService** — mastery aggregation and progress views
- **PracticeService** — practice record tracking
- **ProjectService** — workspace management

---

## Schemas (DTOs)

Pydantic models for request/response:
- `profiles.py` — StudentProfile, TeacherProfile, OnboardingData
- `curriculum.py` — Subject, GradeSubject, Domain, Slo
- `chats.py` — ChatCreate, MessageCreate, StreamEvent
- `quizzes.py` — QuizCreate, QuizQuestion, QuizAttempt
- `flashcards.py` — FlashcardGroup, Flashcard
- `papers.py` — PaperCreate, PaperSection, PaperAttempt
- `community.py` — PostCreate, PollCreate, ReportCreate
- `sessions.py` — SessionCreate, SessionSchedule
- `teachers.py` — TeacherApplication, ApprovalDecision
- `admin.py` — SuspensionAction, AccountList
- `progress.py` — MasteryOverview, TrendData, ActivityCalendar
- `usage.py` — UsageLimits, UsageStatus
- `content.py` — ContentItem, ReviewDecision

---

## Key Design Patterns

1. **Domain logic imports no database** — pure functions testable offline
2. **Dates as state** — no boolean flags; timestamps ARE the truth
3. **Single source of arithmetic** — mastery `advance()` used everywhere to prevent disagreement
4. **Defensive validation** — meeting links, personal details, community content all checked
5. **Usage limiting** — per-user daily caps on chat messages (100), quizzes (30), flashcards (20), uploads (10), posts (40)
6. **Content bank** — pre-generated teacher-reviewable content; practice tools check bank before generating new
