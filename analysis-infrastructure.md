# Infrastructure & Deployment Analysis — NISAAB

## Overview

NISAAB runs entirely on **Google Cloud Platform** in the `asia-south1` (Mumbai) region, chosen for lowest latency to Pakistani students. The deployment is automated via a single `deploy.sh` script that handles everything from image building to database migration.

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                   Firebase Hosting                    │
│              (Static SPA — edu-web build)             │
└────────────────────────┬────────────────────────────┘
                         │ /api/* proxy
┌────────────────────────▼────────────────────────────┐
│                    Cloud Run — API                    │
│              (edu-api container, port 8080)           │
│              Scales 0→N, 512MB / 1 vCPU              │
└────────┬──────────────────────────┬─────────────────┘
         │                          │
┌────────▼────────┐    ┌───────────▼──────────────────┐
│   Cloud SQL      │    │    Vertex AI (Gemini)         │
│   PostgreSQL     │    │    LLM inference              │
│   + pgvector     │    │    Embeddings (3072-dim)      │
└─────────────────┘    └──────────────────────────────┘
         │
┌────────▼────────┐    ┌──────────────────────────────┐
│   Cloud Run —    │    │    Cloud Storage (GCS)        │
│   Worker         │    │    Document uploads           │
│   (edu-worker)   │    │    Generated figures          │
└─────────────────┘    └──────────────────────────────┘
         │
┌────────▼────────┐
│  Cloud Scheduler │
│  (drain trigger) │
└─────────────────┘
```

---

## Services

### Cloud Run — API (`edu-api`)
- **Container**: Python 3.12 + FastAPI + Uvicorn
- **Scaling**: 0 to N instances (scales to zero when idle)
- **Resources**: 512MB RAM, 1 vCPU (configurable)
- **Port**: 8080 (Cloud Run default)
- **Connection**: Cloud SQL via Unix socket connector
- **Auth**: Firebase ID tokens verified server-side

### Cloud Run — Worker (`edu-worker`)
- **Container**: Python 3.12 + polling loop
- **Mode**: Drain-on-schedule (Cloud Scheduler POSTs `/drain`)
- **Purpose**: Document processing (OCR, embedding), content bank generation
- **Scaling**: 0-1 instances (single worker, no concurrency issues)
- **Drain deadline**: 25 minutes (fits Cloud Run's 30-min max)

### Cloud SQL (PostgreSQL)
- **Engine**: PostgreSQL with `pgvector` extension
- **Location**: `asia-south1`
- **Use**: All application data + vector embeddings (3072-dim) + job queue
- **Migrations**: 50 Alembic migrations, run via `deploy.sh migrate`
- **Connection**: Private IP via Cloud SQL Auth Proxy / Unix socket

### Cloud Storage (GCS)
- **Bucket**: Document uploads, generated figures (matplotlib output)
- **Access**: Service account with signed URLs for student downloads
- **Fallback**: Supabase storage supported as alternative backend

### Vertex AI
- **Models**: Gemini family (gemini-3.5-flash default, fallback chain)
- **Features**: Chat completions, embeddings, code execution, file processing
- **Region**: Same region as Cloud Run for latency
- **Embeddings**: 3072-dimensional vectors via `:predict` API

### Firebase / Identity Platform
- **Authentication**: Email/password + Google sign-in
- **Hosting**: Static SPA serving with CDN
- **Rewrites**: All routes → `index.html` (SPA mode)

### Cloud Scheduler
- **Job**: Periodic POST to worker's `/drain` endpoint
- **Purpose**: Triggers job processing without keeping worker always running
- **Schedule**: Configurable interval

### Cloud Build
- **`cloudbuild-backend.yaml`**: Parallel Docker builds for API + Worker images
- **`cloudbuild-web.yaml`**: Frontend build and deploy to Firebase Hosting
- **Timeout**: 1800s (30 minutes)
- **Registry**: Artifact Registry for container images

---

## Deployment Script (`deploy.sh`)

A comprehensive Bash script with subcommands:

| Command | Purpose |
|---------|---------|
| `setup` | First-time GCP project setup (enable APIs, create resources) |
| `deploy` | Build + push images + deploy Cloud Run services |
| `web` | Build + deploy frontend to Firebase Hosting |
| `migrate` | Run Alembic migrations against Cloud SQL |
| `seed` | Seed FBISE curriculum data (subjects, domains, SLOs) |
| `content` | Generate content bank (pre-made quizzes, flashcards) |
| `e2e` | Run end-to-end tests against deployed instance |
| `script` | Run arbitrary Python script in Cloud Run context |

### Windows Compatibility
- `gcloud-win/` wrapper directory for Git Bash on Windows
- Handles path translation between Windows and Unix-style paths
- `deploy.env` for environment-specific configuration

---

## Environment Configuration

### API Environment Variables
| Variable | Purpose |
|----------|---------|
| `DATABASE_URL` | PostgreSQL connection string |
| `LLM_PROVIDER` | AI provider (`vertex` / `gemini` / `azure` / `openai`) |
| `LLM_CHAT_MODEL` | Default model (e.g. `gemini-3.5-flash`) |
| `LLM_TUTOR_MODEL` | Chatbot model override |
| `LLM_GENERATION_MODEL` | Content generation model override |
| `LLM_MARKING_MODEL` | Answer marking model override |
| `LLM_OCR_MODEL` | Document OCR model override |
| `LLM_FALLBACK_MODELS` | Comma-separated fallback chain |
| `FIREBASE_PROJECT_ID` | For auth token verification |
| `STORAGE_BACKEND` | `gcs` or `supabase` |
| `GCS_BUCKET` | Cloud Storage bucket name |
| `ADMIN_EMAILS` | Comma-separated admin email addresses |
| `REVIEWER_EMAILS` | Comma-separated content reviewer emails |
| `API_DOCS` | Enable/disable Scalar API documentation |

### Usage Limits (configurable)
| Resource | Default Limit |
|----------|--------------|
| Chat messages | 100/day |
| Quiz generations | 30/day |
| Flashcard generations | 20/day |
| Document uploads | 10/day |
| Community posts | 40/day |

---

## Azure (Legacy)

The `deploy/azure/` directory contains an earlier Azure deployment configuration:
- Azure Container Apps
- Azure OpenAI (GPT-4o)
- Azure Cosmos DB / Supabase
- **Status**: Superseded by GCP deployment, kept for reference

---

## Monitoring & Observability

- **Cloud Run metrics**: Request count, latency, instance count (built-in)
- **Cloud SQL metrics**: Connections, queries, storage (built-in)
- **Structured logging**: Python `logging` → Cloud Logging (automatic on Cloud Run)
- **Error tracking**: Exception handlers in FastAPI catch and log unhandled errors
- **No dedicated APM**: Relies on GCP's built-in monitoring

---

## Security

1. **Private Cloud SQL** — no public IP, accessed via Cloud SQL connector
2. **Service accounts** — least-privilege IAM for each service
3. **Firebase Auth** — tokens verified server-side on every request
4. **CORS**: Currently `allow_origins=["*"]` (should be tightened for production)
5. **Secrets**: Environment variables via Cloud Run secret references
6. **No admin in database** — admin status from env var, requires redeploy to change

---

## Key Design Decisions

1. **Single region (asia-south1)** — optimised for Pakistan, no multi-region complexity
2. **Scale-to-zero** — Cloud Run scales API and worker to zero when idle, minimising cost for an education platform
3. **No external message broker** — PostgreSQL `jobs` table serves as job queue, avoiding Pub/Sub complexity
4. **No separate vector database** — pgvector in the same PostgreSQL instance; at FBISE scale (9 subjects, ~1000 SLOs) a dedicated vector DB adds cost for no gain
5. **Worker drain model** — Cloud Scheduler triggers batch processing instead of always-on polling, saving compute costs
6. **Single deploy script** — one entry point for all deployment operations, reducing operational complexity
7. **Firebase Hosting CDN** — global edge caching for the static SPA, even though the API is single-region
