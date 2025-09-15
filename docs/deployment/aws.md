# Deploying Scrapyd to AWS

This guide covers deploying Scrapyd to Amazon Web Services using various services including ECS Fargate, Lambda, and EKS.

## Deployment Options

| Option | Best For | Scaling | Cost |
|--------|----------|---------|------|
| **ECS Fargate** | Production workloads | Auto-scaling | Medium |
| **EKS** | Complex orchestration | Horizontal/Vertical | High |
| **Lambda** | Lightweight spiders | Automatic | Low |
| **EC2** | Custom requirements | Manual/Auto | Variable |

## Option 1: ECS Fargate (Recommended)

### Prerequisites

```bash
# Install AWS CLI
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

# Configure credentials
aws configure
```

### 1. Create ECR Repository

```bash
# Set variables
export AWS_REGION="us-east-1"
export REPO_NAME="scrapyd"
export CLUSTER_NAME="scrapyd-cluster"

# Create ECR repository
aws ecr create-repository \
  --repository-name $REPO_NAME \
  --region $AWS_REGION

# Get login token
aws ecr get-login-password --region $AWS_REGION | \
  docker login --username AWS --password-stdin \
  $(aws sts get-caller-identity --query Account --output text).dkr.ecr.$AWS_REGION.amazonaws.com
```

### 2. Build and Push Container

```dockerfile
# Dockerfile.aws
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
RUN pip install --no-cache-dir /tmp/*.whl /tmp/boto3 /tmp/psycopg2-binary && rm /tmp/*.whl

# Install AWS-specific dependencies
RUN pip install boto3 psycopg2-binary

RUN mkdir -p /app/{eggs,logs,items,dbs} && \
    chown -R scrapyd:scrapyd /app

ENV SCRAPYD_BIND_ADDRESS=0.0.0.0 \
    SCRAPYD_HTTP_PORT=6800 \
    SCRAPYD_EGG_DIR=/app/eggs \
    SCRAPYD_LOGS_DIR=/app/logs \
    SCRAPYD_ITEMS_DIR=/app/items \
    SCRAPYD_DBS_DIR=/app/dbs

USER scrapyd
EXPOSE 6800

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:6800/daemonstatus.json || exit 1

CMD ["python", "-m", "scrapyd.aws"]
```

```bash
# Build and push
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_URI="$ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$REPO_NAME"

docker build -f Dockerfile.aws -t $ECR_URI:latest .
docker push $ECR_URI:latest
```

### 3. Create ECS Infrastructure

```yaml
# cloudformation/scrapyd-infrastructure.yaml
AWSTemplateFormatVersion: '2010-09-09'
Description: 'Scrapyd ECS Infrastructure'

Parameters:
  VpcCIDR:
    Type: String
    Default: '10.0.0.0/16'

  DatabasePassword:
    Type: String
    NoEcho: true
    MinLength: 8

Resources:
  # VPC Configuration
  VPC:
    Type: AWS::EC2::VPC
    Properties:
      CidrBlock: !Ref VpcCIDR
      EnableDnsHostnames: true
      EnableDnsSupport: true
      Tags:
        - Key: Name
          Value: ScrapydVPC

  PublicSubnet1:
    Type: AWS::EC2::Subnet
    Properties:
      VpcId: !Ref VPC
      AvailabilityZone: !Select [0, !GetAZs '']
      CidrBlock: !Sub '${VpcCIDR::-4}1.0/24'
      MapPublicIpOnLaunch: true

  PublicSubnet2:
    Type: AWS::EC2::Subnet
    Properties:
      VpcId: !Ref VPC
      AvailabilityZone: !Select [1, !GetAZs '']
      CidrBlock: !Sub '${VpcCIDR::-4}2.0/24'
      MapPublicIpOnLaunch: true

  PrivateSubnet1:
    Type: AWS::EC2::Subnet
    Properties:
      VpcId: !Ref VPC
      AvailabilityZone: !Select [0, !GetAZs '']
      CidrBlock: !Sub '${VpcCIDR::-4}3.0/24'

  PrivateSubnet2:
    Type: AWS::EC2::Subnet
    Properties:
      VpcId: !Ref VPC
      AvailabilityZone: !Select [1, !GetAZs '']
      CidrBlock: !Sub '${VpcCIDR::-4}4.0/24'

  # Internet Gateway
  InternetGateway:
    Type: AWS::EC2::InternetGateway

  InternetGatewayAttachment:
    Type: AWS::EC2::VPCGatewayAttachment
    Properties:
      InternetGatewayId: !Ref InternetGateway
      VpcId: !Ref VPC

  # Route Tables
  PublicRouteTable:
    Type: AWS::EC2::RouteTable
    Properties:
      VpcId: !Ref VPC

  DefaultPublicRoute:
    Type: AWS::EC2::Route
    DependsOn: InternetGatewayAttachment
    Properties:
      RouteTableId: !Ref PublicRouteTable
      DestinationCidrBlock: 0.0.0.0/0
      GatewayId: !Ref InternetGateway

  PublicSubnet1RouteTableAssociation:
    Type: AWS::EC2::SubnetRouteTableAssociation
    Properties:
      RouteTableId: !Ref PublicRouteTable
      SubnetId: !Ref PublicSubnet1

  PublicSubnet2RouteTableAssociation:
    Type: AWS::EC2::SubnetRouteTableAssociation
    Properties:
      RouteTableId: !Ref PublicRouteTable
      SubnetId: !Ref PublicSubnet2

  # Security Groups
  ALBSecurityGroup:
    Type: AWS::EC2::SecurityGroup
    Properties:
      GroupDescription: Access to the public facing load balancer
      VpcId: !Ref VPC
      SecurityGroupIngress:
        - IpProtocol: tcp
          FromPort: 80
          ToPort: 80
          CidrIp: 0.0.0.0/0
        - IpProtocol: tcp
          FromPort: 443
          ToPort: 443
          CidrIp: 0.0.0.0/0

  ECSSecurityGroup:
    Type: AWS::EC2::SecurityGroup
    Properties:
      GroupDescription: Access to the ECS containers
      VpcId: !Ref VPC
      SecurityGroupIngress:
        - IpProtocol: tcp
          FromPort: 6800
          ToPort: 6800
          SourceSecurityGroupId: !Ref ALBSecurityGroup

  # RDS Database
  DBSubnetGroup:
    Type: AWS::RDS::DBSubnetGroup
    Properties:
      DBSubnetGroupDescription: Subnet group for RDS database
      SubnetIds:
        - !Ref PrivateSubnet1
        - !Ref PrivateSubnet2

  DatabaseSecurityGroup:
    Type: AWS::EC2::SecurityGroup
    Properties:
      GroupDescription: Access to the RDS database
      VpcId: !Ref VPC
      SecurityGroupIngress:
        - IpProtocol: tcp
          FromPort: 5432
          ToPort: 5432
          SourceSecurityGroupId: !Ref ECSSecurityGroup

  Database:
    Type: AWS::RDS::DBInstance
    Properties:
      DBInstanceIdentifier: scrapyd-db
      DBInstanceClass: db.t3.micro
      Engine: postgres
      EngineVersion: '13.7'
      AllocatedStorage: '20'
      StorageType: gp2
      DBName: scrapyd
      MasterUsername: scrapyd
      MasterUserPassword: !Ref DatabasePassword
      VPCSecurityGroups:
        - !Ref DatabaseSecurityGroup
      DBSubnetGroupName: !Ref DBSubnetGroup
      BackupRetentionPeriod: 7
      MultiAZ: false
      PubliclyAccessible: false

  # S3 Bucket for storage
  S3Bucket:
    Type: AWS::S3::Bucket
    Properties:
      BucketName: !Sub 'scrapyd-data-${AWS::AccountId}-${AWS::Region}'
      VersioningConfiguration:
        Status: Enabled
      LifecycleConfiguration:
        Rules:
          - Id: DeleteOldVersions
            Status: Enabled
            NoncurrentVersionExpirationInDays: 30

  # ECS Cluster
  ECSCluster:
    Type: AWS::ECS::Cluster
    Properties:
      ClusterName: !Ref AWS::StackName

  # Application Load Balancer
  LoadBalancer:
    Type: AWS::ElasticLoadBalancingV2::LoadBalancer
    Properties:
      Scheme: internet-facing
      LoadBalancerAttributes:
        - Key: idle_timeout.timeout_seconds
          Value: '30'
      Subnets:
        - !Ref PublicSubnet1
        - !Ref PublicSubnet2
      SecurityGroups:
        - !Ref ALBSecurityGroup

  TargetGroup:
    Type: AWS::ElasticLoadBalancingV2::TargetGroup
    Properties:
      HealthCheckIntervalSeconds: 10
      HealthCheckPath: /daemonstatus.json
      HealthCheckProtocol: HTTP
      HealthCheckTimeoutSeconds: 5
      HealthyThresholdCount: 2
      TargetType: ip
      Port: 6800
      Protocol: HTTP
      UnhealthyThresholdCount: 2
      VpcId: !Ref VPC

  LoadBalancerListener:
    Type: AWS::ElasticLoadBalancingV2::Listener
    Properties:
      DefaultActions:
        - TargetGroupArn: !Ref TargetGroup
          Type: forward
      LoadBalancerArn: !Ref LoadBalancer
      Port: 80
      Protocol: HTTP

Outputs:
  VPC:
    Description: VPC ID
    Value: !Ref VPC
    Export:
      Name: !Sub ${AWS::StackName}-VPC

  LoadBalancerUrl:
    Description: URL of the load balancer
    Value: !Sub http://${LoadBalancer.DNSName}
    Export:
      Name: !Sub ${AWS::StackName}-LoadBalancerUrl

  DatabaseEndpoint:
    Description: RDS instance endpoint
    Value: !GetAtt Database.Endpoint.Address
    Export:
      Name: !Sub ${AWS::StackName}-DatabaseEndpoint

  S3Bucket:
    Description: S3 bucket name
    Value: !Ref S3Bucket
    Export:
      Name: !Sub ${AWS::StackName}-S3Bucket
```

### 4. Deploy Infrastructure

```bash
# Deploy CloudFormation stack
aws cloudformation create-stack \
  --stack-name scrapyd-infrastructure \
  --template-body file://cloudformation/scrapyd-infrastructure.yaml \
  --parameters ParameterKey=DatabasePassword,ParameterValue=SecurePassword123! \
  --capabilities CAPABILITY_IAM

# Wait for completion
aws cloudformation wait stack-create-complete \
  --stack-name scrapyd-infrastructure
```

### 5. Create ECS Service

```yaml
# cloudformation/scrapyd-service.yaml
AWSTemplateFormatVersion: '2010-09-09'
Description: 'Scrapyd ECS Service'

Parameters:
  InfrastructureStackName:
    Type: String
    Default: scrapyd-infrastructure

  ImageUri:
    Type: String
    Description: ECR image URI

Resources:
  # ECS Task Definition
  TaskDefinition:
    Type: AWS::ECS::TaskDefinition
    Properties:
      Family: scrapyd
      Cpu: 1024
      Memory: 2048
      NetworkMode: awsvpc
      RequiresCompatibilities:
        - FARGATE
      ExecutionRoleArn: !Ref ExecutionRole
      TaskRoleArn: !Ref TaskRole
      ContainerDefinitions:
        - Name: scrapyd
          Cpu: 1024
          Memory: 2048
          Image: !Ref ImageUri
          PortMappings:
            - ContainerPort: 6800
          Environment:
            - Name: DATABASE_URL
              Value: !Sub
                - 'postgresql://scrapyd:SecurePassword123!@${DatabaseEndpoint}:5432/scrapyd'
                - DatabaseEndpoint:
                    Fn::ImportValue: !Sub '${InfrastructureStackName}-DatabaseEndpoint'
            - Name: S3_BUCKET
              Value:
                Fn::ImportValue: !Sub '${InfrastructureStackName}-S3Bucket'
            - Name: AWS_DEFAULT_REGION
              Value: !Ref AWS::Region
            - Name: SCRAPYD_MAX_PROC
              Value: '10'
          LogConfiguration:
            LogDriver: awslogs
            Options:
              awslogs-group: !Ref LogGroup
              awslogs-region: !Ref AWS::Region
              awslogs-stream-prefix: scrapyd
          HealthCheck:
            Command:
              - CMD-SHELL
              - curl -f http://localhost:6800/daemonstatus.json || exit 1
            Interval: 30
            Timeout: 5
            Retries: 3

  # IAM Roles
  ExecutionRole:
    Type: AWS::IAM::Role
    Properties:
      RoleName: !Sub ecs-task-execution-role-${AWS::StackName}
      AssumeRolePolicyDocument:
        Statement:
          - Effect: Allow
            Principal:
              Service: ecs-tasks.amazonaws.com
            Action: 'sts:AssumeRole'
      ManagedPolicyArns:
        - 'arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy'

  TaskRole:
    Type: AWS::IAM::Role
    Properties:
      RoleName: !Sub ecs-task-role-${AWS::StackName}
      AssumeRolePolicyDocument:
        Statement:
          - Effect: Allow
            Principal:
              Service: ecs-tasks.amazonaws.com
            Action: 'sts:AssumeRole'
      Policies:
        - PolicyName: S3Access
          PolicyDocument:
            Statement:
              - Effect: Allow
                Action:
                  - 's3:GetObject'
                  - 's3:PutObject'
                  - 's3:DeleteObject'
                  - 's3:ListBucket'
                Resource:
                  - !Sub
                    - '${S3BucketArn}/*'
                    - S3BucketArn:
                        Fn::ImportValue: !Sub '${InfrastructureStackName}-S3Bucket'
                  - Fn::ImportValue: !Sub '${InfrastructureStackName}-S3Bucket'

  # CloudWatch Logs
  LogGroup:
    Type: AWS::Logs::LogGroup
    Properties:
      LogGroupName: !Sub /ecs/${AWS::StackName}
      RetentionInDays: 30

  # ECS Service
  Service:
    Type: AWS::ECS::Service
    Properties:
      ServiceName: scrapyd
      Cluster: !Sub '${InfrastructureStackName}'
      LaunchType: FARGATE
      DeploymentConfiguration:
        MaximumPercent: 200
        MinimumHealthyPercent: 75
      DesiredCount: 2
      NetworkConfiguration:
        AwsvpcConfiguration:
          AssignPublicIp: ENABLED
          SecurityGroups:
            - Fn::ImportValue: !Sub '${InfrastructureStackName}-ECSSecurityGroup'
          Subnets:
            - Fn::ImportValue: !Sub '${InfrastructureStackName}-PublicSubnet1'
            - Fn::ImportValue: !Sub '${InfrastructureStackName}-PublicSubnet2'
      TaskDefinition: !Ref TaskDefinition
      LoadBalancers:
        - ContainerName: scrapyd
          ContainerPort: 6800
          TargetGroupArn:
            Fn::ImportValue: !Sub '${InfrastructureStackName}-TargetGroup'

  # Auto Scaling
  ScalableTarget:
    Type: AWS::ApplicationAutoScaling::ScalableTarget
    Properties:
      MaxCapacity: 10
      MinCapacity: 1
      ResourceId: !Sub service/${InfrastructureStackName}/${Service.Name}
      RoleARN: !Sub arn:aws:iam::${AWS::AccountId}:role/aws-service-role/ecs.application-autoscaling.amazonaws.com/AWSServiceRoleForApplicationAutoScaling_ECSService
      ScalableDimension: ecs:service:DesiredCount
      ServiceNamespace: ecs

  ScalingPolicy:
    Type: AWS::ApplicationAutoScaling::ScalingPolicy
    Properties:
      PolicyName: ScrapydTargetTrackingScalingPolicy
      PolicyType: TargetTrackingScaling
      ScalingTargetId: !Ref ScalableTarget
      TargetTrackingScalingPolicyConfiguration:
        PredefinedMetricSpecification:
          PredefinedMetricType: ECSServiceAverageCPUUtilization
        ScaleInCooldown: 300
        ScaleOutCooldown: 300
        TargetValue: 70.0
```

### 6. Deploy Service

```bash
# Get ECR URI
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_URI="$ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$REPO_NAME:latest"

# Deploy service
aws cloudformation create-stack \
  --stack-name scrapyd-service \
  --template-body file://cloudformation/scrapyd-service.yaml \
  --parameters ParameterKey=ImageUri,ParameterValue=$ECR_URI \
  --capabilities CAPABILITY_NAMED_IAM

# Wait for completion
aws cloudformation wait stack-create-complete \
  --stack-name scrapyd-service
```

## Option 2: AWS Lambda (Serverless)

For lightweight spider workloads, deploy individual spiders as Lambda functions.

### Lambda Function Template

```python
# lambda/spider_handler.py
import json
import os
import tempfile
import subprocess
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings

def lambda_handler(event, context):
    """
    AWS Lambda handler for running individual Scrapy spiders
    """
    try:
        # Extract parameters
        spider_name = event.get('spider', '')
        project_name = event.get('project', '')
        settings = event.get('settings', {})
        spider_args = event.get('args', {})

        if not spider_name:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Spider name is required'})
            }

        # Download project from S3
        s3_bucket = os.environ['S3_BUCKET']
        download_project(s3_bucket, project_name)

        # Run spider
        result = run_spider(spider_name, settings, spider_args)

        return {
            'statusCode': 200,
            'body': json.dumps({
                'status': 'completed',
                'items_count': result.get('item_count', 0),
                'duration': result.get('duration', 0)
            })
        }

    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }

def download_project(bucket, project_name):
    """Download and extract project from S3"""
    import boto3

    s3 = boto3.client('s3')

    with tempfile.NamedTemporaryFile(suffix='.egg') as tmp_file:
        s3.download_fileobj(bucket, f'projects/{project_name}.egg', tmp_file)
        tmp_file.flush()

        # Extract egg file
        extract_dir = f'/tmp/{project_name}'
        subprocess.run(['unzip', '-o', tmp_file.name, '-d', extract_dir])

        # Add to Python path
        import sys
        sys.path.insert(0, extract_dir)

def run_spider(spider_name, custom_settings, spider_args):
    """Run the spider with custom settings"""
    from scrapy.crawler import CrawlerProcess

    settings = get_project_settings()
    settings.update(custom_settings)

    # Configure for Lambda environment
    settings.update({
        'LOG_LEVEL': 'INFO',
        'ROBOTSTXT_OBEY': True,
        'CONCURRENT_REQUESTS': 16,
        'DOWNLOAD_DELAY': 1,
    })

    process = CrawlerProcess(settings)

    # Track results
    stats = {}

    def spider_closed(spider, reason):
        stats['item_count'] = spider.crawler.stats.get_value('item_scraped_count', 0)
        stats['duration'] = spider.crawler.stats.get_value('elapsed_time_seconds', 0)

    # Connect signal
    from scrapy import signals
    from scrapy.crawler import CrawlerRunner

    runner = CrawlerRunner(settings)
    crawler = runner.create_crawler(spider_name)
    crawler.signals.connect(spider_closed, signal=signals.spider_closed)

    # Run spider
    runner.crawl(crawler, **spider_args)
    runner.start()

    return stats
```

### Lambda Deployment

```yaml
# serverless.yml
service: scrapyd-lambda

provider:
  name: aws
  runtime: python3.9
  stage: ${opt:stage, 'dev'}
  region: ${opt:region, 'us-east-1'}
  timeout: 900  # 15 minutes
  memorySize: 3008
  environment:
    S3_BUCKET: ${self:custom.bucketName}

  iamRoleStatements:
    - Effect: Allow
      Action:
        - s3:GetObject
        - s3:PutObject
        - s3:ListBucket
      Resource:
        - arn:aws:s3:::${self:custom.bucketName}
        - arn:aws:s3:::${self:custom.bucketName}/*

custom:
  bucketName: scrapyd-lambda-${self:provider.stage}-${aws:accountId}

functions:
  runSpider:
    handler: spider_handler.lambda_handler
    events:
      - http:
          path: run
          method: post
      - schedule:
          rate: cron(0 */6 * * ? *)  # Every 6 hours
          input:
            spider: "quotes"
            project: "tutorial"

  scheduleSpiders:
    handler: scheduler.lambda_handler
    events:
      - schedule:
          rate: rate(5 minutes)

resources:
  Resources:
    SpiderBucket:
      Type: AWS::S3::Bucket
      Properties:
        BucketName: ${self:custom.bucketName}

plugins:
  - serverless-python-requirements

package:
  exclude:
    - node_modules/**
    - .git/**
```

```bash
# Deploy with Serverless Framework
npm install -g serverless
npm install serverless-python-requirements

# Deploy
serverless deploy
```

## Option 3: EKS (Kubernetes)

For complex orchestration requirements, use Amazon EKS.

### Create EKS Cluster

```bash
# Install eksctl
curl --silent --location "https://github.com/weaveworks/eksctl/releases/latest/download/eksctl_$(uname -s)_amd64.tar.gz" | tar xz -C /tmp
sudo mv /tmp/eksctl /usr/local/bin

# Create cluster
eksctl create cluster \
  --name scrapyd-cluster \
  --version 1.24 \
  --region us-east-1 \
  --nodegroup-name workers \
  --node-type t3.medium \
  --nodes 2 \
  --nodes-min 1 \
  --nodes-max 4 \
  --managed
```

### Deploy Scrapyd to EKS

```yaml
# k8s/scrapyd-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: scrapyd
  namespace: default
spec:
  replicas: 3
  selector:
    matchLabels:
      app: scrapyd
  template:
    metadata:
      labels:
        app: scrapyd
    spec:
      containers:
      - name: scrapyd
        image: your-account.dkr.ecr.us-east-1.amazonaws.com/scrapyd:latest
        ports:
        - containerPort: 6800
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: scrapyd-secrets
              key: database-url
        - name: S3_BUCKET
          value: "scrapyd-data-bucket"
        - name: AWS_DEFAULT_REGION
          value: "us-east-1"
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /daemonstatus.json
            port: 6800
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /daemonstatus.json
            port: 6800
          initialDelaySeconds: 10
          periodSeconds: 5

---
apiVersion: v1
kind: Service
metadata:
  name: scrapyd-service
spec:
  selector:
    app: scrapyd
  ports:
  - port: 80
    targetPort: 6800
  type: LoadBalancer

---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: scrapyd-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: scrapyd
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

```bash
# Deploy to EKS
kubectl apply -f k8s/scrapyd-deployment.yaml

# Get service URL
kubectl get service scrapyd-service
```

## Monitoring and Logging

### CloudWatch Monitoring

```python
# scrapyd/aws/cloudwatch.py
import boto3
import time
from datetime import datetime

class CloudWatchMetrics:
    def __init__(self, namespace='Scrapyd'):
        self.cloudwatch = boto3.client('cloudwatch')
        self.namespace = namespace

    def put_metric(self, metric_name, value, unit='Count', dimensions=None):
        """Send custom metric to CloudWatch"""
        try:
            self.cloudwatch.put_metric_data(
                Namespace=self.namespace,
                MetricData=[
                    {
                        'MetricName': metric_name,
                        'Value': value,
                        'Unit': unit,
                        'Timestamp': datetime.utcnow(),
                        'Dimensions': dimensions or []
                    }
                ]
            )
        except Exception as e:
            print(f"Failed to send metric {metric_name}: {e}")

# Usage
metrics = CloudWatchMetrics()
metrics.put_metric('ActiveSpiders', 5, dimensions=[
    {'Name': 'Project', 'Value': 'myproject'}
])
metrics.put_metric('QueueLength', 20)
```

### Centralized Logging

```yaml
# cloudformation/logging.yaml
Resources:
  LogGroup:
    Type: AWS::Logs::LogGroup
    Properties:
      LogGroupName: /aws/scrapyd
      RetentionInDays: 30

  LogStream:
    Type: AWS::Logs::LogStream
    Properties:
      LogGroupName: !Ref LogGroup
      LogStreamName: application-logs
```

This comprehensive AWS deployment guide provides multiple options for running Scrapyd at scale with proper monitoring, security, and cost optimization.