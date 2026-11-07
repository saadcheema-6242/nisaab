# 15. Infrastructure and Deployment

## 15.1 Resources

| Resource | Purpose |
|---|---|
| Firebase Hosting | Serves the built single-page application on `nisaab.muhammadsaadcheema.com` |
| Cloud Run: `edu-api` | The HTTP service, publicly reachable |
| Cloud Run: `edu-worker` | Background processing; private, called only by the scheduler |
| Cloud SQL: PostgreSQL 16 | Primary database with the pgvector extension |
| Cloud Storage | Uploaded documents and extracted text |
| Secret Manager | Database connection string and API keys |
| Identity Platform | Authentication |
| Cloud Scheduler | Wakes the worker every minute to empty the queue |
| Cloud Build | Builds container images from source |
| Artifact Registry | Stores the built images |

## 15.2 The deployment script

A single shell script performs the whole deployment. Its sub-commands are:

```bash
deploy/gcp/deploy.sh setup | deploy | migrate | seed | content | script | e2e
```

A full deployment runs these steps in order:

1. Build the backend image.
2. Run database migrations as a Cloud Run job.
3. Seed the curriculum.
4. Deploy the API.
5. Deploy the worker.
6. Configure the scheduler.
7. Build the web image against the deployed API's address.
8. Deploy the web service.
9. Authorise the sign-in domain.
10. Check the API's health endpoint.

Cloud Run jobs are defined for migration, seeding, content generation, the end-to-end test and ad-hoc scripts. Optional secrets are attached only when they exist, so a deployment succeeds whether or not every optional integration is set up.

## 15.3 Operating characteristics

- The worker scales to zero and is woken on a schedule. An always-on mode exists for demonstration days.
- The database is reachable only over a private Unix socket and has no public address.
- The curriculum seed is idempotent, so re-running it is safe.

## 15.4 Cost

NISAAB currently runs on the Google Cloud free-trial credit, which ends in December 2026. The figures below are estimates from the September build and are to be checked against real billing.

| Item | How it is billed | Estimate |
|---|---|---|
| Cloud SQL (smallest tier) | Fixed monthly | About $10 per month |
| Cloud Run (web and API) | Per use | Low; covered by the credit |
| Cloud Run (worker) | Scales to zero | About $1.60 per day when kept always on for demo days |
| Gemini on Vertex AI | Per token | Kept low by reusing the pre-generated bank |

Budget alerts were set at about $50, $150 and $250. A grant of PKR 15,000 (PKR 10,000 for AI usage and PKR 5,000 for hosting) has been requested from the college for the competition period.
