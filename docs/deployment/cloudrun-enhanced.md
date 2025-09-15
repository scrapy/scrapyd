# Enhanced Google Cloud Run Gen2 Deployment

This document describes the enhanced Cloud Run deployment script for Scrapyd with improved error handling, validation, health checks, and rollback capabilities.

## Features

### ✅ Enhanced Error Handling
- Comprehensive dependency checks (gcloud, docker, authentication)
- Robust error handling for all gcloud operations
- Automatic cleanup on failure
- Clear error messages with actionable guidance

### ✅ Configuration Validation
- YAML configuration file validation
- Project ID, region, and resource format validation
- CPU, memory, and timeout value validation
- Required field existence checks

### ✅ Rollback Capabilities
- Automatic rollback on deployment failure (configurable)
- Previous revision tracking
- Manual rollback instructions in output
- Safe deployment with fallback options

### ✅ Health Checks & Verification
- Post-deployment health checks via `/daemonstatus.json`
- Configurable health check attempts and timeouts
- Image deployment verification
- Service URL accessibility testing

### ✅ Improved Logging
- Color-coded output (INFO, WARN, ERROR, SUCCESS)
- Structured logging with clear progress indication
- Deployment configuration summary
- Comprehensive success output with next steps

### ✅ Cloud Run Gen2 Optimizations
- Full Gen2 execution environment support
- Enhanced resource configuration options
- VPC connector and egress settings support
- Advanced scaling and networking options

## Usage

### Quick Start

1. **Configure your deployment:**
   ```bash
   cp cloudrun-config.yaml my-config.yaml
   # Edit my-config.yaml with your settings
   ```

2. **Deploy to Cloud Run:**
   ```bash
   ./deploy-cloudrun.bash my-config.yaml
   ```

### Configuration File

The script uses a YAML configuration file with the following structure:

```yaml
# Required Settings
project_id: "your-gcp-project-id"
region: "us-central1"
repo: "scrapyd-images"
service: "scrapyd"

# Resource Configuration
cpu: "2"                    # 1, 2, 4, 6, 8, or decimals like 0.5, 1.5
memory: "2Gi"              # 512Mi, 1Gi, 2Gi, 4Gi, 8Gi, etc.
concurrency: "100"         # Max concurrent requests per instance
timeout: "900s"            # Request timeout (max 3600s for Gen2)

# Scaling Configuration
min_instances: "0"         # Minimum instances (0 for scale-to-zero)
max_instances: "10"        # Maximum instances
execution_environment: "gen2"

# Network Configuration
ingress: "all"             # all, internal, internal-and-cloud-load-balancing
allow_unauthenticated: "true"

# Optional: VPC Configuration
vpc_connector: "projects/your-project/locations/us-central1/connectors/your-connector"
egress_settings: "all-traffic"

# Optional: Environment Variables
env_vars: "SCRAPYD_MAX_PROC=4,SCRAPYD_DEBUG=false"

# Optional: Build Configuration
dockerfile_path: "Dockerfile"
context_dir: "."
tag_strategy: "date"       # "date" or "git"

# Optional: Deployment Settings
rollback_on_failure: "true"
health_check_timeout: "300"
health_check_attempts: "10"
```

## Configuration Options

### Required Settings

- **project_id**: Your Google Cloud Project ID
- **region**: GCP region (e.g., us-central1, europe-west1)
- **repo**: Artifact Registry repository name
- **service**: Cloud Run service name
- **cpu**: CPU allocation (1, 2, 4, 6, 8, or decimals)
- **memory**: Memory allocation (512Mi, 1Gi, 2Gi, etc.)
- **concurrency**: Max concurrent requests per instance
- **timeout**: Request timeout (format: 300s, 900s, etc.)
- **min_instances**: Minimum instances (0 for scale-to-zero)
- **max_instances**: Maximum instances
- **execution_environment**: gen1 or gen2 (gen2 recommended)
- **ingress**: Traffic ingress (all, internal, internal-and-cloud-load-balancing)
- **allow_unauthenticated**: Allow unauthenticated requests

### Optional Settings

- **vpc_connector**: VPC connector for private networking
- **egress_settings**: VPC egress configuration
- **env_vars**: Environment variables (comma-separated key=value pairs)
- **dockerfile_path**: Path to Dockerfile (default: Dockerfile)
- **context_dir**: Build context directory (default: .)
- **tag_strategy**: Image tagging strategy (date or git)

### Enhanced Features

- **rollback_on_failure**: Auto-rollback on deployment failure
- **health_check_timeout**: Health check timeout in seconds
- **health_check_attempts**: Number of health check attempts

## Deployment Process

The enhanced script follows this improved process:

1. **Pre-flight Checks**
   - Validate dependencies (gcloud, docker, authentication)
   - Parse and validate configuration file
   - Check GCP permissions and project access

2. **Preparation**
   - Get current revision for potential rollback
   - Enable required GCP APIs
   - Create Artifact Registry repository if needed
   - Configure Docker authentication

3. **Build & Push**
   - Build Docker image with error handling
   - Push to Artifact Registry with verification
   - Tag images based on strategy (date/git)

4. **Deployment**
   - Deploy to Cloud Run Gen2 with full configuration
   - Apply resource limits, scaling, and networking settings
   - Set environment variables and VPC configuration

5. **Verification**
   - Verify deployment success
   - Perform health checks on service endpoints
   - Validate image deployment and accessibility

6. **Output & Rollback**
   - Provide comprehensive deployment information
   - Include rollback instructions if needed
   - Display management commands for ongoing operations

## Error Handling & Rollback

### Automatic Rollback

If `rollback_on_failure` is enabled (default), the script will automatically attempt to rollback to the previous revision if:
- Deployment fails
- Health checks fail
- Post-deployment verification fails

### Manual Rollback

To manually rollback to a previous revision:

```bash
gcloud run services update-traffic SERVICE_NAME \
  --region=REGION \
  --to-revisions=PREVIOUS_REVISION=100
```

### Troubleshooting

Common issues and solutions:

1. **Permission Errors**: Ensure you have Cloud Run Admin and Artifact Registry Admin roles
2. **API Not Enabled**: The script automatically enables required APIs
3. **Docker Build Fails**: Check Dockerfile and build context
4. **Health Check Fails**: Verify Scrapyd configuration and startup time

## Best Practices

### Resource Configuration

- **CPU**: Start with 1-2 CPUs, scale based on spider load
- **Memory**: Minimum 1Gi for Scrapyd, 2Gi+ for heavy workloads
- **Concurrency**: Set to 1-10 for Scrapyd (not highly concurrent)
- **Timeout**: Set to 900s+ for long-running spider jobs

### Scaling Configuration

- **Min Instances**: 0 for cost optimization, 1+ for consistent availability
- **Max Instances**: Based on expected concurrent spider load
- **Execution Environment**: Always use gen2 for better performance

### Security & Networking

- Use VPC connectors for private resource access
- Set `allow_unauthenticated: false` for production environments
- Configure ingress restrictions based on access requirements
- Use environment variables for sensitive configuration

### Monitoring & Maintenance

- Monitor Cloud Run metrics and logs
- Set up alerting for deployment failures
- Regularly update container images
- Test rollback procedures periodically

## Example Deployment

```bash
# 1. Create configuration
cat > production-config.yaml << EOF
project_id: "my-scrapyd-project"
region: "us-central1"
repo: "scrapyd-images"
service: "scrapyd-prod"
cpu: "2"
memory: "4Gi"
concurrency: "5"
timeout: "1800s"
min_instances: "1"
max_instances: "5"
execution_environment: "gen2"
ingress: "internal-and-cloud-load-balancing"
allow_unauthenticated: "false"
env_vars: "SCRAPYD_MAX_PROC=8,SCRAPYD_DEBUG=false"
rollback_on_failure: "true"
EOF

# 2. Deploy
./deploy-cloudrun.bash production-config.yaml

# 3. Verify deployment
curl https://scrapyd-prod-xxx-uc.a.run.app/daemonstatus.json
```

This enhanced deployment script provides enterprise-grade reliability and operational features for running Scrapyd on Google Cloud Run Gen2.