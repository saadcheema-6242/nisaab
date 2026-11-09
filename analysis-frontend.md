# Frontend Analysis — NISAAB

## Overview

The NISAAB frontend is a **React 19 SPA** built with Vite, TanStack Router (file-based routing), Effect atoms for state management, and Tailwind CSS v4. It provides the student learning experience, teacher dashboard, and admin panel in a single application deployed to Firebase Hosting.

---

## Technology Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| Framework | React | 19 |
| Bundler | Vite | 6.x |
| Router | TanStack Router | file-based |
| State | Effect Atoms (`@effect-atom/atom-react`) | — |
| Styling | Tailwind CSS | v4 |
| Auth | Firebase Auth (Google Identity Platform) | — |
| Math | KaTeX | — |
| Diagrams | XY Flow (React Flow) | — |
| Carousel | Embla Carousel | — |
| Animation | Motion (Framer Motion) | — |
| Code Highlighting | Shiki | — |
| PDF Export | jsPDF | — |
| Testing | Vitest | — |

---

## Route Structure (15 route files)

### Public Routes
- **Home / Marketing** — landing page, unauthenticated

### Auth Routes
- **`_config.tsx`** — auth configuration and guards
- **Onboarding** — grade/group selection flow for new students

### Dashboard Routes (authenticated, sidebar layout)
- **`dashboard-route.tsx`** — main dashboard with subject cards, recent activity
- **`chat-detail-route.tsx`** — AI tutor conversation view with streaming
- **`quiz-detail-route.tsx`** — interactive quiz taking with instant feedback
- **`quiz-edit-route.tsx`** — quiz editing (teacher/admin)
- **`flashcard-detail-route.tsx`** — flashcard study with flip animation
- **`flashcard-edit-route.tsx`** — flashcard editing
- **`note-detail-route.tsx`** — study note viewer
- **`mind-map-detail-route.tsx`** — zoomable mind map (XY Flow)
- **`paper-route.tsx`** — practice paper taking (MCQ + SRQ + ERQ sections)
- **`srq-route.tsx`** — short-response question with AI marking
- **`document-detail-route.tsx`** — uploaded document viewer/preview
- **`study-plan-route.tsx`** — personalised study plan view
- **`project-detail-route.tsx`** — workspace/project management

---

## Feature Modules (23 feature directories)

| Feature | Purpose |
|---------|---------|
| `admin` | Account management, suspensions, moderation queue |
| `auth` | Firebase Auth integration, sign-in/sign-up, token management |
| `chat` | AI tutor conversation UI, message streaming, tool call rendering, file attachments |
| `community` | Discussion posts, polls, voting, reporting, file uploads |
| `dashboard` | Subject cards, recent activity, quick actions |
| `document` | Document upload, preview, management |
| `flashcard` | Flashcard study UI, flip animation, self-rating (Knew it / Still learning) |
| `home` | Landing/marketing page |
| `marketing` | Public-facing pages |
| `mind-map` | Zoomable mind map using XY Flow (React Flow) |
| `note` | Study note viewer with markdown rendering |
| `onboarding` | Grade/group selection, teacher application |
| `paper` | Practice paper UI — MCQ bubbles, SRQ writing, ERQ sections, timer |
| `progress` | Mastery overview, trend graphs, activity calendar, cognitive breakdown |
| `project` | Workspace management |
| `quiz` | Interactive quiz UI — question navigation, instant feedback, score display |
| `review` | Teacher content review dashboard |
| `sessions` | Weekly class session schedule, join button with countdown |
| `settings` | User preferences |
| `srq` | Short-response question writing and AI marking display |
| `study-plan` | Personalised study plan display |
| `syllabus` | Curriculum browser, SLO list, domain tree |
| `teacher` | Teacher dashboard, application flow, approval status |

---

## State Management

### Effect Atoms
The app uses `@effect-atom/atom-react` (Effect ecosystem) instead of Zustand/Jotai:
- **`isAuthenticatedAtom`** — auth state derived from Firebase
- Atoms for each feature's client-side state
- Reactive updates through `useAtomValue` hook

### Server State
- TanStack Router loaders fetch data on navigation
- API calls via fetch with Firebase ID token in Authorization header
- Streaming responses (SSE) for AI generation

---

## UI Components

### Component Library
- Built on **shadcn/ui** patterns (Radix primitives + Tailwind)
- Custom sidebar (`AppSidebar`) with collapsible navigation
- Conditional sidebar: only shown on `/dashboard` routes

### Rich Content Rendering
- **KaTeX** — mathematical formula rendering (critical for Physics, Chemistry, Maths)
- **Shiki** — syntax-highlighted code blocks (for ICS/Computer Science)
- **Markdown** — study notes, AI responses
- **XY Flow** — interactive mind maps with zoom/pan
- **Embla Carousel** — flashcard swipe interface
- **Motion** — page transitions, card flips, loading states

### Practice Paper UI
- MCQ section with bubble-sheet style
- SRQ section with writing area
- ERQ section with extended response
- Timer display
- Section navigation
- Submit and mark flow

### Community UI
- Post creation with file attachments
- Poll creation and voting
- Report/flag system
- AI-moderated content warnings
- Media gallery

---

## Authentication Flow

1. User signs in via Firebase Auth (email/password or Google)
2. Firebase ID token stored client-side
3. Token sent as `Authorization: Bearer <token>` on every API call
4. Backend verifies token via Firebase Admin SDK
5. First login triggers onboarding (grade/group selection)
6. Teacher applicants see "awaiting approval" state

---

## Build & Deployment

- **Vite** bundles the SPA
- **Firebase Hosting** serves the built static files
- All routes rewrite to `index.html` (SPA routing)
- Cloud Build (`cloudbuild-web.yaml`) handles CI/CD
- Environment variables injected at build time

---

## Key Design Decisions

1. **Effect Atoms over Redux/Zustand** — lightweight, composable, integrates with Effect ecosystem
2. **TanStack Router** — file-based routing with type-safe loaders, better than React Router for data-heavy apps
3. **Tailwind v4** — utility-first CSS with no config file (CSS-based configuration)
4. **KaTeX over MathJax** — faster rendering for the heavy math content in FBISE curriculum
5. **XY Flow for mind maps** — production-grade node/edge graph library with zoom, pan, and interaction
6. **Conditional sidebar** — clean full-page layout for non-dashboard routes (marketing, onboarding)
7. **SSE streaming** — real-time AI response display without WebSocket complexity
8. **jsPDF** — client-side PDF export for practice papers and notes (no server round-trip)
