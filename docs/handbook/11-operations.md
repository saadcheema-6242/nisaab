# 11. Operations

Everything is Google Cloud, project `fbise-tutor-2026`, region
`asia-south1`. One script does all of it: `deploy/gcp/deploy.sh`. Every
step is safe to re-run.

## Configuration

`deploy/gcp/deploy.env`, copied from `deploy.example.env`, or whatever
`$DEPLOY_ENV` points at. Not in git.

## Commands

```bash
deploy/gcp/deploy.sh                    # setup + deploy, first time
deploy/gcp/deploy.sh setup              # infrastructure only
deploy/gcp/deploy.sh deploy             # build images, migrate, deploy api + worker
deploy/gcp/deploy.sh deploy --skip-build  # redeploy latest images (settings only)
deploy/gcp/deploy.sh web                # build the site, publish to Firebase Hosting
deploy/gcp/deploy.sh migrate            # migrations only
deploy/gcp/deploy.sh seed               # load the FBISE curriculum
deploy/gcp/deploy.sh content --subject PHY --grade 11 --domains B
deploy/gcp/deploy.sh e2e                # the end-to-end suite, in the cloud
deploy/gcp/deploy.sh script scripts/content/fix_latex.py
```

**A frontend-only change needs `web` and nothing else.** `deploy` and
`e2e` should not be run at the same time.

On Windows this runs in Git Bash. The script sets `MSYS_NO_PATHCONV`
because Git Bash otherwise rewrites `/app/...` and `/cloudsql/...`
arguments into Windows paths on the way to gcloud.

## Two things that lie to you

Both cost real time here. Neither is obvious.

**A Cloud Run job reporting success is not proof the work succeeded.**
Jobs retry, and the job can be reported "successfully completed" while a
container inside it exited 1. **Read the logs**, not the status.

**`gcloud builds submit` can exit 0 having built nothing.** It happened
once: exit code 0, no build created, the source tarball never reached
GCS, and the deploy then pushed the *previous* image. `deploy.sh` now
checks the registry for the expected tag before migrating, and stops if
it is not there.

The general lesson, worth keeping: verify the artefact, not the exit
code.

## Database

Cloud SQL for PostgreSQL with pgvector. Alembic, 50 migrations, head
`b8e4d21f6c39`.

```bash
deploy/gcp/deploy.sh migrate
```

`deploy` runs migrations itself, after the registry check and before the
services are updated.

## Making someone an administrator

Add their email to `ADMIN_EMAILS` in `deploy.env` and redeploy settings:

```bash
deploy/gcp/deploy.sh deploy --skip-build
```

There is no database column and no UI for it. Chapter 13 explains why,
and the cost: it needs a deploy, not a click.

`REVIEWER_EMAILS` works the same way.

## Making someone a teacher

Not an environment variable. They apply in the app, and an administrator
approves them from the **Teachers** tab. An administrator can also set
the role directly from the admin dashboard, which counts as the
approval.

## Environment

The ones that matter, from `src/edu-api/config.py`:

| Variable | What it does |
|---|---|
| `DATABASE_URL` | Cloud SQL |
| `FIREBASE_PROJECT_ID` | Token verification |
| `STORAGE_BACKEND`, `STORAGE_BUCKET` | Documents and media |
| `ADMIN_EMAILS` | Comma-separated administrators |
| `REVIEWER_EMAILS` | Comma-separated content reviewers |
| `LLM_CHAT_MODEL` and the per-task overrides | Chapter 5 |
| `LLM_FALLBACK_MODELS` | Tried when the first is unavailable |
| `MAX_*_PER_DAY` | The usage limits in chapter 8 |
| `API_DOCS` | Serve interactive API docs |

`SUPABASE_*` and `AZURE_OPENAI_*` are from earlier deployments and are
unused in production.

## Local development

```bash
python -m uv sync
python -m uv run uvicorn main:app --reload --port 8010   # from src/edu-api
cd src/edu-web && pnpm install && pnpm dev               # port 3000
```

The API runs on **8010**, not 8000. The offline checkers (chapter 12)
need no database and no key, and are the fastest way to know the rules
still hold.

## A runbook for the usual problems

**A deploy failed partway.** Re-run it. Every step is idempotent. If the
build is the step that failed, check the registry actually has the tag.

**The site looks stale after `web`.** Asset filenames are hashed, so this
is almost always a cached `index.html`. Hard-reload.

**Students report "Failed to load your subjects".** Usually an
unconfirmed email, or an account with no `student_profile`. Check
`/api/v1/teachers/me` for that user: `send_to` says where they should
have been sent.

**A teacher cannot be assigned to a class.** They are not approved.
`teacher_approved_at` is null. Teachers tab.

**Rate limits during a demo.** `LLM_FALLBACK_MODELS`, and
`deploy --skip-build` to apply it.

Next: [12. Testing](12-testing.md)
