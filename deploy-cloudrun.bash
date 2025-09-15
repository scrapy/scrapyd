#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

CONFIG_FILE="${1:-cloudrun-config.yaml}"

# --- tiny YAML parser for flat key: value pairs ---
yget() {
  local key="$1"
  awk -F': *' -v k="$key" '
    $1 ~ "^[[:space:]]*"k"[[:space:]]*$" {print $2; found=1; exit}
    $1 == k {print $2; found=1; exit}
  END { if (!found) exit 1 }' "$CONFIG_FILE" | tr -d '"'\''[:space:]'
}

require_val() {
  local name="$1"
  local val
  if ! val="$(yget "$name")"; then
    echo "ERROR: Missing required key '$name' in $CONFIG_FILE" >&2
    exit 1
  fi
  echo "$val"
}

optional_val() {
  local name="$1"
  yget "$name" 2>/dev/null || true
}

# --- read config ---
PROJECT_ID="$(require_val project_id)"
REGION="$(require_val region)"
REPO="$(require_val repo)"
SERVICE="$(require_val service)"
CPU="$(require_val cpu)"
MEMORY="$(require_val memory)"
CONCURRENCY="$(require_val concurrency)"
TIMEOUT="$(require_val timeout)"
MIN_INSTANCES="$(require_val min_instances)"
MAX_INSTANCES="$(require_val max_instances)"
EXEC_ENV="$(require_val execution_environment)"
INGRESS="$(require_val ingress)"
ALLOW_UNAUTH="$(require_val allow_unauthenticated)"

VPC_CONNECTOR="$(optional_val vpc_connector)"
EGRESS_SETTINGS="$(optional_val egress_settings)"
ENV_VARS="$(optional_val env_vars)"
TAG_STRATEGY="$(optional_val tag_strategy)"
DOCKERFILE_PATH="$(optional_val dockerfile_path)"
CONTEXT_DIR="$(optional_val context_dir)"

: "${DOCKERFILE_PATH:=Dockerfile}"
: "${CONTEXT_DIR:=.}"
: "${TAG_STRATEGY:=date}"

# --- choose tag ---
if [[ "$TAG_STRATEGY" == "git" ]] && command -v git >/dev/null 2>&1; then
  TAG="$(git rev-parse --short=12 HEAD)"
else
  TAG="$(date +%Y%m%d-%H%M%S)"
fi

# --- image coordinates (Artifact Registry) ---
IMAGE_BASE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}/${SERVICE}"
IMAGE="${IMAGE_BASE}:${TAG}"

gcloud auth application-default set-quota-project ${PROJECT_ID}

# --- gcloud non-interactive ---
gcloud config set disable_prompts true >/dev/null

echo "› Setting project: ${PROJECT_ID}"
gcloud config set project "${PROJECT_ID}" >/dev/null

echo "› Enabling required APIs (must have permissions; run once as Owner/Editor)"
gcloud services enable \
  artifactregistry.googleapis.com \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  --project "${PROJECT_ID}" >/dev/null

# --- create Artifact Registry repo if missing ---
if ! gcloud artifacts repositories describe "${REPO}" --location="${REGION}" >/dev/null 2>&1; then
  echo "› Creating Artifact Registry repository: ${REPO} in ${REGION}"
  gcloud artifacts repositories create "${REPO}" \
    --repository-format=docker \
    --location="${REGION}" \
    --description="Containers for ${PROJECT_ID}" >/dev/null
fi

echo "› Configuring Docker auth for Artifact Registry"
gcloud auth configure-docker "${REGION}-docker.pkg.dev" --quiet >/dev/null

# --- build & push ---
echo "› Building image: ${IMAGE}"
docker build -f "${DOCKERFILE_PATH}" -t "${IMAGE}" "${CONTEXT_DIR}"

echo "› Pushing image: ${IMAGE}"
docker push "${IMAGE}"

# --- deploy to Cloud Run Gen2 ---
DEPLOY_ARGS=(
  "--image=${IMAGE}"
  "--region=${REGION}"
  "--platform=managed"
  "--execution-environment=${EXEC_ENV}"
  "--ingress=${INGRESS}"
  "--cpu=${CPU}"
  "--memory=${MEMORY}"
  "--concurrency=${CONCURRENCY}"
  "--timeout=${TIMEOUT}"
  "--min-instances=${MIN_INSTANCES}"
  "--max-instances=${MAX_INSTANCES}"
  "--allow-unauthenticated"
  # "--set-env-vars "SCRAPYD_MAX_PROC=4"
)

if [[ -n "${ENV_VARS}" ]]; then
  DEPLOY_ARGS+=( "--set-env-vars=${ENV_VARS}" )
fi
if [[ -n "${VPC_CONNECTOR}" ]]; then
  DEPLOY_ARGS+=( "--vpc-connector=${VPC_CONNECTOR}" )
fi
if [[ -n "${EGRESS_SETTINGS}" ]]; then
  DEPLOY_ARGS+=( "--vpc-egress=${EGRESS_SETTINGS}" )
fi
if [[ "${ALLOW_UNAUTH,,}" == "true" ]]; then
  DEPLOY_ARGS+=( "--allow-unauthenticated" )
fi

echo "› Deploying Cloud Run service: ${SERVICE}"
gcloud run deploy "${SERVICE}" "${DEPLOY_ARGS[@]}"

# --- output URL ---
URL="$(gcloud run services describe "${SERVICE}" --region "${REGION}" --format='value(status.url)')"
echo "✅ Deployed ${SERVICE}"
echo "   URL: ${URL}"
echo "   Image: ${IMAGE}"
