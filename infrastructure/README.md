# Songwriter Infrastructure (AWS CDK)

AWS CDK infrastructure for the Songwriter application using ECS Fargate.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      CLOUDFLARE (DNS/CDN)                       │
└───────────────────────────┬─────────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────────┐
│                    AWS ECS FARGATE                              │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                Application Load Balancer                 │   │
│  │  /health, /auth/*, /songs/* ─► API Service              │   │
│  │  /*                         ─► Web Service              │   │
│  └─────────────────────────────────────────────────────────┘   │
│                            │                                    │
│         ┌──────────────────┼──────────────────┐                │
│         ▼                  ▼                  ▼                │
│  ┌────────────┐    ┌────────────┐    ┌────────────┐           │
│  │   Web      │    │   API      │    │  Worker    │           │
│  │  (Next.js) │    │  (FastAPI) │    │   (ARQ)    │           │
│  └────────────┘    └────────────┘    └────────────┘           │
│                            │                  │                │
│                    ┌───────┴──────────────────┘                │
│                    ▼                                           │
│  ┌────────────────────────────────────────────────────────┐   │
│  │   RDS PostgreSQL     │     ElastiCache Redis           │   │
│  └────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

## Stack Organization

| Stack | Description | Changes |
|-------|-------------|---------|
| `Foundation` | VPC, Subnets, Security Groups, IAM | Rarely |
| `Data` | RDS, ElastiCache, S3 (RETAIN policy) | Rarely |
| `Platform` | ECS Cluster, ALB, ECR, Log Groups | Sometimes |
| `Services` | API, Web, Worker Fargate Services | Often |

## Prerequisites

1. **AWS CLI** configured with credentials
2. **Node.js** 18+ and npm
3. **AWS CDK CLI** installed globally:
   ```bash
   npm install -g aws-cdk
   ```

## Quick Start

```bash
cd infrastructure

# Install dependencies
npm install

# Bootstrap CDK (first time only)
cdk bootstrap aws://YOUR_ACCOUNT_ID/us-east-1

# Deploy to dev
cdk deploy --all -c environment=dev

# Deploy to prod
cdk deploy --all -c environment=prod
```

## Commands

```bash
# Show what will be deployed (diff)
cdk diff --all -c environment=dev

# Deploy all stacks
cdk deploy --all -c environment=dev

# Deploy specific stack
cdk deploy Songwriter-dev-Services -c environment=dev

# Deploy without approval prompts
cdk deploy --all -c environment=dev --require-approval never

# Destroy all stacks (data retained)
cdk destroy --all -c environment=dev

# List all stacks
cdk list -c environment=dev

# Synthesize CloudFormation templates
cdk synth -c environment=dev
```

## Pre-Deployment Setup

### 1. Create Required Secrets

```bash
# JWT Secret (required)
aws secretsmanager create-secret \
  --name "songwriter/dev/jwt" \
  --secret-string '{"JWT_SECRET_KEY":"your-secret-key-min-32-chars"}'

# Connection strings (created by Data stack, update after deploy)
# Get the values from stack outputs:
cdk deploy Songwriter-dev-Data -c environment=dev

# Then update the connection strings secret:
aws secretsmanager put-secret-value \
  --secret-id "songwriter/dev/connection-strings" \
  --secret-string '{
    "DATABASE_URL": "postgresql://songwriter:PASSWORD@ENDPOINT:5432/songwriter",
    "REDIS_URL": "redis://REDIS_ENDPOINT:6379"
  }'

# Stripe secrets (optional)
aws secretsmanager create-secret \
  --name "songwriter/dev/stripe" \
  --secret-string '{
    "STRIPE_SECRET_KEY": "sk_test_...",
    "STRIPE_WEBHOOK_SECRET": "whsec_...",
    "STRIPE_PRICE_ID_PRO": "price_..."
  }'

# OpenAI key (optional)
aws secretsmanager create-secret \
  --name "songwriter/dev/openai" \
  --secret-string '{"OPENAI_API_KEY": "sk-..."}'
```

### 2. Build and Push Docker Images

```bash
# Get ECR login
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin YOUR_ACCOUNT.dkr.ecr.us-east-1.amazonaws.com

# Build and push API image
docker build -f Dockerfile.api -t songwriter-api .
docker tag songwriter-api:latest YOUR_ACCOUNT.dkr.ecr.us-east-1.amazonaws.com/songwriter-dev/api:latest
docker push YOUR_ACCOUNT.dkr.ecr.us-east-1.amazonaws.com/songwriter-dev/api:latest

# Build and push Web image
cd apps/songwriter-web
docker build -t songwriter-web .
docker tag songwriter-web:latest YOUR_ACCOUNT.dkr.ecr.us-east-1.amazonaws.com/songwriter-dev/web:latest
docker push YOUR_ACCOUNT.dkr.ecr.us-east-1.amazonaws.com/songwriter-dev/web:latest
```

### 3. Configure Cloudflare

1. Get ALB DNS from stack outputs:
   ```bash
   aws cloudformation describe-stacks \
     --stack-name Songwriter-dev-Platform \
     --query "Stacks[0].Outputs[?OutputKey=='ALBDnsName'].OutputValue" \
     --output text
   ```

2. In Cloudflare, add CNAME records:
   - `app.yourdomain.com` → ALB DNS (Proxied)
   - `api.yourdomain.com` → ALB DNS (Proxied) [optional, same ALB]

3. Set SSL mode to **Full** (not Full Strict)

## Environment Configuration

Edit `lib/config.ts` to customize:

```typescript
dev: {
  database: {
    instanceClass: 'db.t4g.micro',  // Change instance size
    allocatedStorage: 20,
  },
  services: {
    api: {
      cpu: 512,
      memoryMiB: 1024,
      desiredCount: 1,
      minCapacity: 1,
      maxCapacity: 4,
    },
    // ...
  },
}
```

## Updating Services

For code changes, push new images and force deployment:

```bash
# Push new image
docker build -f Dockerfile.api -t songwriter-api .
docker tag songwriter-api:latest $ECR_URI/songwriter-dev/api:latest
docker push $ECR_URI/songwriter-dev/api:latest

# Force new deployment
aws ecs update-service \
  --cluster songwriter-dev \
  --service songwriter-dev-api \
  --force-new-deployment
```

Or redeploy through CDK:
```bash
cdk deploy Songwriter-dev-Services -c environment=dev
```

## Database Migrations

```bash
# Get task ID
TASK_ID=$(aws ecs list-tasks \
  --cluster songwriter-dev \
  --service-name songwriter-dev-api \
  --query 'taskArns[0]' \
  --output text | cut -d'/' -f3)

# Run migrations
aws ecs execute-command \
  --cluster songwriter-dev \
  --task $TASK_ID \
  --container api \
  --interactive \
  --command "alembic upgrade head"
```

## Monitoring

```bash
# View logs
aws logs tail /ecs/songwriter-dev/api --follow
aws logs tail /ecs/songwriter-dev/worker --follow

# Check service status
aws ecs describe-services \
  --cluster songwriter-dev \
  --services songwriter-dev-api songwriter-dev-web songwriter-dev-worker
```

## Cost Estimate

### Dev Environment (~$70/month)
| Resource | Spec | Cost |
|----------|------|------|
| ECS API | 0.5 vCPU, 1GB | ~$15 |
| ECS Web | 0.25 vCPU, 0.5GB | ~$8 |
| ECS Worker | 0.5 vCPU, 1GB | ~$15 |
| RDS | db.t4g.micro | $0 (free tier) |
| ElastiCache | cache.t4g.micro | ~$12 |
| ALB | Base + LCU | ~$18 |
| S3, ECR, Logs | Minimal | ~$2 |

### Prod Environment (~$180/month)
| Resource | Spec | Cost |
|----------|------|------|
| ECS API (2x) | 1 vCPU, 2GB | ~$60 |
| ECS Web (2x) | 0.5 vCPU, 1GB | ~$30 |
| ECS Worker (2x) | 1 vCPU, 2GB | ~$60 |
| RDS | db.t4g.medium, Multi-AZ | ~$50 |
| ElastiCache | cache.t4g.medium | ~$25 |
| ALB | Base + LCU | ~$20 |

## Troubleshooting

### Tasks failing to start
```bash
# Check stopped task reason
aws ecs describe-tasks \
  --cluster songwriter-dev \
  --tasks $(aws ecs list-tasks --cluster songwriter-dev --desired-status STOPPED --query 'taskArns[0]' --output text)
```

### Can't pull images
- Verify ECR repository exists and has images
- Check ECS execution role has ECR permissions
- Ensure security group allows outbound HTTPS

### Health checks failing
```bash
# SSH into container
aws ecs execute-command \
  --cluster songwriter-dev \
  --task $TASK_ID \
  --container api \
  --interactive \
  --command "/bin/bash"

# Check health manually
curl http://localhost:8081/health
```

## File Structure

```
infrastructure/
├── bin/
│   └── app.ts              # CDK app entry point
├── lib/
│   ├── config.ts           # Environment configuration
│   └── stacks/
│       ├── foundation-stack.ts  # VPC, SGs, IAM
│       ├── data-stack.ts        # RDS, Redis, S3
│       ├── platform-stack.ts    # ECS, ALB, ECR
│       └── services-stack.ts    # API, Web, Worker
├── cdk.json                # CDK configuration
├── package.json            # Dependencies
└── tsconfig.json           # TypeScript config
```
