# Distributed AI Task Orchestrator

A production-grade, cloud-native system for **asynchronous AI-powered text analysis at scale**. Tasks are submitted through a REST API, queued in Redis, processed by auto-scaling Celery workers that call the **Groq LLaMA-3.3-70b** model, and persisted in PostgreSQL — all observable in real-time through a React dashboard.

---

## Architecture

### System Overview

```mermaid
graph TB
    USER("Browser / Client")

    subgraph INGRESS_LAYER["Ingress Layer"]
        NG["NGINX Ingress Controller<br/>/ → frontend : 80<br/>/api/* → api : 8000"]
    end

    subgraph FRONTEND_LAYER["Frontend — React + Vite"]
        FE["React Dashboard  ·  Nginx :80<br/>── Queue Stats  ── System Health<br/>── Worker Autoscaling  ── Results Log<br/>Polls /api/* every 4 s"]
    end

    subgraph API_LAYER["API Layer — FastAPI / Uvicorn :8000"]
        AP["FastAPI Application<br/>POST  /tasks  ·  POST  /tasks/bulk<br/>GET   /tasks  ·  GET   /tasks/:id<br/>GET   /metrics/queue  ·  /metrics/workers<br/>GET   /metrics/results  ·  /metrics/autoscaling/events<br/>GET   /health  ·  /health/detailed"]
    end

    subgraph BROKER_LAYER["Message Broker — Redis 7 :6379"]
        RD[("Redis<br/>── List  celery         task queue<br/>── Key   worker:heartbeat  TTL 30 s<br/>── Backend celery-results")]
    end

    subgraph WORKER_LAYER["Celery Worker Pool  ·  1 – 10 Pods"]
        W1["Worker Pod<br/>concurrency = 2<br/>heartbeat interval = 15 s<br/>max_retries = 3  ·  countdown = 10 s"]
        WDOTS(("  ...  "))
        WN["Worker Pod N<br/>concurrency = 2<br/>heartbeat interval = 15 s<br/>max_retries = 3  ·  countdown = 10 s"]
    end

    subgraph AI_LAYER["External AI — Groq Cloud"]
        GROQ("Groq API<br/>Model: llama-3.3-70b-versatile<br/>max_tokens = 512  ·  temperature = 0.3<br/>Output: Summary · Issues · Action")
    end

    subgraph DB_LAYER["Persistence — PostgreSQL 15 :5432"]
        PG[("PostgreSQL<br/>Table: tasks<br/>── id          UUID PK<br/>── input_text  TEXT<br/>── status      ENUM<br/>── result      TEXT<br/>── retry_count INT<br/>── created_at  TIMESTAMPTZ<br/>── updated_at  TIMESTAMPTZ")]
    end

    subgraph AUTOSCALE_LAYER["Autoscaling — KEDA + Kubernetes"]
        KEDA["KEDA ScaledObject<br/>Trigger: Redis list length >= 3<br/>minReplicas = 1  ·  maxReplicas = 10<br/>pollingInterval = 10 s  ·  cooldownPeriod = 30 s"]
        RBAC["Kubernetes API + RBAC<br/>ServiceAccount: api-sa<br/>Role: deployment-reader<br/>Verbs: get, list  →  Deployments"]
    end

    USER -->|"HTTP / HTTPS"| NG
    NG -->|"Static SPA"| FE
    NG -->|"REST Requests"| AP
    FE -.->|"Polls every 4 s"| NG

    AP -->|"process_task.delay(id)"| RD
    AP -->|"INSERT / SELECT tasks"| PG
    AP -->|"GET worker:heartbeat"| RD
    AP -->|"list namespaced Deployments"| RBAC

    RD -->|"Dispatch task message"| W1
    RD -->|"Dispatch task message"| WN

    W1 -->|"SET worker:heartbeat  EX 30"| RD
    WN -->|"SET worker:heartbeat  EX 30"| RD

    W1 -->|"chat.completions.create()"| GROQ
    WN -->|"chat.completions.create()"| GROQ
    GROQ -->|"AI analysis result"| W1
    GROQ -->|"AI analysis result"| WN

    W1 -->|"UPDATE status, result"| PG
    WN -->|"UPDATE status, result"| PG

    KEDA -->|"LLEN celery"| RD
    KEDA -->|"Scale worker Deployment"| RBAC
```

---

### Task Status State Machine

Every task transitions through a strict lifecycle. Workers use `SELECT ... FOR UPDATE SKIP LOCKED` to prevent double-processing, and automatically retry transient failures up to three times.

```mermaid
stateDiagram-v2
    [*] --> PENDING : Task created via POST /tasks

    PENDING --> IN_PROGRESS : Worker acquires task lock

    IN_PROGRESS --> COMPLETED : Groq analysis succeeds
    IN_PROGRESS --> PENDING   : Transient error — retry scheduled\nretry_count++ · countdown 10 s

    PENDING --> FAILED : retry_count > 3\n(MaxRetriesExceeded)
    IN_PROGRESS --> FAILED : Simulated failure\n(FAIL_TEST keyword detected)

    COMPLETED --> [*]
    FAILED    --> [*]
```

---

### Request & Task Processing Flow

End-to-end sequence from the moment a user submits a task to the moment the result appears in the dashboard.

```mermaid
sequenceDiagram
    autonumber
    actor User as Browser
    participant FE as React Dashboard
    participant NG as NGINX Ingress
    participant API as FastAPI API
    participant PG as PostgreSQL
    participant RD as Redis
    participant W as Celery Worker
    participant GROQ as Groq Cloud API

    User->>FE: Submit task text
    FE->>NG: POST /api/tasks {input_text}
    NG->>API: POST /tasks
    API->>PG: INSERT task  status=PENDING
    PG-->>API: task {id, status: PENDING}
    API->>RD: RPUSH celery  process_task(id)
    API-->>FE: 201 Created {id, status: PENDING}

    Note over RD,W: Worker consumes from Redis queue

    W->>RD: BLPOP celery
    RD-->>W: task message {id}
    W->>PG: SELECT ... FOR UPDATE SKIP LOCKED WHERE id=?
    PG-->>W: task row
    W->>PG: UPDATE status=IN_PROGRESS
    W->>RD: SET worker:heartbeat  EX 30

    W->>GROQ: chat.completions.create(input_text)
    GROQ-->>W: {summary, issues, action}

    W->>PG: UPDATE status=COMPLETED  result=analysis
    W->>RD: SET worker:heartbeat  EX 30

    Note over FE,API: Dashboard polls every 4 s

    FE->>NG: GET /api/metrics/results
    NG->>API: GET /metrics/results
    API->>PG: SELECT recent COMPLETED tasks
    PG-->>API: task list with results
    API-->>FE: [{id, status, result, ...}]
    FE-->>User: Display AI analysis result
```

---

### KEDA Autoscaling Logic

KEDA continuously monitors the Redis task queue depth and drives the Kubernetes `worker` Deployment between 1 and 10 replicas with no custom code required.

```mermaid
flowchart TD
    START(["KEDA polls Redis every 10 s"])
    CHECK{"LLEN celery >= 3?"}
    SCALE_UP["Scale UP worker Deployment<br/>Add replicas  ·  max = 10"]
    STABLE["Maintain current replicas"]
    COOLDOWN{"Cooldown period elapsed?\n30 s since last scale event"}
    SCALE_DOWN["Scale DOWN worker Deployment<br/>Reduce replicas  ·  min = 1"]
    K8S["Kubernetes adjusts Pod count<br/>New Workers pull from Redis queue"]

    START --> CHECK
    CHECK -- "Yes — queue is growing" --> SCALE_UP
    CHECK -- "No — queue is empty/small" --> COOLDOWN
    SCALE_UP --> K8S
    COOLDOWN -- "Yes" --> SCALE_DOWN
    COOLDOWN -- "No" --> STABLE
    SCALE_DOWN --> K8S
    STABLE --> START
    K8S --> START
```

---

### Deployment Topology (Kubernetes)

All workloads run in the `ai-orchestrator` namespace. The API reads Deployment status through a scoped RBAC role, enabling live replica counts in the dashboard without cluster-admin privileges.

```mermaid
graph LR
    subgraph INTERNET["Internet"]
        EXT_USER("Client")
    end

    subgraph K8S_CLUSTER["Kubernetes Cluster — namespace: ai-orchestrator"]
        subgraph INGRESS_NS["Ingress"]
            ING_CTRL["NGINX Ingress<br/>NodePort / LoadBalancer"]
        end

        subgraph FRONTEND_NS["frontend Deployment"]
            FE1["frontend Pod<br/>ghcr.io/.../frontend:latest<br/>Nginx :80  NodePort 30300"]
        end

        subgraph API_NS["api Deployment"]
            API1["api Pod<br/>ghcr.io/.../api:latest<br/>Uvicorn :8000  NodePort 30800<br/>ServiceAccount: api-sa"]
        end

        subgraph WORKER_NS["worker Deployment  — scaled by KEDA"]
            WW1["worker Pod 1<br/>ghcr.io/.../worker:latest"]
            WW2["worker Pod 2"]
            WWN["worker Pod N  (up to 10)"]
        end

        subgraph DATA_NS["Stateful Services"]
            REDIS_K8S[("Redis Pod<br/>redis:7-alpine<br/>ClusterIP :6379")]
            PG_K8S[("PostgreSQL Pod<br/>postgres:15<br/>ClusterIP :5432")]
        end

        subgraph CONTROL_NS["Control Plane Extensions"]
            KEDA_OP["KEDA Operator<br/>ScaledObject: worker"]
            SA["ServiceAccount: api-sa<br/>Role: deployment-reader<br/>RoleBinding: api-reads-deployments"]
            CM["ConfigMap: app-config<br/>Secret: app-secrets"]
        end
    end

    EXT_USER -->|"HTTP"| ING_CTRL
    ING_CTRL -->|"/"| FE1
    ING_CTRL -->|"/api/*"| API1
    API1 --> REDIS_K8S
    API1 --> PG_K8S
    API1 -->|"RBAC"| SA
    WW1 --> REDIS_K8S
    WW2 --> REDIS_K8S
    WWN --> REDIS_K8S
    WW1 --> PG_K8S
    WW2 --> PG_K8S
    WWN --> PG_K8S
    KEDA_OP -->|"watches"| REDIS_K8S
    KEDA_OP -->|"scales"| SA
    API1 -.->|"envFrom"| CM
    WW1 -.->|"envFrom"| CM
```

---

## Technology Stack

| Layer | Technology | Version | Role |
|---|---|---|---|
| **Frontend** | React + Vite | 18 / 5 | Dashboard SPA — queue, health, autoscaling, results |
| **Web Server** | Nginx | Alpine | Serves static assets; proxies `/api/*` to FastAPI |
| **API Framework** | FastAPI | 0.110.0 | REST API server; async-ready with Uvicorn |
| **ASGI Server** | Uvicorn | 0.29.0 | Production ASGI server for FastAPI |
| **Task Queue** | Celery | 5.3.6 | Distributed async task processing |
| **Message Broker** | Redis | 7 | Celery broker, result backend, worker heartbeat |
| **AI Inference** | Groq API | 0.9.0 | LLaMA-3.3-70b-Versatile — text analysis |
| **Database** | PostgreSQL | 15 | Persistent task storage with status lifecycle |
| **ORM** | SQLAlchemy | 2.0.29 | Database access layer |
| **Data Validation** | Pydantic | v2 | Request/response schema validation |
| **K8s Client** | kubernetes | 29.0.0 | In-cluster Deployment status inspection |
| **Autoscaler** | KEDA | v2 | Event-driven autoscaling via Redis queue depth |
| **Ingress** | NGINX Ingress | — | Path-based routing; URL rewriting |
| **Containerization** | Docker | — | Multi-service local dev via Compose |
| **Orchestration** | Kubernetes | — | Production workload management |
| **Image Registry** | GHCR | — | `ghcr.io/moazakramkhan1/...` |

---

## API Reference

### Tasks

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/tasks` | Submit a single task for AI analysis |
| `POST` | `/api/tasks/bulk` | Submit multiple tasks in one request |
| `GET` | `/api/tasks` | List all tasks |
| `GET` | `/api/tasks/{id}` | Get a single task by UUID |

### Metrics

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/metrics/queue` | Queue depth — pending, in_progress, completed, failed |
| `GET` | `/api/metrics/workers` | Worker replica count + scaling status from K8s |
| `GET` | `/api/metrics/results` | Recent completed tasks with AI results |
| `GET` | `/api/metrics/autoscaling/events` | Live autoscaling event snapshot |

### Health

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | Liveness check — database connectivity |
| `GET` | `/api/health/detailed` | Deep health — API, database, Redis, worker heartbeat |

---

## Project Structure

```
.
├── docker-compose.yml          # Local dev: db, redis, api, worker, frontend
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── main.py             # FastAPI app factory + CORS + lifespan
│       ├── api/routes/
│       │   ├── tasks.py        # Task CRUD + Celery dispatch
│       │   ├── metrics.py      # Queue depth, worker replicas, results
│       │   └── health.py       # Liveness + detailed health check
│       ├── core/
│       │   ├── config.py       # Pydantic Settings — env-driven config
│       │   └── database.py     # SQLAlchemy engine + session factory
│       ├── models/task.py      # SQLAlchemy Task model + TaskStatus enum
│       ├── schemas/task.py     # Pydantic request/response schemas
│       ├── services/
│       │   ├── groq_service.py         # Groq API call + error handling
│       │   ├── task_service.py         # DB queries for Task model
│       │   ├── health_service.py       # Redis ping + heartbeat key
│       │   ├── queue_metrics_service.py # Redis LLEN + scaling status inference
│       │   └── k8s_service.py          # Kubernetes Deployment status via RBAC
│       └── worker/
│           ├── celery_app.py   # Celery application factory
│           └── tasks.py        # process_task — acquire lock, call Groq, persist result
└── frontend/
│   ├── Dockerfile
│   ├── nginx.conf              # Static serving + /api/* proxy pass
│   └── src/
│       ├── App.jsx             # Root component + polling orchestration
│       ├── components/
│       │   ├── StatCard.jsx         # Individual metric tile
│       │   ├── HealthPanel.jsx      # API/DB/Redis/Worker health status
│       │   ├── AutoscalingPanel.jsx # Replica count + scaling state
│       │   └── ResultLog.jsx        # Scrollable completed task results
│       └── services/api.js     # Typed fetch wrappers for all API calls
└── k8s/
    ├── namespace.yaml
    ├── api/
    │   ├── deployment.yaml     # API Deployment + NodePort Service
    │   └── rbac.yaml           # ServiceAccount + Role + RoleBinding
    ├── worker/deployment.yaml  # Worker Deployment (scaled by KEDA)
    ├── frontend/deployment.yaml # Frontend Deployment + NodePort Service
    ├── keda/scaledobject.yaml  # KEDA ScaledObject — Redis trigger
    ├── postgres/postgres.yaml  # PostgreSQL StatefulSet/Deployment
    ├── redis/redis.yaml        # Redis Deployment + ClusterIP Service
    ├── ingress/ingress.yaml    # NGINX Ingress — path rewriting
    └── config/app-config.yaml.example  # ConfigMap + Secret template
```

---

## Local Development (Docker Compose)

### Prerequisites

- Docker Desktop
- A `.env` file in the project root (see below)

### Environment Variables

```env
POSTGRES_USER=orchestrator
POSTGRES_PASSWORD=secret
POSTGRES_DB=orchestrator

DATABASE_URL=postgresql://orchestrator:secret@db:5432/orchestrator
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0

GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=llama-3.3-70b-versatile

SIMULATE_AI_FAILURE=true
WORKER_HEARTBEAT_TTL_SECONDS=30
CELERY_QUEUE_NAME=celery

K8S_NAMESPACE=ai-orchestrator
WORKER_DEPLOYMENT_NAME=worker
WORKER_MIN_REPLICAS=1
WORKER_MAX_REPLICAS=10
```

### Start All Services

```bash
docker compose up --build
```

| Service | URL |
|---|---|
| React Dashboard | http://localhost:3000 |
| FastAPI (Swagger) | http://localhost:8000/docs |
| PostgreSQL | localhost:5432 |
| Redis | localhost:6379 |

---

## Kubernetes Deployment

### Prerequisites

- A running Kubernetes cluster (minikube, kind, or cloud)
- KEDA v2 installed — [keda.sh/docs](https://keda.sh/docs/deploy/)
- NGINX Ingress Controller installed
- Container images pushed to GHCR

### Deploy

```bash
# 1. Create namespace
kubectl apply -f k8s/namespace.yaml

# 2. Create config and secrets (copy and populate the example first)
cp k8s/config/app-config.yaml.example k8s/config/app-config.yaml
kubectl apply -f k8s/config/app-config.yaml

# 3. Deploy stateful services
kubectl apply -f k8s/postgres/
kubectl apply -f k8s/redis/

# 4. Deploy application (API, Worker, Frontend)
kubectl apply -f k8s/api/
kubectl apply -f k8s/worker/
kubectl apply -f k8s/frontend/

# 5. Configure autoscaling
kubectl apply -f k8s/keda/

# 6. Expose via Ingress
kubectl apply -f k8s/ingress/
```

### Verify

```bash
# Watch worker pods scale with queue depth
kubectl get pods -n ai-orchestrator -w

# Check KEDA ScaledObject status
kubectl get scaledobject -n ai-orchestrator

# Submit tasks and observe autoscaling
curl -X POST http://<ingress-ip>/api/tasks \
  -H "Content-Type: application/json" \
  -d '{"input_text": "Analyze this operational alert..."}'
```

---

## Key Design Decisions

| Decision | Rationale |
|---|---|
| **`SELECT ... FOR UPDATE SKIP LOCKED`** | Prevents multiple workers from claiming the same task; eliminates duplicate processing without a distributed lock service |
| **Redis heartbeat key with TTL** | Workers continuously refresh a Redis key; the API treats absence of the key as a degraded worker — no complex health protocol needed |
| **KEDA Redis trigger** | Zero-code autoscaling: KEDA reads `LLEN celery` directly and drives the K8s Deployment — no custom metrics server or HPA adapter needed |
| **RBAC deployment-reader role** | Minimal-privilege K8s access: the API can observe worker replica counts without cluster-admin, enabling live autoscaling data in the dashboard |
| **Celery retry with `with_for_update`** | Tasks retry up to 3 times with exponential-style countdown; the DB is the source of truth for retry count, preventing silent drops |
| **SIMULATE_AI_FAILURE flag** | `FAIL_TEST` keyword in input triggers a controlled failure path, allowing full retry/failure lifecycle testing without breaking the Groq API key |
