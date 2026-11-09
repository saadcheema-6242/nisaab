# API Routers Analysis — NISAAB

## Overview

The FastAPI backend exposes **121 endpoints** across **25 routers**, all under `/api/v1/`. Every endpoint requires Firebase Auth (via `get_current_user` dependency) except the health check. Routers are grouped by domain: content creation, practice, community, curriculum, admin, and user management.

---

## Router Inventory

### Authentication & Users
| Router | Prefix | Endpoints | Purpose |
|--------|--------|-----------|---------|
| `auth.py` | `/api/v1/auth` | 1 | `GET /me` — returns authenticated user |
| `users.py` | `/api/v1/users` | 3 | Get own account, list self, delete own account |
| `profile.py` | `/api/v1/users` | 5 | Profile state, update profile, onboarding, group change |

### Content Creation (Project-Scoped)
All under `/api/v1/projects/{project_id}/...`

| Router | Resource | Endpoints | Key Operations |
|--------|----------|-----------|----------------|
| `chats.py` | `/chats` | 6 | CRUD + streaming chat completions (SSE) |
| `quizzes.py` | `/quizzes` | 14 | CRUD + AI generation + stream + questions CRUD + reorder + attempts |
| `flashcard_groups.py` | `/flashcard-groups` | 13 | CRUD + AI generation + stream + individual flashcard CRUD + attempts |
| `notes.py` | `/notes` | 7 | CRUD + AI generation + stream |
| `mind_maps.py` | `/mind-maps` | 5 | List + get + delete + create + stream generation |
| `papers.py` | `/papers` | 5 | Create + list + get + save answers + submit for marking |
| `srq.py` | `/srq` | 4 | Create + list + get + AI marking |
| `documents.py` | `/documents` | 7 | Upload (multipart) + create + get + preview + list + update + delete |
| `study_plans.py` | `/study-plans` | — | Study plan generation and retrieval |

### Practice & Progress
| Router | Prefix | Endpoints | Purpose |
|--------|--------|-----------|---------|
| `practice_records.py` | `.../practice-records` | 3 | Get records, create record, batch create |
| `attempts.py` | `.../attempts` | 1 | Practice history list |
| `progress.py` | `.../progress` | 2 | Mastery overview + trend graphs |
| `usage.py` | `.../usage` | 1 | Daily usage status |

### Community
| Router | Prefix | Endpoints | Purpose |
|--------|--------|-----------|---------|
| `community.py` | `.../community` | 7 | Posts (with files), voting, reporting, attachments, warnings, delete |

### Curriculum
| Router | Prefix | Endpoints | Purpose |
|--------|--------|-----------|---------|
| `curriculum.py` | `/api/v1/curriculum` | 4 | Grade-subjects list, curriculum tree, SLO by code, search SLOs |

### Teacher & Admin
| Router | Prefix | Endpoints | Purpose |
|--------|--------|-----------|---------|
| `teachers.py` | `/api/v1/teachers` | 5 | Account state, apply, withdraw, approval queue, approve/reject |
| `review.py` | `/api/v1/review` | 4 | Reviewer state, content items list, summary, approve/reject item |
| `sessions.py` | `/api/v1/sessions` | 6 | Student view, teacher dashboard, admin CRUD, assign teacher |
| `admin.py` | `/api/v1/admin` | 10 | Admin state, user list/detail, ban/unban, delete user(s), moderation queue |

### Workspace
| Router | Prefix | Endpoints | Purpose |
|--------|--------|-----------|---------|
| `projects.py` | `/api/v1/projects` | 5 | CRUD for student workspaces |

---

## Endpoint Patterns

### Streaming
Content generation endpoints offer dual modes:
- `POST /{id}/generate` — synchronous, returns completed resource
- `POST /{id}/generate/stream` — SSE stream via `StreamingResponse`, returns chunks as they generate

Chat completions use the streaming path exclusively (`POST /chats/{id}/completions`).

### Request Validation
- `routers/schemas.py` — shared Pydantic models for request bodies (`ChatCompletionRequest`, `ChatCreate`, `FilePart`, etc.)
- Each router imports domain-specific DTOs from `edu_core.schemas`
- File uploads use FastAPI's `UploadFile` with base64 encoding for chat attachments

### Authentication & Authorization
- **All routes**: `Depends(get_current_user)` — Firebase ID token required
- **Admin routes**: `require_admin()` — checks email against `ADMIN_EMAILS` env var; returns 404 (not 403) to hide admin existence
- **Teacher routes**: `require_teacher()` — checks `is_approved_teacher()`
- **Reviewer routes**: `is_reviewer()` — checks email against `REVIEWER_EMAILS` env var
- **Resource ownership**: services filter by `user_id` — you can only access your own data

### Error Handling
- `NotFoundError` from services → 404
- Usage limits → `UsageLimitExceededError` → 429
- Unhandled exceptions → 500 with generic message (production) or detail (development)

---

## Notable Endpoints

### `POST /projects/{project_id}/chats/{chat_id}/completions`
The main AI endpoint. Accepts:
- `messages`: conversation history
- `tools`: which AI tools to enable (checkboxes in UI)
- `web_search`: boolean toggle
- `files`: base64 file attachments

Returns SSE stream of chat chunks, tool calls, and source citations.

### `POST /admin/users/{user_id}/ban`
Suspends a student account:
- `days: int | None` — null/0 = permanent
- `reason: str` — shown to student on login attempt
- Uses `until_from_days()` from moderation module

### `DELETE /admin/users` (batch)
Bulk account deletion with:
- `before: datetime` — delete accounts created before this date
- `never_onboarded: bool` — only accounts that never completed onboarding
- Returns `DeletionReportDto` with count and details

### `POST /sessions` (admin)
Schedules a weekly class session:
- Validates meeting link against allowed hosts
- Assigns teacher
- Sets subject, grade, time, duration

---

## API Documentation
- Scalar API docs at `/docs` (conditional on `API_DOCS` setting)
- OpenAPI schema auto-generated from Pydantic models and FastAPI type hints
- All endpoints versioned under `/api/v1/`

---

## Key Design Decisions

1. **Project-scoped resources** — all student content lives under `/projects/{project_id}`, enabling future multi-workspace support
2. **Dual generation modes** — sync for background jobs, stream for real-time UI
3. **404 for unauthorized admin** — security through obscurity for admin panel discovery
4. **Base64 chat attachments** — avoids multipart complexity in SSE streams
5. **Batch operations** — practice records support batch creation for quiz/flashcard attempts
6. **Usage checking at router level** — rate limits enforced before hitting AI layer
