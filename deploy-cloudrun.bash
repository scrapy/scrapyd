#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

# Cloud Run Gen2 Deployment Script for Scrapyd
# Enhanced version with improved error handling, validation, and rollback capabilities

SCRIPT_VERSION="2.0.0"
CONFIG_FILE="${1:-cloudrun-config.yaml}"

# Colors for output
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $*" >&2
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $*" >&2
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*" >&2
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $*" >&2
}

# Error handling
cleanup() {
    local exit_code=$?
    if [[ $exit_code -ne 0 ]]; then
        log_error "Deployment failed with exit code $exit_code"
        if [[ "${ROLLBACK_ON_FAILURE:-true}" == "true" && -n "${PREVIOUS_REVISION:-}" ]]; then
            log_warn "Attempting rollback to previous revision: $PREVIOUS_REVISION"
            rollback_deployment
        fi
    fi
    exit $exit_code
}

trap cleanup EXIT

# Dependency checks
check_dependencies() {
    local missing_deps=()

    for cmd in gcloud docker awk; do
        if ! command -v "$cmd" >/dev/null 2>&1; then
            missing_deps+=("$cmd")
        fi
    done

    if [[ ${#missing_deps[@]} -gt 0 ]]; then
        log_error "Missing required dependencies: ${missing_deps[*]}"
        log_error "Please install the missing tools and try again"
        exit 1
    fi

    # Check gcloud authentication
    if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
        log_error "No active gcloud authentication found"
        log_error "Please run: gcloud auth login"
        exit 1
    fi

    log_info "All dependencies verified"
}

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
    log_error "Missing required key '$name' in $CONFIG_FILE"
    exit 1
  fi

  # Validate non-empty values
  if [[ -z "$val" ]]; then
    log_error "Required key '$name' cannot be empty in $CONFIG_FILE"
    exit 1
  fi

  echo "$val"
}

optional_val() {
  local name="$1"
  yget "$name" 2>/dev/null || true
}

# Configuration validation
validate_config() {
    log_info "Validating configuration file: $CONFIG_FILE"

    if [[ ! -f "$CONFIG_FILE" ]]; then
        log_error "Configuration file not found: $CONFIG_FILE"
        log_error "Please create a configuration file or specify a different path"
        exit 1
    fi

    # Validate required fields exist and have reasonable values
    local project_id="$(require_val project_id)"
    local region="$(require_val region)"
    local cpu="$(require_val cpu)"
    local memory="$(require_val memory)"
    local timeout="$(require_val timeout)"

    # Validate project ID format
    if [[ ! "$project_id" =~ ^[a-z][a-z0-9-]*[a-z0-9]$ ]]; then
        log_error "Invalid project_id format: $project_id"
        log_error "Project ID must start with a letter, contain only lowercase letters, numbers, and hyphens"
        exit 1
    fi

    # Validate region
    if [[ ! "$region" =~ ^[a-z0-9-]+$ ]]; then
        log_error "Invalid region format: $region"
        exit 1
    fi

    # Validate CPU (must be numeric or specific values)
    if [[ ! "$cpu" =~ ^[0-9]+(\.[0-9]+)?$ ]] && [[ ! "$cpu" =~ ^(1|2|4|6|8)$ ]]; then
        log_error "Invalid CPU value: $cpu. Must be 1, 2, 4, 6, 8 or decimal (e.g., 0.5, 1.5)"
        exit 1
    fi

    # Validate memory format
    if [[ ! "$memory" =~ ^[0-9]+[GM]i$ ]]; then
        log_error "Invalid memory format: $memory. Must be like 512Mi, 1Gi, 2Gi, etc."
        exit 1
    fi

    # Validate timeout (must be numeric with 's' suffix)
    if [[ ! "$timeout" =~ ^[0-9]+s$ ]]; then
        log_error "Invalid timeout format: $timeout. Must be like 300s, 900s, etc."
        exit 1
    fi

    log_success "Configuration validation passed"
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

# Rollback functionality
get_current_revision() {
    local service="$1"
    local region="$2"

    gcloud run revisions list \
        --service="$service" \
        --region="$region" \
        --filter="status.conditions.type:Ready AND status.conditions.status:True" \
        --format="value(metadata.name)" \
        --limit=1 2>/dev/null || echo ""
}

rollback_deployment() {
    if [[ -z "${PREVIOUS_REVISION:-}" ]]; then
        log_warn "No previous revision available for rollback"
        return 1
    fi

    log_warn "Rolling back to revision: $PREVIOUS_REVISION"

    if gcloud run services update-traffic "$SERVICE" \
        --region="$REGION" \
        --to-revisions="$PREVIOUS_REVISION=100" \
        --quiet; then
        log_success "Rollback completed successfully"
        return 0
    else
        log_error "Rollback failed"
        return 1
    fi
}

# Health check function
health_check() {
    local url="$1"
    local max_attempts="${2:-10}"
    local wait_time="${3:-30}"

    log_info "Performing health check on: $url"

    for ((i=1; i<=max_attempts; i++)); do
        log_info "Health check attempt $i/$max_attempts"

        if curl -f -s -m 10 "$url/daemonstatus.json" >/dev/null 2>&1; then
            log_success "Health check passed"
            return 0
        elif curl -f -s -m 10 "$url" >/dev/null 2>&1; then
            log_success "Basic connectivity check passed"
            return 0
        fi

        if [[ $i -lt $max_attempts ]]; then
            log_info "Waiting ${wait_time}s before next attempt..."
            sleep "$wait_time"
        fi
    done

    log_error "Health check failed after $max_attempts attempts"
    return 1
}

# Enhanced deployment verification
verify_deployment() {
    local service="$1"
    local region="$2"
    local expected_image="$3"

    log_info "Verifying deployment..."

    # Get service URL
    local url
    if ! url="$(gcloud run services describe "$service" --region "$region" --format='value(status.url)' 2>/dev/null)"; then
        log_error "Failed to get service URL"
        return 1
    fi

    if [[ -z "$url" ]]; then
        log_error "Service URL is empty"
        return 1
    fi

    # Verify the image is deployed
    local current_image
    current_image="$(gcloud run services describe "$service" --region "$region" --format='value(spec.template.spec.template.spec.containers[0].image)' 2>/dev/null)"

    if [[ "$current_image" != "$expected_image" ]]; then
        log_error "Deployed image mismatch. Expected: $expected_image, Got: $current_image"
        return 1
    fi

    # Perform health check
    if ! health_check "$url"; then
        log_error "Health check failed"
        return 1
    fi

    log_success "Deployment verification completed successfully"
    return 0
}

# Initialize
log_info "Cloud Run Gen2 Deployment Script v$SCRIPT_VERSION"

# Check dependencies
check_dependencies

# Validate configuration
validate_config

gcloud auth application-default set-quota-project ${PROJECT_ID}

# Get current revision for potential rollback
PREVIOUS_REVISION="$(get_current_revision "$SERVICE" "$REGION")"
if [[ -n "$PREVIOUS_REVISION" ]]; then
    log_info "Current revision for rollback: $PREVIOUS_REVISION"
else
    log_info "No previous revision found (first deployment)"
fi

# --- gcloud non-interactive ---
gcloud config set disable_prompts true >/dev/null

log_info "Setting project: ${PROJECT_ID}"
if ! gcloud config set project "${PROJECT_ID}" >/dev/null; then
    log_error "Failed to set project: ${PROJECT_ID}"
    exit 1
fi

log_info "Enabling required APIs (must have permissions; run once as Owner/Editor)"
if ! gcloud services enable \
  artifactregistry.googleapis.com \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  --project "${PROJECT_ID}" >/dev/null 2>&1; then
    log_error "Failed to enable required APIs"
    log_error "Please ensure you have the necessary permissions (Owner/Editor role)"
    exit 1
fi

# --- create Artifact Registry repo if missing ---
if ! gcloud artifacts repositories describe "${REPO}" --location="${REGION}" >/dev/null 2>&1; then
  log_info "Creating Artifact Registry repository: ${REPO} in ${REGION}"
  if ! gcloud artifacts repositories create "${REPO}" \
    --repository-format=docker \
    --location="${REGION}" \
    --description="Containers for ${PROJECT_ID}" >/dev/null; then
    log_error "Failed to create Artifact Registry repository"
    exit 1
  fi
  log_success "Artifact Registry repository created successfully"
else
  log_info "Artifact Registry repository already exists: ${REPO}"
fi

log_info "Configuring Docker auth for Artifact Registry"
if ! gcloud auth configure-docker "${REGION}-docker.pkg.dev" --quiet >/dev/null; then
    log_error "Failed to configure Docker authentication"
    exit 1
fi

# --- build & push ---
log_info "Building image: ${IMAGE}"
log_info "Dockerfile: ${DOCKERFILE_PATH}, Context: ${CONTEXT_DIR}"

if ! docker build -f "${DOCKERFILE_PATH}" -t "${IMAGE}" "${CONTEXT_DIR}"; then
    log_error "Docker build failed"
    exit 1
fi

log_success "Image built successfully"

log_info "Pushing image: ${IMAGE}"
if ! docker push "${IMAGE}"; then
    log_error "Docker push failed"
    exit 1
fi

log_success "Image pushed successfully"

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

log_info "Deploying Cloud Run service: ${SERVICE}"
log_info "Deployment configuration:"
log_info "  - Image: ${IMAGE}"
log_info "  - CPU: ${CPU}"
log_info "  - Memory: ${MEMORY}"
log_info "  - Concurrency: ${CONCURRENCY}"
log_info "  - Min instances: ${MIN_INSTANCES}"
log_info "  - Max instances: ${MAX_INSTANCES}"
log_info "  - Timeout: ${TIMEOUT}"
log_info "  - Execution environment: ${EXEC_ENV}"

if ! gcloud run deploy "${SERVICE}" "${DEPLOY_ARGS[@]}"; then
    log_error "Cloud Run deployment failed"
    exit 1
fi

log_success "Cloud Run service deployed successfully"

# --- verification and health check ---
if ! verify_deployment "${SERVICE}" "${REGION}" "${IMAGE}"; then
    log_error "Deployment verification failed"
    exit 1
fi

# --- output URL ---
URL="$(gcloud run services describe "${SERVICE}" --region "${REGION}" --format='value(status.url)')"
LATEST_REVISION="$(gcloud run revisions list --service="${SERVICE}" --region="${REGION}" --format='value(metadata.name)' --limit=1)"

log_success "=== DEPLOYMENT COMPLETED SUCCESSFULLY ==="
log_success "Service: ${SERVICE}"
log_success "URL: ${URL}"
log_success "Image: ${IMAGE}"
log_success "Region: ${REGION}"
log_success "Latest revision: ${LATEST_REVISION}"

if [[ -n "${PREVIOUS_REVISION:-}" ]]; then
    log_info "Previous revision (for rollback): ${PREVIOUS_REVISION}"
    log_info "To rollback, run:"
    log_info "  gcloud run services update-traffic ${SERVICE} --region=${REGION} --to-revisions=${PREVIOUS_REVISION}=100"
fi

log_info "To view logs, run:"
log_info "  gcloud run services logs read ${SERVICE} --region=${REGION}"

log_info "To view service details, run:"
log_info "  gcloud run services describe ${SERVICE} --region=${REGION}"
