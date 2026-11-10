#!/usr/bin/env bash
# Phase 14 — deploy Outreach Copilot to Google Cloud (free-tier sizing). Run ONE step at a time:
#
#   export PROJECT=<your-project-id> REGION=asia-south1
#   ./deploy/gcp.sh apis        # select project, enable APIs
#   ./deploy/gcp.sh firestore   # create the (default) Firestore database (Native mode)
#   ./deploy/gcp.sh secrets     # Groq / Tavily / Neon / dashboard password -> Secret Manager
#   ./deploy/gcp.sh iam         # least-privilege service accounts + build role
#   ./deploy/gcp.sh api         # build + deploy the PRIVATE FastAPI service
#   ./deploy/gcp.sh web         # build + deploy the dashboard (basic auth) and let it call the API
#   ./deploy/gcp.sh status      # URLs + quick checks (API must refuse unauthenticated calls)
#   ./deploy/gcp.sh cleanup     # delete old container images (stay inside 0.5 GB free storage)
#
# Secrets are read from backend/.env (or typed silently) and piped straight into Secret Manager.
# Nothing secret is printed, written to disk, or passed on the command line.
set -euo pipefail

: "${PROJECT:?export PROJECT=<your-gcp-project-id> first}"
REGION="${REGION:-asia-south1}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
API_SA="outreach-api-sa@${PROJECT}.iam.gserviceaccount.com"
WEB_SA="outreach-web-sa@${PROJECT}.iam.gserviceaccount.com"
DASHBOARD_USER="${DASHBOARD_USER:-demo}"

say() { printf '\n\033[1m▶ %s\033[0m\n' "$*"; }
gc() { gcloud --project "$PROJECT" --quiet "$@"; }

env_value() {  # value of KEY from backend/.env, quotes stripped (never echoed)
  local line
  line="$(grep -E "^$1=" "$ROOT/backend/.env" 2>/dev/null | tail -1 || true)"
  line="${line#*=}"; line="${line%\"}"; line="${line#\"}"; line="${line%\'}"; line="${line#\'}"
  printf %s "$line"
}

put_secret() {  # put_secret <name> <ENV_KEY or ''>
  local name="$1" key="$2" val=""
  [[ -n "$key" ]] && val="$(env_value "$key")"
  if [[ -z "$val" ]]; then
    read -rsp "Value for $name (input hidden): " val; echo
  else
    echo "Using $key from backend/.env for $name"
  fi
  [[ -n "$val" ]] || { echo "  ✗ empty value for $name"; exit 1; }
  if gc secrets describe "$name" >/dev/null 2>&1; then
    printf %s "$val" | gc secrets versions add "$name" --data-file=- >/dev/null
    echo "  ✓ $name: new version added"
  else
    printf %s "$val" | gc secrets create "$name" --replication-policy=automatic --data-file=- >/dev/null
    echo "  ✓ $name: created"
  fi
  unset val
}

case "${1:-}" in
  apis)
    say "Project $PROJECT, region $REGION"
    gcloud config set project "$PROJECT"
    gc services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com \
      secretmanager.googleapis.com firestore.googleapis.com iam.googleapis.com
    echo "  ✓ APIs enabled"
    ;;

  firestore)
    if gc firestore databases describe --database="(default)" >/dev/null 2>&1; then
      echo "  ✓ Firestore (default) database already exists"
    else
      gc firestore databases create --database="(default)" --location="$REGION" --type=firestore-native
      echo "  ✓ Firestore created in $REGION (only the (default) database gets the free quota)"
    fi
    ;;

  secrets)
    say "Storing secrets in Secret Manager"
    put_secret groq-api-key GROQ_API_KEY
    put_secret tavily-api-key TAVILY_API_KEY
    put_secret database-url DATABASE_URL
    put_secret dashboard-password ""   # choose a new password for the website login (user: $DASHBOARD_USER)
    ;;

  iam)
    say "Service accounts (least privilege)"
    for sa in outreach-api-sa outreach-web-sa; do
      gc iam service-accounts describe "$sa@${PROJECT}.iam.gserviceaccount.com" >/dev/null 2>&1 \
        || gc iam service-accounts create "$sa" --display-name "$sa"
    done
    gc projects add-iam-policy-binding "$PROJECT" --member="serviceAccount:$API_SA" \
      --role=roles/datastore.user --condition=None >/dev/null
    for s in groq-api-key tavily-api-key database-url; do
      gc secrets add-iam-policy-binding "$s" --member="serviceAccount:$API_SA" \
        --role=roles/secretmanager.secretAccessor >/dev/null
    done
    gc secrets add-iam-policy-binding dashboard-password --member="serviceAccount:$WEB_SA" \
      --role=roles/secretmanager.secretAccessor >/dev/null
    # Source deploys build as the Compute Engine default SA, which needs Cloud Run Builder (Cloud Run docs).
    NUM="$(gc projects describe "$PROJECT" --format='value(projectNumber)')"
    gc projects add-iam-policy-binding "$PROJECT" \
      --member="serviceAccount:${NUM}-compute@developer.gserviceaccount.com" \
      --role=roles/run.builder --condition=None >/dev/null
    echo "  ✓ IAM ready (role grants can take ~2 minutes to apply)"
    ;;

  api)
    say "Deploying PRIVATE API (outreach-api) — first build takes ~5 minutes"
    gc run deploy outreach-api --source "$ROOT/backend" --region "$REGION" \
      --service-account "$API_SA" --no-allow-unauthenticated \
      --no-cpu-throttling --min-instances 0 --max-instances 1 --cpu 1 --memory 512Mi --timeout 900 \
      --set-env-vars "APP_ENV=prod,STORAGE_BACKEND=firestore,CHECKPOINT_BACKEND=postgres,GCP_PROJECT=${PROJECT}" \
      --set-secrets "GROQ_API_KEY=groq-api-key:latest,TAVILY_API_KEY=tavily-api-key:latest,DATABASE_URL=database-url:latest"
    ;;

  web)
    API_URL="$(gc run services describe outreach-api --region "$REGION" --format='value(status.url)')"
    [[ -n "$API_URL" ]] || { echo "Deploy the API first: ./deploy/gcp.sh api"; exit 1; }
    say "Allowing the dashboard's service account to call the private API"
    gc run services add-iam-policy-binding outreach-api --region "$REGION" \
      --member="serviceAccount:$WEB_SA" --role=roles/run.invoker >/dev/null
    say "Deploying dashboard (outreach-web) — public URL, protected by basic auth"
    gc run deploy outreach-web --source "$ROOT/frontend" --region "$REGION" \
      --service-account "$WEB_SA" --allow-unauthenticated \
      --min-instances 0 --max-instances 1 --cpu 1 --memory 512Mi \
      --set-env-vars "BACKEND_URL=${API_URL},BACKEND_AUTH=google,DASHBOARD_USER=${DASHBOARD_USER}" \
      --set-secrets "DASHBOARD_PASSWORD=dashboard-password:latest"
    ;;

  status)
    API_URL="$(gc run services describe outreach-api --region "$REGION" --format='value(status.url)' 2>/dev/null || true)"
    WEB_URL="$(gc run services describe outreach-web --region "$REGION" --format='value(status.url)' 2>/dev/null || true)"
    echo "API: ${API_URL:-not deployed}"
    echo "Web: ${WEB_URL:-not deployed}   (login user: $DASHBOARD_USER)"
    [[ -n "$API_URL" ]] && echo "API without a token → HTTP $(curl -s -o /dev/null -w '%{http_code}' "$API_URL/health") (expected 403)"
    [[ -n "$WEB_URL" ]] && echo "Web without a password → HTTP $(curl -s -o /dev/null -w '%{http_code}' "$WEB_URL/") (expected 401)"
    ;;

  cleanup)
    REPO="${REGION}-docker.pkg.dev/${PROJECT}/cloud-run-source-deploy"
    for img in outreach-api outreach-web; do
      # Never delete an image a live revision runs on; of the rest, keep nothing older than the live one.
      live="$(gc run services describe "$img" --region "$REGION" \
        --format='value(spec.template.spec.containers[0].image)' 2>/dev/null | sed 's/.*@//')"
      [[ -n "$live" ]] || { echo "  skip $img (not deployed)"; continue; }
      gc artifacts docker images list "$REPO/$img" --format='value(version)' 2>/dev/null | while read -r digest; do
        [[ "$digest" == "$live" ]] && { echo "  kept $img@${digest:0:19} (live)"; continue; }
        gc artifacts docker images delete "$REPO/$img@$digest" --delete-tags >/dev/null && echo "  deleted $img@${digest:0:19}"
      done
    done
    echo "  ✓ cleanup done"
    ;;

  *)
    sed -n '2,15p' "$0"; exit 1 ;;
esac
