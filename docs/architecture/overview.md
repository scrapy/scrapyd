# Scrapyd Architecture Overview

## Introduction

Scrapyd is a web service daemon for running Scrapy spiders. It provides a JSON API to upload projects, schedule spiders, and monitor execution. This document describes the internal architecture and design principles.

## High-Level Architecture

```mermaid
graph TB
    subgraph "Client Layer"
        CLI[Scrapyd Client]
        WEB[Web Interface]
        API[REST API Clients]
    end

    subgraph "Service Layer"
        HTTP[HTTP Server<br/>Twisted Web]
        AUTH[Authentication<br/>Middleware]
        RATE[Rate Limiting]
        ROUTER[API Router]
    end

    subgraph "Business Logic"
        WS[WebService<br/>Handlers]
        SCHED[Spider<br/>Scheduler]
        POLL[Job<br/>Poller]
        LAUNCH[Process<br/>Launcher]
    end

    subgraph "Storage Layer"
        EGGS[Egg Storage<br/>Projects]
        JOBS[Job Storage<br/>History]
        QUEUE[Spider Queue<br/>Pending Jobs]
        CONFIG[Configuration<br/>Settings]
    end

    subgraph "Runtime"
        PROC[Spider Processes<br/>Scrapy Crawl]
        LOGS[Log Files]
        ITEMS[Item Files]
    end

    CLI --> HTTP
    WEB --> HTTP
    API --> HTTP

    HTTP --> AUTH
    AUTH --> RATE
    RATE --> ROUTER
    ROUTER --> WS

    WS --> SCHED
    WS --> POLL
    WS --> LAUNCH

    SCHED --> QUEUE
    POLL --> QUEUE
    LAUNCH --> PROC

    SCHED --> EGGS
    LAUNCH --> JOBS

    PROC --> LOGS
    PROC --> ITEMS
```

## Core Components

### 1. Web Service Layer

The web service layer handles all HTTP requests and provides both the JSON API and web interface.

```mermaid
sequenceDiagram
    participant Client
    participant WebServer
    participant Auth
    participant Handler
    participant Storage

    Client->>WebServer: HTTP Request
    WebServer->>Auth: Validate Request
    Auth->>WebServer: Authorized
    WebServer->>Handler: Route Request
    Handler->>Storage: Read/Write Data
    Storage->>Handler: Return Data
    Handler->>WebServer: JSON Response
    WebServer->>Client: HTTP Response
```

**Key Files:**
- `scrapyd/webservice.py` - API endpoint handlers
- `scrapyd/website.py` - Web interface
- `scrapyd/basicauth.py` - Authentication middleware

### 2. Job Scheduling System

The scheduling system manages the lifecycle of spider jobs from submission to completion.

```mermaid
stateDiagram-v2
    [*] --> Pending: Schedule Spider
    Pending --> Running: Poller Picks Up
    Running --> Finished: Success
    Running --> Failed: Error
    Finished --> [*]
    Failed --> [*]

    note right of Pending: Job added to queue\nwith priority
    note right of Running: Process spawned\nLogs captured
    note right of Finished: Results stored\nCleanup performed
```

**Components:**
- **Scheduler** (`scheduler.py`) - Adds jobs to queue with priority
- **Poller** (`poller.py`) - Continuously checks for pending jobs
- **Launcher** (`launcher.py`) - Spawns and manages spider processes
- **Queue** (`spiderqueue.py`) - SQLite-backed job queue

### 3. Process Management

Scrapyd uses Twisted's process management to spawn and monitor Scrapy processes.

```mermaid
graph LR
    subgraph "Launcher"
        SLOTS[Process Slots<br/>max_proc limit]
        SPAWN[Process Spawner]
        MON[Process Monitor]
    end

    subgraph "Spider Processes"
        P1[Spider 1<br/>python -m scrapy crawl]
        P2[Spider 2<br/>python -m scrapy crawl]
        P3[Spider N<br/>python -m scrapy crawl]
    end

    SLOTS --> SPAWN
    SPAWN --> P1
    SPAWN --> P2
    SPAWN --> P3

    P1 --> MON
    P2 --> MON
    P3 --> MON
```

**Process Lifecycle:**
1. Job picked from queue
2. Environment prepared (PYTHONPATH, settings)
3. Process spawned with `subprocess`
4. Output captured to log files
5. Exit code monitored
6. Results stored in job storage

### 4. Storage Architecture

Scrapyd uses pluggable storage backends for different data types.

```mermaid
graph TB
    subgraph "Storage Interfaces"
        IEGG[IEggStorage]
        IJOB[IJobStorage]
        IQUEUE[ISpiderQueue]
    end

    subgraph "Default Implementations"
        FEGG[FilesystemEggStorage<br/>Local files]
        MJOB[MemoryJobStorage<br/>In-memory dict]
        SQUEUE[SqliteSpiderQueue<br/>SQLite database]
    end

    subgraph "Cloud Implementations"
        S3EGG[S3EggStorage<br/>AWS S3]
        PGJOB[PostgreSQLJobStorage<br/>PostgreSQL]
        REDIS[RedisSpiderQueue<br/>Redis]
    end

    IEGG -.-> FEGG
    IEGG -.-> S3EGG
    IJOB -.-> MJOB
    IJOB -.-> PGJOB
    IQUEUE -.-> SQUEUE
    IQUEUE -.-> REDIS
```

### 5. Configuration System

Configuration is loaded from multiple sources with precedence:

```mermaid
graph TD
    ENV[Environment Variables] --> MERGE[Config Merger]
    FILE[scrapyd.conf] --> MERGE
    DEFAULTS[Built-in Defaults] --> MERGE

    MERGE --> CONFIG[Final Configuration]

    CONFIG --> APP[Application Components]
    CONFIG --> STORAGE[Storage Backends]
    CONFIG --> NETWORK[Network Settings]
```

**Configuration Sources (highest to lowest precedence):**
1. Environment variables (`SCRAPYD_*`)
2. Configuration file (`scrapyd.conf`)
3. Built-in defaults

## Data Flow

### Project Deployment

```mermaid
sequenceDiagram
    participant Developer
    participant ScrapydClient
    participant WebService
    participant EggStorage
    participant SpiderList

    Developer->>ScrapydClient: scrapyd-deploy
    ScrapydClient->>ScrapydClient: Build egg file
    ScrapydClient->>WebService: POST /addversion.json
    WebService->>EggStorage: store(project, version, egg)
    EggStorage->>WebService: success
    WebService->>SpiderList: extract_spiders(egg)
    SpiderList->>WebService: spider_list
    WebService->>ScrapydClient: {"status": "ok"}
    ScrapydClient->>Developer: Deployment complete
```

### Spider Execution

```mermaid
sequenceDiagram
    participant Client
    participant WebService
    participant Scheduler
    participant Queue
    participant Poller
    participant Launcher
    participant Process

    Client->>WebService: POST /schedule.json
    WebService->>Scheduler: schedule(project, spider, args)
    Scheduler->>Queue: add_job(job_data)
    Queue->>Scheduler: job_id
    Scheduler->>WebService: job_id
    WebService->>Client: {"jobid": "..."}

    loop Polling
        Poller->>Queue: next_job()
        Queue->>Poller: job_data
        Poller->>Launcher: spawn(job_data)
        Launcher->>Process: start spider
        Process->>Launcher: exit code
        Launcher->>Poller: completed
    end
```

### Status Monitoring

```mermaid
sequenceDiagram
    participant Client
    participant WebService
    participant JobStorage
    participant Queue
    participant Launcher

    Client->>WebService: GET /listjobs.json
    WebService->>Queue: list_pending()
    Queue->>WebService: pending_jobs
    WebService->>Launcher: list_running()
    Launcher->>WebService: running_jobs
    WebService->>JobStorage: list_finished()
    JobStorage->>WebService: finished_jobs
    WebService->>Client: {"pending": [...], "running": [...], "finished": [...]}
```

## Scalability Considerations

### Vertical Scaling

- **Increase `max_proc`** - More concurrent spider processes
- **Add memory** - Support memory-intensive spiders
- **Faster storage** - SSD for database and logs
- **CPU cores** - Better process scheduling

### Horizontal Scaling

```mermaid
graph TB
    subgraph "Load Balancer"
        LB[HAProxy/Nginx]
    end

    subgraph "Scrapyd Cluster"
        S1[Scrapyd Node 1]
        S2[Scrapyd Node 2]
        S3[Scrapyd Node N]
    end

    subgraph "Shared Storage"
        DB[(PostgreSQL<br/>Job Queue)]
        S3[(S3/GCS<br/>Eggs & Logs)]
        REDIS[(Redis<br/>Cache)]
    end

    LB --> S1
    LB --> S2
    LB --> S3

    S1 --> DB
    S2 --> DB
    S3 --> DB

    S1 --> S3
    S2 --> S3
    S3 --> S3

    S1 --> REDIS
    S2 --> REDIS
    S3 --> REDIS
```

**Requirements for Horizontal Scaling:**
- Shared database for job queue
- Shared storage for eggs and logs
- Session affinity not required
- Health checks for load balancer

### Cloud-Native Deployment

```mermaid
graph TB
    subgraph "Kubernetes Cluster"
        subgraph "Namespace: scrapyd"
            DEPLOY[Deployment<br/>scrapyd-app]
            SVC[Service<br/>scrapyd-svc]
            HPA[HorizontalPodAutoscaler]
            PVC[PersistentVolumeClaim]
        end
    end

    subgraph "External Services"
        RDS[(RDS PostgreSQL)]
        S3[(S3 Bucket)]
        REDIS[(ElastiCache Redis)]
    end

    DEPLOY --> RDS
    DEPLOY --> S3
    DEPLOY --> REDIS
    DEPLOY --> PVC

    HPA --> DEPLOY
    SVC --> DEPLOY
```

## Security Architecture

### Authentication Flow

```mermaid
sequenceDiagram
    participant Client
    participant Gateway
    participant Auth
    participant Service

    Client->>Gateway: Request with credentials
    Gateway->>Auth: Validate credentials
    Auth->>Auth: Check permissions
    Auth->>Gateway: Auth result
    alt Authorized
        Gateway->>Service: Forward request
        Service->>Gateway: Response
        Gateway->>Client: Response
    else Unauthorized
        Gateway->>Client: 401/403 Error
    end
```

### Security Layers

1. **Network Security**
   - TLS encryption for all communication
   - VPC/firewall rules
   - Rate limiting and DDoS protection

2. **Authentication & Authorization**
   - JWT tokens or API keys
   - Role-based access control (RBAC)
   - Permission-based endpoint access

3. **Process Security**
   - Non-root user execution
   - Resource limits per spider
   - Isolated environments

4. **Data Security**
   - Encrypted storage at rest
   - Secure secret management
   - Audit logging

## Performance Characteristics

### Throughput Metrics

| Metric | Typical Value | Notes |
|--------|---------------|-------|
| API Requests/sec | 100-1000 | Depends on endpoint |
| Concurrent Spiders | 10-100 | Limited by `max_proc` |
| Job Queue Depth | 1000-10000 | SQLite or PostgreSQL |
| Spider Startup Time | 2-10 seconds | Including Python import |
| Memory per Spider | 50-500 MB | Varies by spider complexity |

### Bottlenecks

1. **Process Limits** - `max_proc` setting
2. **Memory** - Spider memory usage
3. **I/O** - Log writing, database queries
4. **Network** - Target website rate limits

### Optimization Strategies

- **Caching** - Spider lists, project metadata
- **Connection Pooling** - Database connections
- **Async I/O** - Non-blocking operations
- **Process Reuse** - Warm process pools
- **Resource Monitoring** - Alerts and auto-scaling

## Extension Points

### Custom Storage Backends

Implement storage interfaces:
- `IEggStorage` - Project storage
- `IJobStorage` - Job history
- `ISpiderScheduler` - Custom scheduling logic

### Middleware Integration

- **Authentication** - Custom auth providers
- **Monitoring** - Metrics collection
- **Logging** - Structured logging
- **Caching** - Custom cache backends

### Plugin System

```python
from scrapyd.interfaces import IPlugin

class MetricsPlugin(IPlugin):
    def on_spider_start(self, project, spider, job_id):
        # Custom logic
        pass

    def on_spider_complete(self, project, spider, job_id, success):
        # Custom logic
        pass
```

This architecture supports both small single-instance deployments and large-scale distributed systems while maintaining backward compatibility and extensibility.