# 7 · Cloud and deployment

[← AI layer](06-ai.md) · [Contents](README.md) · [Next: Curriculum data →](08-curriculum-data.md)

Everything runs in **one** Google Cloud project: `fbise-tutor-2026`, region
`asia-south1` (Mumbai — the closest region to Pakistan).

---

## What is running

| Service | Kind | Role |
|---|---|---|
| `edu-web` | Cloud Run | nginx serving the built React app |
| `edu-api` | Cloud Run | FastAPI, public |
| `edu-worker` | Cloud Run | background jobs, **private** |
| `edu-db` | Cloud SQL | PostgreSQL 16 + pgvector, `db-f1-micro` |
| `fbise-tutor-2026-documents` | Cloud Storage | uploaded documents |
| Vertex AI | — | Gemini, location `global` for the widest model availability |
| Identity Platform | — | student logins |
| Secret Manager | — | database URL, API keys, OAuth credentials |
| Artifact Registry | — | container images |
| Cloud Scheduler | — | `edu-worker-drain`, wakes the worker when it scales to zero |
| Cloud Build | — | builds the three images |

### Live URLs

```
Web     https://edu-web-yvi5hrqfda-el.a.run.app
API     https://edu-api-yvi5hrqfda-el.a.run.app
Worker  https://edu-worker-yvi5hrqfda-el.a.run.app   (private)
```

### Service account

All three services run as `edu-agent-run@fbise-tutor-2026.iam.gserviceaccount.com`:

| Role | For |
|---|---|
| `roles/aiplatform.user` | Calling Gemini |
| `roles/secretmanager.secretAccessor` | Reading secrets |
| `roles/cloudsql.client` | Connecting to the database |
| `roles/logging.logWriter`, `roles/monitoring.metricWriter` | Telemetry |
| `roles/iam.serviceAccountTokenCreator` *(on itself)* | Signing Cloud Storage URLs for document previews |

---

## Deploying

One script, `deploy/gcp/deploy.sh`. **Every command is safe to re-run.**

| Command | Does |
|---|---|
| `setup` | Create or update infrastructure: APIs, registry, service account, Cloud SQL, bucket, Identity Platform |
| `deploy` | Build images → migrate → seed → deploy all three services |
| `deploy --skip-build` | Redeploy the current images, for a settings change only |
| `web` | Rebuild and deploy the web app only |
| `migrate` | Run database migrations |
| `seed` | Load the FBISE curriculum from `scripts/seed/data` |
| `content` | Pre-generate reviewable SLO content |
| `script <path>` | Run a one-off script in the worker image |
| `e2e` | Run the end-to-end check in the cloud |

The usual one:

```bash
bash deploy/gcp/deploy.sh deploy
```

Takes about six minutes: ~2 min for the API and worker images, ~4 min for the web image.

> **`script` does not rebuild anything.** It points a Cloud Run job at
> `edu-worker:latest` — whatever image was built last. A source change only reaches it
> after a `deploy`. This cost a wasted debugging cycle; it is written here so it costs
> nobody another.

### Running it on Windows

Git Bash is the supported shell. Plain `gcloud` there is a `.cmd` that breaks on the
spaces and brackets in `C:\Program Files (x86)\...`, so `deploy/gcp/gcloud-win` calls the
SDK's own bundled Python directly.

**The script finds that wrapper by itself** — no `GCLOUD=` prefix is needed:

```bash
if [[ -z "${GCLOUD:-}" && "$(uname -s)" == *NT* && -f "$SCRIPT_DIR/gcloud-win" ]]; then
  GCLOUD="$SCRIPT_DIR/gcloud-win"
fi
```

### Settings

`deploy/gcp/deploy.env`, git-ignored. **No secrets live there** — the database password
is generated and kept in Secret Manager. It holds the project, region, model names and
the cost controls below.

---

## Cost control

This is a student project with a real bill, so the knobs are deliberate.

| Setting | Values | Effect |
|---|---|---|
| `WORKER_ALWAYS_ON` | `true` / `false` | `true` keeps one worker polling (~**$1.60/day**). `false` scales to zero and Cloud Scheduler calls `POST /drain` every minute — pennies a month, but a job may wait up to a minute to start |
| `API_MIN_INSTANCES` | `1` / `0` | `1` keeps one API instance warm, so the first request of the day has no cold start. `0` scales to zero |
| `WORKER_CONCURRENCY` | `3` | How many jobs one worker instance takes at once |
| `SQL_TIER` | `db-f1-micro` | Smallest shared-core tier, about $10/month |

**Currently `WORKER_ALWAYS_ON=true` and `API_MIN_INSTANCES=1`** for the competition
period. Both should go back down afterwards.

Budget alerts are configured at roughly $50, $150 and $250.

### Stopping without deleting

Scaling the services to zero stops nearly all cost while keeping the URLs, the database
and every student's work. **Deleting** the Cloud Run services makes the links dead and
is not the same thing — that distinction caused real confusion once and is worth
keeping straight.

---

## Secrets

| Secret | Holds |
|---|---|
| `edu-database-url` | The Cloud SQL connection string |
| `edu-tavily-api-key` | Web search key (optional) |
| `edu-google-oauth-client-id` | Google Forms OAuth client |
| `edu-google-oauth-client-secret` | " |
| `edu-google-oauth-refresh-token` | " |

`optional_secrets()` in `deploy.sh` wires a secret in **only if it exists**, so the
stack deploys cleanly whether or not the optional features are configured. The three
Forms secrets are treated as one set, keyed on the refresh token.

---

## A Cloud Run authentication trap

Worth knowing before it costs someone a day.

On Cloud Run, Application Default Credentials come from the metadata server, which
returns a token carrying **the scopes the service was given** — normally
`cloud-platform`. Asking for different scopes is **silently ignored**:

```python
creds, _ = google.auth.default(scopes=SCOPES)   # scopes ignored on Cloud Run
```

`cloud-platform` does not cover Workspace APIs such as Forms and Drive. A call made
with that token is refused — and Google answers **500**, not 403, which makes it look
like a fault on their side.

The fix for scope problems is self-impersonation through the IAM Credentials API. But
in the Forms case the scopes turned out not to be the real blocker at all: see
[Operations](09-operations.md#google-forms).

---

[← AI layer](06-ai.md) · [Contents](README.md) · [Next: Curriculum data →](08-curriculum-data.md)
