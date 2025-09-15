# Deploying Scrapyd to Google Cloud

This guide covers deploying Scrapyd to Google Cloud Platform using Cloud Run Gen2 for serverless scaling.

## Prerequisites

- Google Cloud account with billing enabled
- `gcloud` CLI installed and configured
- Docker installed locally
- Git repository with Scrapyd code

## Quick Start

### 1. Setup Environment

```bash
# Set project variables
export PROJECT_ID="your-project-id"
export REGION="us-central1"
export SERVICE_NAME="scrapyd-service"

# Login and set project
gcloud auth login
gcloud config set project $PROJECT_ID
```

### 2. Enable Required APIs

```bash
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  storage.googleapis.com \
  secretmanager.googleapis.com \
  vpcaccess.googleapis.com
```

### 3. Deploy with Script

```bash
# Clone and deploy
git clone https://github.com/scrapy/scrapyd.git
cd scrapyd
git checkout feature/google-cloud-run-deployment

# Run deployment script
./scripts/deploy-cloudrun.sh
```

## Manual Deployment

### 1. Build Container Image

Create optimized Dockerfile for Cloud Run:

```dockerfile
# Dockerfile
FROM python:3.12-slim as builder
WORKDIR /build
COPY pyproject.toml README.rst MANIFEST.in ./
COPY scrapyd/ ./scrapyd/
RUN pip install --no-cache-dir build && python -m build --wheel

FROM python:3.12-slim
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl ca-certificates && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

RUN groupadd -r scrapyd && useradd -r -g scrapyd scrapyd

WORKDIR /app
COPY --from=builder /build/dist/*.whl /tmp/
RUN pip install --no-cache-dir /tmp/*.whl && rm /tmp/*.whl

RUN mkdir -p /mnt/gcs/{eggs,logs,items} /tmp/scrapyd && \
    chown -R scrapyd:scrapyd /mnt/gcs /tmp/scrapyd

ENV PORT=8080 \
    SCRAPYD_BIND_ADDRESS=0.0.0.0 \
    SCRAPYD_HTTP_PORT=8080 \
    SCRAPYD_EGG_DIR=/mnt/gcs/eggs \
    SCRAPYD_LOGS_DIR=/mnt/gcs/logs \
    SCRAPYD_ITEMS_DIR=/mnt/gcs/items \
    SCRAPYD_DBS_DIR=/tmp/scrapyd

USER scrapyd
EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:8080/daemonstatus.json || exit 1

CMD ["python", "-m", "scrapyd.cloudrun"]
```

### 2. Build and Push Image

```bash
# Build image
docker build -t gcr.io/$PROJECT_ID/scrapyd:latest .

# Configure Docker for GCR
gcloud auth configure-docker

# Push image
docker push gcr.io/$PROJECT_ID/scrapyd:latest
```

### 3. Create Cloud Storage Bucket

```bash
# Create bucket for persistent storage
gsutil mb -p $PROJECT_ID -c STANDARD -l $REGION gs://$PROJECT_ID-scrapyd-data

# Set permissions
gsutil iam ch serviceAccount:$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")-compute@developer.gserviceaccount.com:objectAdmin gs://$PROJECT_ID-scrapyd-data
```

### 4. Deploy to Cloud Run

```bash
gcloud run deploy $SERVICE_NAME \
  --image=gcr.io/$PROJECT_ID/scrapyd:latest \
  --platform=managed \
  --region=$REGION \
  --allow-unauthenticated \
  --execution-environment=gen2 \
  --cpu=4 \
  --memory=8Gi \
  --concurrency=1000 \
  --timeout=3600 \
  --min-instances=0 \
  --max-instances=100 \
  --set-env-vars="GOOGLE_CLOUD_PROJECT=$PROJECT_ID,GCS_BUCKET=$PROJECT_ID-scrapyd-data,SCRAPYD_MAX_PROC=10"
```

## Infrastructure as Code (Terraform)

### Setup Terraform

```bash
# Install Terraform
wget https://releases.hashicorp.com/terraform/1.5.0/terraform_1.5.0_linux_amd64.zip
unzip terraform_1.5.0_linux_amd64.zip
sudo mv terraform /usr/local/bin/

# Initialize Terraform
cd terraform/
terraform init
```

### Configure Variables

```hcl
# terraform/variables.tf
variable "project_id" {
  description = "Google Cloud Project ID"
  type        = string
}

variable "region" {
  description = "Google Cloud Region"
  type        = string
  default     = "us-central1"
}

variable "max_concurrent_spiders" {
  description = "Maximum concurrent spider processes"
  type        = string
  default     = "10"
}

variable "github_owner" {
  description = "GitHub repository owner"
  type        = string
}

variable "github_repo" {
  description = "GitHub repository name"
  type        = string
}

variable "alert_email" {
  description = "Email for monitoring alerts"
  type        = string
}
```

### Deploy Infrastructure

```bash
# Set variables
terraform plan -var="project_id=$PROJECT_ID" \
               -var="github_owner=your-username" \
               -var="github_repo=scrapyd" \
               -var="alert_email=admin@example.com"

# Apply changes
terraform apply -var="project_id=$PROJECT_ID" \
                -var="github_owner=your-username" \
                -var="github_repo=scrapyd" \
                -var="alert_email=admin@example.com"
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GOOGLE_CLOUD_PROJECT` | GCP Project ID | Required |
| `GCS_BUCKET` | Cloud Storage bucket name | Required |
| `SCRAPYD_MAX_PROC` | Max concurrent spiders | 10 |
| `SCRAPYD_BIND_ADDRESS` | Bind address | 0.0.0.0 |
| `SCRAPYD_HTTP_PORT` | HTTP port | 8080 |
| `PORT` | Cloud Run port | 8080 |

### Cloud Run Service Configuration

```yaml
# cloudrun.yaml
apiVersion: serving.knative.dev/v1
kind: Service
metadata:
  name: scrapyd-service
  annotations:
    run.googleapis.com/execution-environment: gen2
    run.googleapis.com/cpu-throttling: "false"
spec:
  template:
    metadata:
      annotations:
        run.googleapis.com/execution-environment: gen2
        run.googleapis.com/cpu-throttling: "false"
        run.googleapis.com/timeout: "3600"
        run.googleapis.com/http2: "true"
        run.googleapis.com/vpc-access-connector: scrapyd-connector
        run.googleapis.com/vpc-access-egress: private-ranges-only
    spec:
      containerConcurrency: 1000
      timeoutSeconds: 3600
      containers:
      - image: gcr.io/PROJECT_ID/scrapyd:latest
        ports:
        - containerPort: 8080
        env:
        - name: SCRAPYD_MAX_PROC
          value: "10"
        - name: GOOGLE_CLOUD_PROJECT
          value: "PROJECT_ID"
        - name: GCS_BUCKET
          value: "scrapyd-data-bucket"
        resources:
          limits:
            cpu: "4"
            memory: "8Gi"
          requests:
            cpu: "1"
            memory: "2Gi"
        volumeMounts:
        - name: gcs-volume
          mountPath: /mnt/gcs
      volumes:
      - name: gcs-volume
        csi:
          driver: gcsfuse.csi.storage.gke.io
          volumeAttributes:
            bucketName: scrapyd-data-bucket
            mountOptions: "implicit-dirs"
      scaling:
        minScale: 0
        maxScale: 100
```

## Monitoring and Alerting

### Enable Cloud Monitoring

```bash
# Create monitoring dashboard
gcloud monitoring dashboards create --config-from-file=monitoring/cloudrun-dashboard.json
```

### Setup Alerts

```bash
# Create notification channel
gcloud alpha monitoring channels create \
  --display-name="Scrapyd Email Alerts" \
  --type=email \
  --channel-labels=email_address=admin@example.com

# Create alerting policies
gcloud alpha monitoring policies create \
  --policy-from-file=monitoring/alert-policies.yaml
```

### Custom Metrics

Add custom metrics to your Scrapyd application:

```python
# scrapyd/metrics.py
from google.cloud import monitoring_v3

class CloudMonitoringMetrics:
    def __init__(self, project_id):
        self.client = monitoring_v3.MetricServiceClient()
        self.project_name = f"projects/{project_id}"

    def send_metric(self, metric_name, value, labels=None):
        series = monitoring_v3.TimeSeries()
        series.metric.type = f"custom.googleapis.com/scrapyd/{metric_name}"
        series.resource.type = "cloud_run_revision"

        if labels:
            for key, value in labels.items():
                series.metric.labels[key] = value

        now = time.time()
        seconds = int(now)
        nanos = int((now - seconds) * 10 ** 9)

        interval = monitoring_v3.TimeInterval(
            {"end_time": {"seconds": seconds, "nanos": nanos}}
        )

        point = monitoring_v3.Point({
            "interval": interval,
            "value": {"double_value": value},
        })

        series.points = [point]
        self.client.create_time_series(
            name=self.project_name,
            time_series=[series]
        )

# Usage in your code
metrics = CloudMonitoringMetrics(os.getenv('GOOGLE_CLOUD_PROJECT'))
metrics.send_metric('active_spiders', len(active_spiders))
metrics.send_metric('queue_length', queue.qsize())
```

## Security

### Enable HTTPS and Authentication

```bash
# Map custom domain
gcloud run domain-mappings create \
  --service=$SERVICE_NAME \
  --domain=scrapyd.yourdomain.com \
  --region=$REGION
```

### Restrict Access with IAM

```bash
# Remove public access
gcloud run services remove-iam-policy-binding $SERVICE_NAME \
  --member="allUsers" \
  --role="roles/run.invoker" \
  --region=$REGION

# Add specific users
gcloud run services add-iam-policy-binding $SERVICE_NAME \
  --member="user:admin@yourdomain.com" \
  --role="roles/run.invoker" \
  --region=$REGION
```

### Use Service Accounts

```bash
# Create service account
gcloud iam service-accounts create scrapyd-runner \
  --display-name="Scrapyd Runner"

# Grant permissions
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:scrapyd-runner@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/storage.objectAdmin"

# Update Cloud Run service
gcloud run services update $SERVICE_NAME \
  --service-account=scrapyd-runner@$PROJECT_ID.iam.gserviceaccount.com \
  --region=$REGION
```

## Performance Optimization

### Resource Allocation

```bash
# High-performance configuration
gcloud run services update $SERVICE_NAME \
  --cpu=8 \
  --memory=16Gi \
  --concurrency=2000 \
  --max-instances=200 \
  --region=$REGION
```

### Enable HTTP/2

```bash
gcloud run services update $SERVICE_NAME \
  --use-http2 \
  --region=$REGION
```

### Optimize Cold Starts

```bash
# Keep minimum instances warm
gcloud run services update $SERVICE_NAME \
  --min-instances=2 \
  --region=$REGION
```

## Troubleshooting

### Check Service Logs

```bash
# View real-time logs
gcloud logs tail --format='value(textPayload)' \
  --filter="resource.type=cloud_run_revision AND resource.labels.service_name=$SERVICE_NAME"

# Search for errors
gcloud logs read \
  --filter="resource.type=cloud_run_revision AND resource.labels.service_name=$SERVICE_NAME AND severity>=ERROR" \
  --limit=50
```

### Debug Deployment Issues

```bash
# Check service status
gcloud run services describe $SERVICE_NAME --region=$REGION

# View recent revisions
gcloud run revisions list --service=$SERVICE_NAME --region=$REGION

# Check IAM permissions
gcloud run services get-iam-policy $SERVICE_NAME --region=$REGION
```

### Performance Issues

```bash
# Check resource utilization
gcloud monitoring metrics list --filter="metric.type:run.googleapis.com"

# View scaling metrics
gcloud run services describe $SERVICE_NAME \
  --region=$REGION \
  --format="value(status.conditions)"
```

## Cost Optimization

### Understanding Pricing

Cloud Run charges for:
- **CPU allocation** - vCPU-seconds
- **Memory allocation** - GB-seconds
- **Requests** - Number of requests
- **Networking** - Data transfer

### Cost Optimization Tips

1. **Right-size resources** - Start with lower CPU/memory
2. **Use minimum instances** - Only for high-traffic scenarios
3. **Optimize cold starts** - Reduce initialization time
4. **Monitor usage** - Use Cloud Monitoring dashboards
5. **Set budget alerts** - Prevent unexpected costs

```bash
# Set up budget alerts
gcloud billing budgets create \
  --billing-account=BILLING_ACCOUNT_ID \
  --display-name="Scrapyd Budget" \
  --budget-amount=100USD \
  --threshold-rules=percent=80,basis=CURRENT_SPEND \
  --threshold-rules=percent=100,basis=CURRENT_SPEND
```

## Backup and Disaster Recovery

### Data Backup

```bash
# Backup Cloud Storage bucket
gsutil -m cp -r gs://$PROJECT_ID-scrapyd-data gs://$PROJECT_ID-scrapyd-backup

# Scheduled backup with Cloud Scheduler
gcloud scheduler jobs create http scrapyd-backup \
  --schedule="0 2 * * *" \
  --uri="https://cloudfunctions.googleapis.com/backup-scrapyd" \
  --http-method=POST
```

### Multi-Region Deployment

```bash
# Deploy to multiple regions
REGIONS=("us-central1" "europe-west1" "asia-east1")

for region in "${REGIONS[@]}"; do
  gcloud run deploy $SERVICE_NAME-$region \
    --image=gcr.io/$PROJECT_ID/scrapyd:latest \
    --region=$region \
    --platform=managed
done
```

This deployment provides a production-ready, scalable Scrapyd service on Google Cloud with monitoring, security, and cost optimization built-in.