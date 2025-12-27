# Infrastructure Guide

> **Layered CloudFormation stacks + Cloudflare for production deployment.**

---

## Worker Architecture

### Why Separate Workers?

| Without Workers | With Workers |
|-----------------|--------------|
| API blocks during AI calls | API responds instantly |
| 30s+ request timeouts | No timeout issues |
| One slow request blocks others | Parallel processing |
| Can't scale AI load separately | Scale workers independently |
| Server crashes = lost work | Jobs retry/resume |

### Worker Flow

```
USER REQUEST                          WORKER PROCESS
─────────────                         ──────────────

POST /agents/{song_id}/review
          │
          ▼
┌─────────────────┐
│   API Server    │
│                 │
│  1. Validate    │
│  2. Check auth  │
│  3. Queue job   │──────────────────►  Redis Queue
│  4. Return      │                          │
│     task_id     │                          │
└─────────────────┘                          │
          │                                   │
          ▼                                   ▼
    Returns immediately              ┌─────────────────┐
    with task_id                     │     Worker      │
                                     │                 │
    User connects to                 │  1. Poll Redis  │
    WebSocket for updates            │  2. Pick up job │
                                     │  3. Call LLM    │
                                     │  4. Stream back │
                                     │  5. Save result │
                                     └─────────────────┘
```

### Current Worker Jobs

```python
# api/jobs/worker.py
functions = [
    process_document_arq,  # Document upload + embedding
    process_url_arq,       # URL scraping + embedding
]

# Agent tasks queued for:
# - Song reviews (AI analysis)
# - Section reviews
# - Co-writing sessions
# - Cliche checking
# - Rhythm analysis
```

---

## Stack Organization Philosophy

### Wrong: One Giant Stack

```
┌─────────────────────────────────────────────────────────────┐
│  "main-stack"                                               │
│                                                             │
│  VPC + RDS + Redis + ECS Cluster + Services + ALB + S3...  │
│                                                             │
│  Problems:                                                  │
│  - 45 minute deployments                                    │
│  - Change API env var → entire stack updates               │
│  - Delete stack → lose database                            │
│  - Circular dependencies                                    │
│  - Rollback = nightmare                                     │
└─────────────────────────────────────────────────────────────┘
```

### Right: Layered Stacks by Lifecycle

```
┌─────────────────────────────────────────────────────────────┐
│  Layer 1: FOUNDATION (rarely changes)                       │
│  └── VPC, Subnets, Security Groups, IAM Roles              │
├─────────────────────────────────────────────────────────────┤
│  Layer 2: DATA (stateful, protected)                        │
│  └── RDS, ElastiCache, S3 Buckets                          │
├─────────────────────────────────────────────────────────────┤
│  Layer 3: PLATFORM (shared infrastructure)                  │
│  └── ECS Cluster, ALB, ECR Repos, Log Groups               │
├─────────────────────────────────────────────────────────────┤
│  Layer 4: SERVICES (changes frequently, independent)        │
│  └── api, web, worker                                       │
└─────────────────────────────────────────────────────────────┘
```

---

## Stack Dependency Flow

```
                    ┌─────────────────────┐
                    │  1. Foundation      │  Deploy once, rarely touch
                    │  ────────────────   │
                    │  - VPC              │
                    │  - Subnets          │
                    │  - Security Groups  │
                    │  - IAM Roles        │
                    └──────────┬──────────┘
                               │ exports: VpcId, SubnetIds, SGIds
                               ▼
          ┌───────────────────┴───────────────────┐
          │                                       │
          ▼                                       ▼
┌─────────────────────┐             ┌─────────────────────┐
│  2a. Data           │             │  2b. Platform       │
│  ──────────         │             │  ─────────────      │
│  - RDS PostgreSQL   │             │  - ECS Cluster      │
│  - ElastiCache      │             │  - ALB + Listeners  │
│  - S3 Buckets       │             │  - ECR Repos        │
│                     │             │  - Log Groups       │
│  PROTECTED:         │             │                     │
│  DeletionPolicy:    │             │                     │
│    Retain           │             │                     │
└──────────┬──────────┘             └──────────┬──────────┘
           │ exports: DbEndpoint,              │ exports: ClusterArn,
           │ RedisEndpoint, BucketName         │ ALBArn, ListenerArn
           │                                   │
           └───────────────┬───────────────────┘
                           │
                           ▼
          ┌────────────────┴────────────────┐
          │         3. Services             │
          │         ───────────             │
          │                                 │
          │  ┌───────────┐ ┌───────────┐   │
          │  │ API Stack │ │ Web Stack │   │  Each service is
          │  └───────────┘ └───────────┘   │  its own stack
          │  ┌───────────┐                 │
          │  │Worker Stk │                 │  Can deploy/rollback
          │  └───────────┘                 │  independently
          └─────────────────────────────────┘
```

---

## Directory Structure

```
infrastructure/
├── foundation/
│   └── template.yaml       # VPC, Subnets, SGs, IAM
│
├── data/
│   └── template.yaml       # RDS, ElastiCache, S3
│
├── platform/
│   └── template.yaml       # ECS Cluster, ALB, ECR
│
├── services/
│   ├── api/
│   │   └── template.yaml   # API task def + service
│   ├── web/
│   │   └── template.yaml   # Web task def + service
│   └── worker/
│       └── template.yaml   # Worker task def + service
│
├── parameters/
│   ├── dev.json
│   └── prod.json
│
└── deploy.sh               # Deployment script
```

---

## Layer Details

### Layer 1: Foundation

**Deploy:** Once, rarely touch

```yaml
# infrastructure/foundation/template.yaml
Resources:
  VPC:
    Type: AWS::EC2::VPC
    Properties:
      CidrBlock: 10.0.0.0/16
      EnableDnsHostnames: true
      EnableDnsSupport: true

  PublicSubnetA:
    Type: AWS::EC2::Subnet
    Properties:
      VpcId: !Ref VPC
      CidrBlock: 10.0.1.0/24
      AvailabilityZone: !Select [0, !GetAZs '']
      MapPublicIpOnLaunch: true

  # Private subnets for RDS, ECS tasks...
  # Security groups...
  # IAM roles...

Outputs:
  VpcId:
    Value: !Ref VPC
    Export:
      Name: !Sub ${AWS::StackName}-VpcId
  PublicSubnetIds:
    Value: !Join [',', [!Ref PublicSubnetA, !Ref PublicSubnetB]]
    Export:
      Name: !Sub ${AWS::StackName}-PublicSubnetIds
```

### Layer 2a: Data

**Deploy:** Protected, stateful resources

```yaml
# infrastructure/data/template.yaml
Resources:
  Database:
    Type: AWS::RDS::DBInstance
    DeletionPolicy: Retain  # CRITICAL: Don't delete on stack delete
    UpdateReplacePolicy: Retain
    Properties:
      DBInstanceClass: db.t3.micro
      Engine: postgres
      EngineVersion: '15'
      MasterUsername: !Ref DBUsername
      MasterUserPassword: !Ref DBPassword
      AllocatedStorage: 20
      VPCSecurityGroups:
        - !ImportValue foundation-DBSecurityGroup
      DBSubnetGroupName: !Ref DBSubnetGroup

  RedisCluster:
    Type: AWS::ElastiCache::CacheCluster
    Properties:
      CacheNodeType: cache.t3.micro
      Engine: redis
      NumCacheNodes: 1

  AudioBucket:
    Type: AWS::S3::Bucket
    DeletionPolicy: Retain
    Properties:
      BucketName: !Sub ${AWS::StackName}-audio-${AWS::AccountId}
```

### Layer 2b: Platform

**Deploy:** Shared infrastructure

```yaml
# infrastructure/platform/template.yaml
Resources:
  ECSCluster:
    Type: AWS::ECS::Cluster
    Properties:
      ClusterName: !Sub ${Environment}-songwriter

  ALB:
    Type: AWS::ElasticLoadBalancingV2::LoadBalancer
    Properties:
      Type: application
      Subnets: !Split [',', !ImportValue foundation-PublicSubnetIds]
      SecurityGroups:
        - !ImportValue foundation-ALBSecurityGroup

  APIRepository:
    Type: AWS::ECR::Repository
    Properties:
      RepositoryName: songwriter-api

  WebRepository:
    Type: AWS::ECR::Repository
    Properties:
      RepositoryName: songwriter-web
```

### Layer 3: Services

**Deploy:** Frequently, independently

```yaml
# infrastructure/services/api/template.yaml
Resources:
  TaskDefinition:
    Type: AWS::ECS::TaskDefinition
    Properties:
      Family: songwriter-api
      NetworkMode: awsvpc
      RequiresCompatibilities: [FARGATE]
      Cpu: 256
      Memory: 512
      ContainerDefinitions:
        - Name: api
          Image: !Sub ${AWS::AccountId}.dkr.ecr.${AWS::Region}.amazonaws.com/songwriter-api:${ImageTag}
          PortMappings:
            - ContainerPort: 8080
          Environment:
            - Name: DATABASE_URL
              Value: !Sub
                - postgresql://${User}:${Pass}@${Host}:5432/songwriter
                - Host: !ImportValue data-DBEndpoint
                  User: !Ref DBUsername
                  Pass: !Ref DBPassword
            - Name: REDIS_URL
              Value: !Sub
                - redis://${Host}:6379
                - Host: !ImportValue data-RedisEndpoint

  Service:
    Type: AWS::ECS::Service
    Properties:
      Cluster: !ImportValue platform-ClusterArn
      TaskDefinition: !Ref TaskDefinition
      DesiredCount: 2
      LaunchType: FARGATE
      LoadBalancers:
        - ContainerName: api
          ContainerPort: 8080
          TargetGroupArn: !Ref TargetGroup
```

---

## Cloudflare vs Route 53

**Recommendation:** Use Cloudflare

| Feature | Route 53 | Cloudflare |
|---------|----------|------------|
| **Cost** | $0.50/zone + $0.40/M queries | Free |
| **CDN** | Separate (CloudFront) | Included |
| **DDoS Protection** | Basic (need Shield $$) | Included (excellent) |
| **SSL Certs** | ACM (AWS only) | Universal SSL (free) |
| **DNS Propagation** | Minutes | Seconds |
| **UI/UX** | AWS Console | Actually good |
| **Bot Protection** | WAF ($$) | Included |

---

## Architecture with Cloudflare

```
┌─────────────────────────────────────────────────────────────┐
│                      CLOUDFLARE                             │
│                                                             │
│  DNS:  app.yourdomain.com  ─► ALB (AWS)                    │
│        api.yourdomain.com  ─► ALB (AWS)                    │
│                                                             │
│  Features:                                                  │
│  ✓ SSL termination (or pass-through to ALB)                │
│  ✓ CDN caching for static assets                           │
│  ✓ DDoS protection                                         │
│  ✓ Bot protection                                          │
│  ✓ Rate limiting (free tier has limits)                    │
│  ✓ Analytics                                               │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                        AWS                                  │
│                                                             │
│  ALB ─► ECS Services                                       │
│                                                             │
│  SSL: Can use Cloudflare origin certs (free, 15 years)     │
│       or ACM certs                                          │
└─────────────────────────────────────────────────────────────┘
```

---

## Deployment Script

```bash
#!/bin/bash
# infrastructure/deploy.sh

set -e

ENVIRONMENT=${1:-dev}
STACK_PREFIX="songwriter-${ENVIRONMENT}"
PARAMS_FILE="parameters/${ENVIRONMENT}.json"

deploy_stack() {
    local name=$1
    local template=$2

    echo "Deploying ${name}..."
    aws cloudformation deploy \
        --stack-name "${STACK_PREFIX}-${name}" \
        --template-file "${template}" \
        --parameter-overrides file://${PARAMS_FILE} \
        --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM \
        --no-fail-on-empty-changeset
}

# Deploy in order
deploy_stack "foundation" "foundation/template.yaml"
deploy_stack "data" "data/template.yaml"
deploy_stack "platform" "platform/template.yaml"

# Services can deploy in parallel
deploy_stack "api" "services/api/template.yaml" &
deploy_stack "web" "services/web/template.yaml" &
deploy_stack "worker" "services/worker/template.yaml" &
wait

echo "All stacks deployed!"
```

---

## Key Principles

| Principle | Why |
|-----------|-----|
| **Layered by lifecycle** | Things that change together, deploy together |
| **Data layer protected** | `DeletionPolicy: Retain` prevents accidental data loss |
| **Services independent** | Deploy API without touching Web or Worker |
| **Cross-stack exports** | Stacks reference each other via CloudFormation exports |
| **Parameters per environment** | Same templates, different values for dev/prod |

---

## Deployment Order

1. **Foundation** - VPC, subnets, security groups (deploy once)
2. **Data** - RDS, Redis, S3 (protected, deploy carefully)
3. **Platform** - ECS cluster, ALB, ECR (shared infrastructure)
4. **Services** - API, Web, Worker (deploy frequently, independently)

---

## AWS Architecture Options

### Option 1: ECS Fargate (Production-Ready)

Best for: Production, pay-per-use, no server management.

```
                        ┌─────────────────────────────────────┐
                        │            Cloudflare               │
                        │         (DNS + CDN + WAF)           │
                        └───────────────┬─────────────────────┘
                                        │
                        ┌───────────────▼─────────────────────┐
                        │   Application Load Balancer         │
                        └───────────────┬─────────────────────┘
                                        │
              ┌─────────────────────────┼─────────────────────────┐
              │                         │                         │
              ▼                         ▼                         │
┌──────────────────────┐  ┌──────────────────────┐               │
│   ECS Fargate        │  │   ECS Fargate        │               │
│   ───────────        │  │   ───────────        │               │
│   Next.js (2 tasks)  │  │   FastAPI (2 tasks)  │               │
│   256 CPU / 512 MB   │  │   512 CPU / 1GB      │               │
└──────────────────────┘  └──────────────────────┘               │
                                        │                         │
                          ┌─────────────▼─────────────┐          │
                          │   ECS Fargate             │          │
                          │   ───────────             │          │
                          │   Workers (2 tasks)       │          │
                          │   1024 CPU / 2GB          │          │
                          └─────────────┬─────────────┘          │
                                        │                         │
              ┌─────────────────────────┼─────────────────────────┘
              │                         │
              ▼                         ▼
┌──────────────────────┐  ┌──────────────────────┐
│   RDS PostgreSQL     │  │   ElastiCache Redis  │
│   db.t4g.micro       │  │   cache.t4g.micro    │
└──────────────────────┘  └──────────────────────┘
              │
              ▼
┌──────────────────────┐
│   S3 (file uploads)  │
└──────────────────────┘
```

### Option 2: EC2 + Docker Compose (Budget)

Best for: Starting out, learning AWS, much cheaper.

```
┌─────────────────────────────────────────────────────────────┐
│                    EC2 t3.medium ($30/mo)                   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                 Docker Compose                       │   │
│  │                                                      │   │
│  │   nginx ─► next.js ─► fastapi ─► worker             │   │
│  │                          │          │                │   │
│  │                          ▼          ▼                │   │
│  │                    postgres    redis                 │   │
│  │                                                      │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
              │
              ▼
┌──────────────────────┐
│   S3 (file uploads)  │
└──────────────────────┘
```

---

## AWS Cost Breakdown

### ECS Fargate (Production-Ready)

| Service | Spec | Monthly Cost |
|---------|------|--------------|
| ECS - Next.js | 2 × 0.25 vCPU, 0.5GB | ~$15 |
| ECS - FastAPI | 2 × 0.5 vCPU, 1GB | ~$30 |
| ECS - Workers | 2 × 1 vCPU, 2GB | ~$60 |
| RDS PostgreSQL | db.t4g.micro | $0 (free tier) or ~$15 |
| ElastiCache Redis | cache.t4g.micro | ~$12 |
| ALB | Application LB | ~$16 + $0.008/LCU |
| CloudFront | 100GB transfer | ~$9 |
| S3 | 10GB storage | ~$0.25 |
| Route 53 | Hosted zone | ~$0.50 |
| NAT Gateway | If private subnets | ~$32 (can avoid) |
| **Total** | | **~$130-170/month** |

### EC2 Single Server (Budget)

| Service | Spec | Monthly Cost |
|---------|------|--------------|
| EC2 | t3.medium (2 vCPU, 4GB) | ~$30 |
| EBS | 50GB gp3 | ~$4 |
| S3 | 10GB storage | ~$0.25 |
| Route 53 | Hosted zone | ~$0.50 |
| **Total** | | **~$35/month** |

### Platform Comparison

| Platform | Estimated Cost | Effort |
|----------|----------------|--------|
| Railway | ~$40-60/mo | Very Low |
| Render | ~$50-80/mo | Very Low |
| Fly.io | ~$30-50/mo | Low |
| AWS EC2 | ~$35/mo | Medium |
| AWS ECS | ~$130-170/mo | Medium-High |
| AWS EKS | ~$200+/mo | High |

---

## Recommended Learning Path

### Phase 1: EC2 Single Server (~$35/mo)

- Learn VPC, Security Groups, IAM
- Docker Compose for orchestration
- RDS for managed Postgres (optional, +$15)
- S3 for file storage
- Route 53 + ACM for DNS/SSL

### Phase 2: ECS Fargate (~$130/mo)

- Migrate to containers
- Learn ECS task definitions
- ALB for load balancing
- Auto-scaling based on load
- Proper multi-AZ setup

---

## Service Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         EXTERNAL                                │
│  ┌──────────┐    ┌──────────┐    ┌──────────────┐              │
│  │  Users   │    │  Stripe  │    │ LLM Provider │              │
│  │ (Browser)│    │ Webhooks │    │ (OpenAI/etc) │              │
│  └────┬─────┘    └────┬─────┘    └──────┬───────┘              │
└───────┼───────────────┼─────────────────┼──────────────────────┘
        │               │                 │
        ▼               ▼                 │
┌───────────────────────────────────────────────────────────────┐
│                        FRONTEND                                │
│  ┌─────────────────────────────────┐                          │
│  │     Next.js (web)               │                          │
│  │     - Server-side rendering     │◄─────────────────────────┤
│  │     - API routes (proxy)        │                          │
│  │     - Stripe Elements           │                          │
│  │     Port: 3000                  │                          │
│  └───────────────┬─────────────────┘                          │
└──────────────────┼────────────────────────────────────────────┘
                   │ HTTP/WebSocket
                   ▼
┌───────────────────────────────────────────────────────────────┐
│                        BACKEND                                 │
│  ┌─────────────────────────────────┐                          │
│  │     FastAPI (api)               │                          │
│  │     - REST API                  │──────────────────────────┼──► LLM APIs
│  │     - WebSocket (Yjs, Jobs)     │                          │
│  │     - Stripe webhooks           │                          │
│  │     Port: 8080                  │                          │
│  └───────────────┬─────────────────┘                          │
│                  │                                             │
│  ┌───────────────┴─────────────────┐                          │
│  │        ARQ Worker(s)            │                          │
│  │     - Document processing       │──────────────────────────┼──► LLM APIs
│  │     - AI agent tasks            │                          │
│  │     - Background jobs           │                          │
│  └───────────────┬─────────────────┘                          │
└──────────────────┼────────────────────────────────────────────┘
                   │
┌──────────────────┼────────────────────────────────────────────┐
│                  │     DATA LAYER                              │
│  ┌───────────────┴───────────┐    ┌─────────────────────┐     │
│  │      PostgreSQL           │    │       Redis         │     │
│  │   - Users, Songs, etc.    │    │   - Job queue       │     │
│  │   - pgvector embeddings   │    │   - Rate limiting   │     │
│  │   Port: 5432              │    │   - Session cache   │     │
│  └───────────────────────────┘    │   Port: 6379        │     │
│                                   └─────────────────────┘     │
└───────────────────────────────────────────────────────────────┘
```

### Service Breakdown

| Service | Role | Replicas | Stateful? |
|---------|------|----------|-----------|
| web | Next.js frontend | 2+ | No |
| api | FastAPI backend | 2+ | No |
| worker | ARQ background jobs | 1-3 | No |
| postgres | Database | 1 (primary) | Yes |
| redis | Queue + cache | 1 | Yes* |

---

## Docker Compose

```yaml
# docker-compose.yml
version: "3.8"

services:
  # Database
  postgres:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_USER: greg
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      POSTGRES_DB: greg
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U greg"]
      interval: 5s
      timeout: 5s
      retries: 5

  # Cache/Queue
  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 5s
      retries: 5

  # Backend API
  api:
    build:
      context: .
      dockerfile: Dockerfile.api
    environment:
      DATABASE_URL: postgresql://greg:${DB_PASSWORD}@postgres:5432/greg
      REDIS_URL: redis://redis:6379
      JWT_SECRET_KEY: ${JWT_SECRET_KEY}
      STRIPE_SECRET_KEY: ${STRIPE_SECRET_KEY}
      STRIPE_WEBHOOK_SECRET: ${STRIPE_WEBHOOK_SECRET}
      OPENAI_API_KEY: ${OPENAI_API_KEY}
      LLM_PROVIDER: openai
      LLM_MODEL: gpt-4o
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    ports:
      - "8080:8080"

  # Background workers
  worker:
    build:
      context: .
      dockerfile: Dockerfile.api
    command: uv run greg worker
    environment:
      DATABASE_URL: postgresql://greg:${DB_PASSWORD}@postgres:5432/greg
      REDIS_URL: redis://redis:6379
      OPENAI_API_KEY: ${OPENAI_API_KEY}
      LLM_PROVIDER: openai
      LLM_MODEL: gpt-4o
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    deploy:
      replicas: 2

  # Frontend
  web:
    build:
      context: ./web
      dockerfile: Dockerfile
    environment:
      NEXT_PUBLIC_API_URL: http://api:8080
      INTERNAL_API_KEY: ${INTERNAL_API_KEY}
      NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY: ${STRIPE_PUBLISHABLE_KEY}
    depends_on:
      - api
    ports:
      - "3000:3000"

  # Reverse proxy
  nginx:
    image: nginx:alpine
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
    ports:
      - "80:80"
      - "443:443"
    depends_on:
      - web
      - api

volumes:
  postgres_data:
  redis_data:
```

---

## Kubernetes

### API Deployment

```yaml
# k8s/api-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: songwriter-api
  namespace: songwriter
spec:
  replicas: 3
  selector:
    matchLabels:
      app: songwriter-api
  template:
    metadata:
      labels:
        app: songwriter-api
    spec:
      containers:
        - name: api
          image: your-registry/songwriter-api:latest
          ports:
            - containerPort: 8080
          envFrom:
            - secretRef:
                name: songwriter-secrets
            - configMapRef:
                name: songwriter-config
          resources:
            requests:
              memory: "512Mi"
              cpu: "250m"
            limits:
              memory: "1Gi"
              cpu: "500m"
          livenessProbe:
            httpGet:
              path: /health
              port: 8080
            initialDelaySeconds: 10
            periodSeconds: 10
          readinessProbe:
            httpGet:
              path: /health
              port: 8080
            initialDelaySeconds: 5
            periodSeconds: 5
```

### Worker Deployment

```yaml
# k8s/worker-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: songwriter-worker
  namespace: songwriter
spec:
  replicas: 2
  selector:
    matchLabels:
      app: songwriter-worker
  template:
    spec:
      containers:
        - name: worker
          image: your-registry/songwriter-api:latest
          command: ["uv", "run", "greg", "worker"]
          envFrom:
            - secretRef:
                name: songwriter-secrets
          resources:
            requests:
              memory: "1Gi"  # Workers need more for AI tasks
              cpu: "500m"
            limits:
              memory: "2Gi"
              cpu: "1000m"
```

### Ingress

```yaml
# k8s/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: songwriter-ingress
  namespace: songwriter
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  tls:
    - hosts:
        - app.yourdomain.com
        - api.yourdomain.com
      secretName: songwriter-tls
  rules:
    - host: app.yourdomain.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: songwriter-web
                port:
                  number: 3000
    - host: api.yourdomain.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: songwriter-api
                port:
                  number: 8080
```

---

## Simpler Cloud Options

Railway / Render / Fly.io deploy each service separately:

```
┌─────────────────────────────────────────┐
│              Railway/Render              │
├─────────────────────────────────────────┤
│  Service: web         (Next.js)         │
│  Service: api         (FastAPI)         │
│  Service: worker      (ARQ)             │
│  Database: PostgreSQL (managed)         │
│  Redis: Redis         (managed)         │
└─────────────────────────────────────────┘
```

Each platform handles scaling, SSL, and health checks automatically.

---

## Orchestration Considerations

| Concern | Solution |
|---------|----------|
| **Database migrations** | Run as init container or separate job before API starts |
| **Secrets** | Use platform secrets (K8s Secrets, Railway encrypted vars) |
| **WebSocket sticky sessions** | Ingress affinity or Redis pub/sub for cross-instance |
| **Worker scaling** | Scale based on Redis queue depth |
| **Health checks** | `/health` endpoint already exists |
| **Stripe webhooks** | Single endpoint, idempotent handlers |
| **File uploads** | Use S3/R2 instead of local storage |

---

## Recommended Production Stack

For Stripe payments + AI workloads:

```
┌─────────────────────────────────────────────────────────────┐
│                     Cloudflare                              │
│  - CDN, DDoS protection                                     │
│  - R2 for file storage                                      │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────┼───────────────────────────────────────┐
│                     │     Railway / Fly.io                  │
│  ┌──────────────────┴──────────────────┐                   │
│  │           Load Balancer              │                   │
│  └──────────────────┬──────────────────┘                   │
│           ┌─────────┴─────────┐                            │
│           ▼                   ▼                            │
│  ┌─────────────┐     ┌─────────────┐                       │
│  │  Next.js    │     │  FastAPI    │                       │
│  │  (2 inst)   │     │  (2 inst)   │                       │
│  └─────────────┘     └──────┬──────┘                       │
│                             │                              │
│  ┌──────────────────────────┼───────────────────────┐      │
│  │        Workers (2 instances)                     │      │
│  └──────────────────────────┼───────────────────────┘      │
│                             │                              │
│  ┌──────────────────────────┴───────────────────────┐      │
│  │   PostgreSQL (managed)  │  Redis (managed)       │      │
│  └──────────────────────────────────────────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

---

## Related Documentation

- [Architecture Patterns](./patterns.md) - Application-level patterns
- [Songwriter Roadmap](../roadmap/SONGWRITER_ROADMAP.md) - Feature phases
