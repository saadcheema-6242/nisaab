# Deploying EduAgent on Google Cloud

Everything runs in one Google Cloud project (currently `fbise-tutor-2026`, region `asia-south1`, Mumbai):

```text
Browser ─► Cloud Run: edu-web (static React app) ─► Identity Platform (student sign-in)
        └► Cloud Run: edu-api (FastAPI) ──► Vertex AI Gemini (chat, generation, embeddings)
                         │   └─► Cloud Storage (uploaded documents)
                         ▼
             Cloud SQL: Postgres 16 + pgvector (all data, incl. the jobs table)
                         ▲
Cloud Scheduler ─POST /drain every minute─► Cloud Run: edu-worker (private)
Cloud Run jobs: edu-migrate (database migrations), edu-e2e (end-to-end check)
```

| Resource | Name |
|---|---|
| Cloud SQL instance / database / user | `edu-db` / `eduagent` / `eduagent` (password only in Secret Manager `edu-database-url`) |
| Cloud Storage bucket | `PROJECT_ID-documents` (private; previews use short-lived signed URLs) |
| Identity Platform | email + password sign-in; browser API key "EduAgent web" (restricted to sign-in APIs) |
| Service account | `edu-agent-run` (Vertex AI, Cloud SQL client, secrets, bucket objects) |
| Budget | alerts at about $50, $150, $250 of `BUDGET_AMOUNT` on the billing account |

## Commands

```bash
deploy/gcp/deploy.sh                       # first time: setup + deploy
deploy/gcp/deploy.sh setup                 # create or update infrastructure
deploy/gcp/deploy.sh deploy                # build images, migrate the database, deploy services
deploy/gcp/deploy.sh web                   # rebuild and deploy the web app only (front-end changes)
deploy/gcp/deploy.sh deploy --skip-build   # redeploy the latest images after changing deploy.env
deploy/gcp/deploy.sh migrate               # database migrations only
deploy/gcp/deploy.sh e2e                   # end-to-end check (upload, search, chat, generation) in the cloud
```

Settings live in `deploy/gcp/deploy.env` (copy `deploy.example.env`; it holds no secrets). Needs the
[Google Cloud CLI](https://cloud.google.com/sdk/docs/install), signed in (`gcloud auth login`) as a project owner.
Works in Cloud Shell, macOS, Linux and Git Bash on Windows. On Windows `gcloud.cmd` fails on the spaces and
brackets in "Program Files (x86)", so use the wrapper kept next to this file:

```bash
GCLOUD=deploy/gcp/gcloud-win PYTHONUTF8=1 bash deploy/gcp/deploy.sh deploy
```

## Demo days

| Setting in `deploy.env` | Normal | Demo day |
|---|---|---|
| `WORKER_ALWAYS_ON` | `false`: worker scales to zero, jobs start within ~1 minute | `true`: jobs start instantly (~$1.60/day) |
| `API_MIN_INSTANCES` | `0`: first request after idle waits for a cold start | `1`: no cold start |

Apply with `deploy/gcp/deploy.sh deploy --skip-build`, and switch back after the demo.

Before a demo: run `deploy/gcp/deploy.sh e2e`, open the app once, and take an on-demand backup:
`gcloud sql backups create --instance edu-db`.

## Moving to another Google Cloud account

1. The new project's owner adds you in IAM (Owner). Never share passwords.
2. Export the data from the old project:
   `gcloud sql export sql edu-db gs://OLD-PROJECT-documents/backup.sql --database eduagent`
   and copy the bucket (`gcloud storage cp -r gs://OLD-PROJECT-documents gs://NEW-PROJECT-documents`).
3. Set `PROJECT_ID` (and `BILLING_ACCOUNT_ID`) in `deploy.env`, run `deploy/gcp/deploy.sh`,
   then import: `gcloud sql import sql edu-db gs://NEW-PROJECT-documents/backup.sql --database eduagent`.
4. Student logins live in Identity Platform per project; export/import them with the Firebase CLI
   (`firebase auth:export` / `auth:import`), or ask students to sign up again.

## Costs (estimates; check the Google Cloud pricing calculator)

- Cloud SQL `db-f1-micro` with 10 GB SSD: about $10–13/month.
- Cloud Run API and web, scaling to zero: a few dollars/month. Worker: pennies in drain mode; ~$1.60/day always on.
- Vertex AI Gemini: pay per token; pre-generating content plus demos is likely tens of dollars in total.
- Cloud Storage, Secret Manager, Scheduler, Identity Platform (email sign-in): cents at this scale.

## Troubleshooting

- **Logs**: `gcloud logging read 'resource.labels.service_name="edu-api"' --freshness 30m` (or the Cloud Run console).
- **Database connection limit**: `edu-db` allows 60 connections; the API is capped at 2 instances and uses small pools.
- **Vertex AI embeddings**: use the native `:predict` API (`VertexEmbeddings`); Vertex's OpenAI-compatible
  endpoint returns errors for embeddings.
- **Sign-in fails on a new domain**: `deploy.sh deploy` adds the web URL to Identity Platform's authorized domains.
