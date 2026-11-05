#!/usr/bin/env bash
# Deploy EduAgent entirely on Google Cloud:
#   Cloud Run (api, worker, web) + Vertex AI Gemini + Cloud SQL (Postgres + pgvector)
#   + Cloud Storage (documents) + Identity Platform (student logins).
# Every step is safe to re-run.
#
# Usage (Git Bash, Cloud Shell, macOS or Linux):
#   deploy/gcp/deploy.sh                 setup + deploy (first time, or everything)
#   deploy/gcp/deploy.sh setup           create/update infrastructure only
#   deploy/gcp/deploy.sh deploy          build images, migrate the database, deploy services
#   deploy/gcp/deploy.sh deploy --skip-build   redeploy the latest images (settings changes)
#   deploy/gcp/deploy.sh web             rebuild and deploy the web app only (front-end fixes)
#   deploy/gcp/deploy.sh migrate         run database migrations
#   deploy/gcp/deploy.sh seed            load the FBISE curriculum (scripts/seed/data)
#   deploy/gcp/deploy.sh content --subject PHY --grade 11 --domains B
#                                        pre-generate reviewable SLO content (explainers, MCQs, SRQs)
#   deploy/gcp/deploy.sh e2e             run the end-to-end check in the cloud
#   deploy/gcp/deploy.sh script scripts/content/fix_latex.py [args]
#                                        run a one-off script from the worker image
#
# Settings: deploy/gcp/deploy.env (copy deploy.example.env), or the file in $DEPLOY_ENV.
set -euo pipefail
# Git Bash on Windows rewrites arguments that look like Unix paths (/app/...,
# /cloudsql/...) when calling Windows programs; keep them as written.
export MSYS_NO_PATHCONV=1 MSYS2_ARG_CONV_EXCL="*"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
# Local paths handed to gcloud: Windows form on Git Bash (cygpath), unchanged elsewhere
native_path() { if command -v cygpath >/dev/null 2>&1; then cygpath -m "$1"; else printf '%s' "$1"; fi; }
BUILD_DIR="$(native_path "$SCRIPT_DIR")"
SOURCE_DIR="$(native_path "$REPO_ROOT")"
CONFIG="${DEPLOY_ENV:-$SCRIPT_DIR/deploy.env}"
COMMAND="${1:-all}"
SKIP_BUILD=false
[[ "${2:-}" == "--skip-build" ]] && SKIP_BUILD=true

if [[ ! -f "$CONFIG" ]]; then
  echo "Missing $CONFIG. Copy deploy/gcp/deploy.example.env to deploy/gcp/deploy.env and fill it in." >&2
  exit 1
fi
set -a
# shellcheck disable=SC1090
source "$CONFIG"
set +a
for var in PROJECT_ID REGION; do
  if [[ -z "${!var:-}" ]]; then
    echo "Set $var in $CONFIG" >&2
    exit 1
  fi
done

# On Git Bash, plain `gcloud` is a .cmd that breaks on the spaces and brackets
# in "Program Files (x86)". The wrapper beside this script runs the SDK's own
# Python instead, so use it automatically on Windows rather than relying on
# everyone remembering to set GCLOUD.
if [[ -z "${GCLOUD:-}" && "$(uname -s)" == *NT* && -f "$SCRIPT_DIR/gcloud-win" ]]; then
  GCLOUD="$SCRIPT_DIR/gcloud-win"
fi
GCLOUD="${GCLOUD:-gcloud}"
VERTEX_LOCATION="${VERTEX_LOCATION:-global}"
SCHEDULER_REGION="${SCHEDULER_REGION:-$REGION}"
SQL_INSTANCE="${SQL_INSTANCE:-edu-db}"
SQL_TIER="${SQL_TIER:-db-f1-micro}"
DB_NAME=eduagent
DB_USER=eduagent
BUCKET="${STORAGE_BUCKET:-$PROJECT_ID-documents}"
REPO=edu-agent
REGISTRY="$REGION-docker.pkg.dev/$PROJECT_ID/$REPO"
TAG="$(date +%Y%m%d-%H%M%S)"
SA_NAME=edu-agent-run
SA_EMAIL="$SA_NAME@$PROJECT_ID.iam.gserviceaccount.com"
API_SERVICE=edu-api
WORKER_SERVICE=edu-worker
WEB_SERVICE=edu-web
MIGRATE_JOB=edu-migrate
E2E_JOB=edu-e2e
SEED_JOB=edu-seed
CONTENT_JOB=edu-content
SCRIPT_JOB=edu-script
DRAIN_JOB=edu-worker-drain
API_KEY_NAME="EduAgent web"
IDP="https://identitytoolkit.googleapis.com"

step() { printf '\n==> %s\n' "$*"; }
gc() { "$GCLOUD" --project "$PROJECT_ID" "$@"; }
service_url() { gc run services describe "$1" --region "$REGION" --format 'value(status.url)'; }
sql_connection() { gc sql instances describe "$SQL_INSTANCE" --format 'value(connectionName)'; }

identity_api() { # method path [json-body]; fails (with the error body) on HTTP errors
  local method=$1 path=$2 body=${3:-}
  local args=(-sS --fail-with-body -X "$method" "$IDP/$path"
    -H "Authorization: Bearer $("$GCLOUD" auth print-access-token)"
    -H "X-Goog-User-Project: $PROJECT_ID"
    -H "Content-Type: application/json")
  [[ -n "$body" ]] && args+=(-d "$body")
  curl "${args[@]}"
}

# Optional secrets are attached only when they already exist, so a deploy works
# without them. Create one by hand, for example:
#   printf '%s' "$KEY" | gcloud secrets create edu-tavily-api-key #     --replication-policy=automatic --data-file=- --project <project>
optional_secrets() { # prints ",NAME=secret:latest" for each optional secret present
  local out=""
  if gc secrets describe edu-tavily-api-key >/dev/null 2>&1; then
    out+=",TAVILY_API_KEY=edu-tavily-api-key:latest"
  fi
  printf '%s' "$out"
}

put_secret() { # name value: create the secret, add a version only when the value changed
  local name=$1 value=$2
  if ! gc secrets describe "$name" >/dev/null 2>&1; then
    gc secrets create "$name" --replication-policy automatic >/dev/null
  fi
  if [[ "$(gc secrets versions access latest --secret "$name" 2>/dev/null || true)" != "$value" ]]; then
    printf '%s' "$value" | gc secrets versions add "$name" --data-file=- >/dev/null
    echo "   updated secret $name"
  fi
}

# Settings shared by the API, worker and jobs. "^|^" makes | the separator.
# Not a comma, because LLM_FALLBACK_MODELS contains them. Not an @ either,
# which it used to be: ADMIN_EMAILS and REVIEWER_EMAILS hold email
# addresses, so a@b.com split into two variables and gcloud rejected the
# second half as a malformed key. A pipe appears in no email, no model id
# and no number we pass.
common_env() {
  local env="LLM_PROVIDER=vertex|GOOGLE_CLOUD_PROJECT=$PROJECT_ID|VERTEX_LOCATION=$VERTEX_LOCATION"
  env="$env|STORAGE_BACKEND=gcs|STORAGE_BUCKET=$BUCKET|FIREBASE_PROJECT_ID=$PROJECT_ID"
  local var
  for var in LLM_TUTOR_MODEL LLM_GENERATION_MODEL LLM_MARKING_MODEL LLM_OCR_MODEL \
             LLM_FALLBACK_MODELS LLM_EMBEDDING_MODEL REVIEWER_EMAILS ADMIN_EMAILS \
             MAX_CHAT_MESSAGES_PER_DAY MAX_QUIZ_GENERATIONS_PER_DAY \
             MAX_FLASHCARD_GENERATIONS_PER_DAY MAX_DOCUMENT_UPLOADS_PER_DAY \
             IMAGE_MODEL IMAGE_LOCATION; do
    if [[ -n "${!var:-}" ]]; then
      env="$env|$var=${!var}"
    fi
  done
  printf '%s' "$env"
}

setup() {
  step "Enabling APIs"
  gc services enable \
    run.googleapis.com artifactregistry.googleapis.com cloudbuild.googleapis.com \
    secretmanager.googleapis.com aiplatform.googleapis.com cloudscheduler.googleapis.com \
    sqladmin.googleapis.com storage.googleapis.com iam.googleapis.com iamcredentials.googleapis.com \
    identitytoolkit.googleapis.com securetoken.googleapis.com apikeys.googleapis.com \

  step "Artifact Registry repository $REPO"
  if ! gc artifacts repositories describe "$REPO" --location "$REGION" >/dev/null 2>&1; then
    gc artifacts repositories create "$REPO" --repository-format docker --location "$REGION"
  fi

  step "Service account $SA_EMAIL"
  if ! gc iam service-accounts describe "$SA_EMAIL" >/dev/null 2>&1; then
    gc iam service-accounts create "$SA_NAME" --display-name "EduAgent Cloud Run"
  fi
  local role
  for role in roles/aiplatform.user roles/secretmanager.secretAccessor roles/cloudsql.client \
              roles/logging.logWriter roles/monitoring.metricWriter; do
    gc projects add-iam-policy-binding "$PROJECT_ID" \
      --member "serviceAccount:$SA_EMAIL" --role "$role" --condition None >/dev/null
  done
  # Lets the service account sign Cloud Storage URLs for document previews
  gc iam service-accounts add-iam-policy-binding "$SA_EMAIL" \
    --member "serviceAccount:$SA_EMAIL" --role roles/iam.serviceAccountTokenCreator >/dev/null

  step "Cloud SQL instance $SQL_INSTANCE (Postgres 16, $SQL_TIER)"
  if ! gc sql instances describe "$SQL_INSTANCE" >/dev/null 2>&1; then
    gc sql instances create "$SQL_INSTANCE" \
      --database-version POSTGRES_16 --edition ENTERPRISE --tier "$SQL_TIER" \
      --region "$REGION" --storage-type SSD --storage-size 10 --storage-auto-increase \
      --availability-type zonal --backup-start-time 20:00 \
      --database-flags max_connections=60 --deletion-protection
  fi
  until [[ "$(gc sql instances describe "$SQL_INSTANCE" --format 'value(state)')" == "RUNNABLE" ]]; do
    echo "   waiting for the instance to be ready..."
    sleep 20
  done
  if ! gc sql databases describe "$DB_NAME" --instance "$SQL_INSTANCE" >/dev/null 2>&1; then
    gc sql databases create "$DB_NAME" --instance "$SQL_INSTANCE"
  fi
  # The app's database user; its password only ever lives in Secret Manager
  if ! gc secrets describe edu-database-url >/dev/null 2>&1; then
    local password
    password="$(openssl rand -hex 24)"
    if gc sql users list --instance "$SQL_INSTANCE" --format 'value(name)' | grep -qx "$DB_USER"; then
      gc sql users set-password "$DB_USER" --instance "$SQL_INSTANCE" --password "$password" >/dev/null
    else
      gc sql users create "$DB_USER" --instance "$SQL_INSTANCE" --password "$password" >/dev/null
    fi
    put_secret edu-database-url \
      "postgresql+psycopg2://$DB_USER:$password@/$DB_NAME?host=/cloudsql/$(sql_connection)"
  fi

  step "Cloud Storage bucket gs://$BUCKET"
  if ! gc storage buckets describe "gs://$BUCKET" >/dev/null 2>&1; then
    gc storage buckets create "gs://$BUCKET" --location "$REGION" \
      --uniform-bucket-level-access --public-access-prevention
  fi
  gc storage buckets add-iam-policy-binding "gs://$BUCKET" \
    --member "serviceAccount:$SA_EMAIL" --role roles/storage.objectAdmin >/dev/null

  step "Identity Platform (student logins: email + password)"
  if ! identity_api GET "admin/v2/projects/$PROJECT_ID/config" 2>/dev/null | grep -q '"signIn"'; then
    identity_api POST "v2/projects/$PROJECT_ID/identityPlatform:initializeAuth" '{}' >/dev/null
  fi
  identity_api PATCH "admin/v2/projects/$PROJECT_ID/config?updateMask=signIn.email" \
    '{"signIn":{"email":{"enabled":true,"passwordRequired":true}}}' >/dev/null
  if [[ -z "$(gc services api-keys list --filter "displayName='$API_KEY_NAME'" --format 'value(name)')" ]]; then
    gc services api-keys create --display-name "$API_KEY_NAME" \
      --api-target service=identitytoolkit.googleapis.com \
      --api-target service=securetoken.googleapis.com >/dev/null
  fi
  echo "   email/password sign-in enabled"

  if [[ -n "${BILLING_ACCOUNT_ID:-}" ]]; then
    step "Budget alerts"
    gc services enable billingbudgets.googleapis.com
    local budget_name="EduAgent $PROJECT_ID"
    if "$GCLOUD" billing budgets list --billing-account "$BILLING_ACCOUNT_ID" \
        --format 'value(displayName)' | grep -qxF "$budget_name"; then
      echo "   budget already exists"
    else
      "$GCLOUD" billing budgets create --billing-account "$BILLING_ACCOUNT_ID" \
        --display-name "$budget_name" --budget-amount "${BUDGET_AMOUNT:-300}USD" \
        --filter-projects "projects/$PROJECT_ID" \
        --threshold-rule percent=0.17 --threshold-rule percent=0.5 --threshold-rule percent=0.83
    fi
  fi
}

firebase_api_key() {
  local key_name
  key_name="$(gc services api-keys list --filter "displayName='$API_KEY_NAME'" --format 'value(name)' | head -1)"
  gc services api-keys get-key-string "$key_name" --format 'value(keyString)'
}

deploy_job() { # name image command args...
  local name=$1 image=$2 command=$3
  shift 3
  local args
  args="$(IFS=,; echo "$*")"
  gc run jobs deploy "$name" --image "$image" --region "$REGION" \
    --service-account "$SA_EMAIL" --set-cloudsql-instances "$(sql_connection)" \
    --command "$command" "--args=$args" \
    --cpu 1 --memory 1Gi --max-retries 0 --task-timeout 3600 \
    --set-env-vars "^|^$(common_env)" --set-secrets "DATABASE_URL=edu-database-url:latest$(optional_secrets)" >/dev/null
}

migrate() {
  step "Database migrations"
  deploy_job "$MIGRATE_JOB" "$REGISTRY/edu-worker:${IMAGE_TAG:-latest}" alembic -c /app/alembic.ini upgrade head
  gc run jobs execute "$MIGRATE_JOB" --region "$REGION" --wait
}

seed() {
  step "FBISE curriculum (Cloud Run job $SEED_JOB)"
  deploy_job "$SEED_JOB" "$REGISTRY/edu-worker:${IMAGE_TAG:-latest}" python /app/scripts/seed/seed_curriculum.py
  gc run jobs execute "$SEED_JOB" --region "$REGION" --wait
}

# Front-end only: rebuild the web image against the API already running and
# redeploy it. Skips the backend build, the migrations and the seed, so a UI
# fix ships in a couple of minutes without touching the database.
web() {
  IMAGE_TAG="$TAG"
  $SKIP_BUILD && IMAGE_TAG=latest
  local api_url
  api_url="$(service_url "$API_SERVICE")"

  if ! $SKIP_BUILD; then
    step "Building web image (API $api_url)"
    gc builds submit "$SOURCE_DIR" --config "$BUILD_DIR/cloudbuild-web.yaml" \
      --substitutions "_REGISTRY=$REGISTRY,_TAG=$TAG,_VITE_SERVER_URL=$api_url,_VITE_FIREBASE_API_KEY=$(firebase_api_key),_VITE_FIREBASE_PROJECT_ID=$PROJECT_ID"
  fi

  step "Deploying $WEB_SERVICE"
  gc run deploy "$WEB_SERVICE" \
    --image "$REGISTRY/edu-web:$IMAGE_TAG" --region "$REGION" \
    --allow-unauthenticated --port 80 \
    --cpu 1 --memory 256Mi --min-instances 0 --max-instances 3
  echo "   $(service_url "$WEB_SERVICE")"
}

deploy() {
  IMAGE_TAG="$TAG"
  $SKIP_BUILD && IMAGE_TAG=latest
  local connection
  connection="$(sql_connection)"

  if ! $SKIP_BUILD; then
    step "Building API and worker images (Cloud Build)"
    gc builds submit "$SOURCE_DIR" --config "$BUILD_DIR/cloudbuild-backend.yaml" \
      --substitutions "_REGISTRY=$REGISTRY,_TAG=$TAG"
  fi

  migrate
  seed

  step "Deploying $API_SERVICE"
  gc run deploy "$API_SERVICE" \
    --image "$REGISTRY/edu-api:$IMAGE_TAG" --region "$REGION" \
    --service-account "$SA_EMAIL" --allow-unauthenticated \
    --add-cloudsql-instances "$connection" \
    --cpu 1 --memory 1Gi --cpu-boost --min-instances "${API_MIN_INSTANCES:-0}" --max-instances 2 \
    --timeout 3600 \
    --set-env-vars "^|^$(common_env)" --set-secrets "DATABASE_URL=edu-database-url:latest$(optional_secrets)"
  API_URL="$(service_url "$API_SERVICE")"

  step "Deploying $WORKER_SERVICE"
  local worker_poll worker_scaling
  if [[ "${WORKER_ALWAYS_ON:-false}" == "true" ]]; then
    worker_poll=true
    worker_scaling=(--min-instances 1 --max-instances 1 --no-cpu-throttling)
  else
    worker_poll=false
    worker_scaling=(--min-instances 0 --max-instances 1 --cpu-throttling)
  fi
  gc run deploy "$WORKER_SERVICE" \
    --image "$REGISTRY/edu-worker:$IMAGE_TAG" --region "$REGION" \
    --service-account "$SA_EMAIL" --no-allow-unauthenticated \
    --add-cloudsql-instances "$connection" \
    --cpu 1 --memory 1Gi --cpu-boost "${worker_scaling[@]}" --timeout 1800 \
    --set-env-vars "^|^$(common_env)|WORKER_POLL=$worker_poll|WORKER_CONCURRENCY=${WORKER_CONCURRENCY:-3}" \
    --set-secrets "DATABASE_URL=edu-database-url:latest$(optional_secrets)"
  local worker_url
  worker_url="$(service_url "$WORKER_SERVICE")"
  gc run services add-iam-policy-binding "$WORKER_SERVICE" --region "$REGION" \
    --member "serviceAccount:$SA_EMAIL" --role roles/run.invoker >/dev/null

  step "Cloud Scheduler job $DRAIN_JOB"
  if [[ "$worker_poll" == "false" ]]; then
    local verb=create
    if gc scheduler jobs describe "$DRAIN_JOB" --location "$SCHEDULER_REGION" >/dev/null 2>&1; then
      verb=update
    fi
    gc scheduler jobs "$verb" http "$DRAIN_JOB" --location "$SCHEDULER_REGION" \
      --schedule "* * * * *" --uri "$worker_url/drain" --http-method POST \
      --oidc-service-account-email "$SA_EMAIL" --oidc-token-audience "$worker_url" \
      --attempt-deadline 1800s >/dev/null
    gc scheduler jobs resume "$DRAIN_JOB" --location "$SCHEDULER_REGION" >/dev/null 2>&1 || true
    echo "   worker scales to zero; drained every minute"
  else
    gc scheduler jobs pause "$DRAIN_JOB" --location "$SCHEDULER_REGION" >/dev/null 2>&1 || true
    echo "   worker always on (polling); drain job paused"
  fi

  if ! $SKIP_BUILD; then
    step "Building web image (API $API_URL)"
    gc builds submit "$SOURCE_DIR" --config "$BUILD_DIR/cloudbuild-web.yaml" \
      --substitutions "_REGISTRY=$REGISTRY,_TAG=$TAG,_VITE_SERVER_URL=$API_URL,_VITE_FIREBASE_API_KEY=$(firebase_api_key),_VITE_FIREBASE_PROJECT_ID=$PROJECT_ID"
  fi

  step "Deploying $WEB_SERVICE"
  gc run deploy "$WEB_SERVICE" \
    --image "$REGISTRY/edu-web:$IMAGE_TAG" --region "$REGION" \
    --allow-unauthenticated --port 80 \
    --cpu 1 --memory 256Mi --min-instances 0 --max-instances 3
  local web_url
  web_url="$(service_url "$WEB_SERVICE")"

  step "Allowing sign-in from the web app's domain"
  # This PATCH replaces the whole list, so every domain sign-in must work
  # from has to be named here. A domain added by hand in the console would
  # be wiped by the next deploy and sign-in would start failing on it with
  # nothing to say why. Set WEB_DOMAIN to your own domain and it is kept.
  local domains="\"localhost\",\"$PROJECT_ID.firebaseapp.com\",\"$PROJECT_ID.web.app\",\"${web_url#https://}\""
  if [[ -n "${WEB_DOMAIN:-}" ]]; then
    domains="$domains,\"$WEB_DOMAIN\""
  fi
  identity_api PATCH "admin/v2/projects/$PROJECT_ID/config?updateMask=authorizedDomains" \
    "{\"authorizedDomains\":[$domains]}" >/dev/null

  step "Checking the API"
  curl -fsS "$API_URL/health" && echo

  printf '\nDeployed.\n  Web:    %s\n  API:    %s\n  Worker: %s (private)\n' "$web_url" "$API_URL" "$worker_url"
}

content() {
  step "SLO content bank (Cloud Run job $CONTENT_JOB)"
  deploy_job "$CONTENT_JOB" "$REGISTRY/edu-worker:latest" python /app/scripts/content/generate_bank.py "$@"
  gc run jobs execute "$CONTENT_JOB" --region "$REGION" --wait
}

run_script() { # path args...
  local path=$1
  shift
  step "Script $path (Cloud Run job $SCRIPT_JOB)"
  deploy_job "$SCRIPT_JOB" "$REGISTRY/edu-worker:latest" python "/app/$path" "$@"
  gc run jobs execute "$SCRIPT_JOB" --region "$REGION" --wait
}

e2e() {
  step "End-to-end check (Cloud Run job $E2E_JOB)"
  deploy_job "$E2E_JOB" "$REGISTRY/edu-worker:latest" python /app/scripts/e2e_ai_check.py
  gc run jobs execute "$E2E_JOB" --region "$REGION" --wait
}

"$GCLOUD" config set project "$PROJECT_ID" >/dev/null 2>&1 || true

case "$COMMAND" in
  all) setup; deploy ;;
  setup) setup ;;
  deploy) deploy ;;
  web) web ;;
  migrate) migrate ;;
  seed) seed ;;
  content) shift; content "$@" ;;
  script) shift; run_script "$@" ;;
  e2e) e2e ;;
  *) echo "Unknown command: $COMMAND (use setup, deploy, web, migrate, seed, content, script, e2e)" >&2; exit 1 ;;
esac
