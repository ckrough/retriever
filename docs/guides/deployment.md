# Deployment Guide

How to deploy Retriever to production.

## Deployment Options

| Platform | Free Tier | Notes | Recommended For |
|----------|-----------|-------|-----------------|
| **Docker** | N/A | Full control, portable | Testing production build locally |
| Railway | 500 hours/month | Simple, good DX | Quick MVP deployment |
| Render | 750 hours/month | Easy setup | Quick MVP deployment |
| **Google Cloud Run** | Free tier available | Serverless, auto-scaling | Production scale |

Choose based on your needs:
- **Docker** (local): Test production build before deploying
- **Railway/Render**: Quick MVP deployment with minimal setup
- **Cloud Run**: Production-ready with auto-scaling (see [Cloud Run Guide](./cloudrun-deployment.md))

## Docker Deployment

Docker provides a production-ready containerized environment that can run locally or be deployed to any cloud platform.

### Prerequisites

- Docker and docker-compose installed
- `.env` file with all required API keys

### Quick Start

```bash
# Build the production image
docker build -t retriever:latest .

# Run with docker-compose (recommended)
docker-compose up -d

# Check health
curl http://localhost:8000/health

# View logs
docker-compose logs -f retriever

# Create a user
docker-compose exec retriever uv run python scripts/create_user.py
```

### Configuration

All configuration via environment variables. Create a `.env` file:

```bash
# Required
OPENROUTER_API_KEY=your-openrouter-key
OPENAI_API_KEY=your-openai-key
JWT_SECRET_KEY=generate-random-secret-32-chars

# Optional (defaults shown)
DEBUG=false
PORT=8000
DATABASE_PATH=/app/data/retriever.db
CHROMA_PERSIST_PATH=/app/data/chroma
```

### Data Persistence

Docker uses named volumes for persistent data:

- `retriever-data` → SQLite database + Chroma vector store
- `retriever-documents` → Uploaded policy documents

**Backup data:**

```bash
docker run --rm \
  -v retriever-data:/app/data \
  -v $(pwd):/backup \
  retriever:latest tar czf /backup/retriever-data-backup.tar.gz /app/data
```

**Restore data:**

```bash
docker run --rm \
  -v retriever-data:/app/data \
  -v $(pwd):/backup \
  retriever:latest tar xzf /backup/retriever-data-backup.tar.gz -C /
```

### Deploying to Cloud Run

See [Cloud Run Deployment Guide](./cloudrun-deployment.md) for detailed instructions including:
- One-time GCP project setup
- Secret Manager configuration
- Deployment commands for staging/production

---

## Railway / Render Deployment

### Prerequisites

1. GitHub repository with code
2. Platform account (Railway or Render)
3. Environment variables ready:
   - `OPENROUTER_API_KEY`
   - `OPENAI_API_KEY` (for embeddings)
   - `SENTRY_DSN` (optional)
   - `SECRET_KEY` (for JWT)

## Railway Deployment

### 1. Connect Repository

1. Go to [railway.app](https://railway.app)
2. Click "New Project" → "Deploy from GitHub repo"
3. Select your repository
4. Railway auto-detects Python

### 2. Configure Environment

In Railway dashboard → Variables:

```
OPENROUTER_API_KEY=sk-or-...
OPENAI_API_KEY=sk-...
SECRET_KEY=<generate-random-string>
ENVIRONMENT=production
```

### 3. Configure Build

Railway should auto-detect, but if needed create `railway.toml`:

```toml
[build]
builder = "nixpacks"

[deploy]
startCommand = "uvicorn src.main:app --host 0.0.0.0 --port $PORT"
```

### 4. Add Persistent Storage

For SQLite and Chroma data:

1. Railway dashboard → Add Volume
2. Mount path: `/app/data`
3. Update app to use `/app/data` for storage

### 5. Custom Domain (Optional)

1. Settings → Domains
2. Add custom domain
3. Configure DNS CNAME

## Render Deployment

### 1. Create Web Service

1. Go to [render.com](https://render.com)
2. New → Web Service
3. Connect GitHub repository

### 2. Configure Service

```yaml
# render.yaml
services:
  - type: web
    name: retriever
    env: python
    buildCommand: pip install -e .
    startCommand: uvicorn src.main:app --host 0.0.0.0 --port $PORT
    envVars:
      - key: OPENROUTER_API_KEY
        sync: false
      - key: OPENAI_API_KEY
        sync: false
      - key: SECRET_KEY
        generateValue: true
```

### 3. Add Persistent Disk

1. Service settings → Add Disk
2. Mount path: `/app/data`
3. Size: 1GB (sufficient for MVP)

## Post-Deployment Checklist

- [ ] Health check endpoint responds: `GET /health`
- [ ] Can log in with test user
- [ ] Can ask a question and get answer
- [ ] Errors appear in Sentry (if configured)
- [ ] SSL certificate active

## Environment Variables Reference

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENROUTER_API_KEY` | Yes | OpenRouter API key for Claude |
| `OPENAI_API_KEY` | Yes | OpenAI API key for embeddings |
| `SECRET_KEY` | Yes | Random string for JWT signing |
| `SENTRY_DSN` | No | Sentry error tracking DSN |
| `ENVIRONMENT` | No | `development` or `production` |
| `LOG_LEVEL` | No | `DEBUG`, `INFO`, `WARNING`, `ERROR` |

## Initial Document Indexing

After deployment:

1. Upload documents to `documents/` directory
2. Trigger reindex via admin UI or API:
   ```bash
   curl -X POST https://your-app.railway.app/admin/reindex \
        -H "Authorization: Bearer $ADMIN_TOKEN"
   ```
3. Verify documents indexed in admin dashboard

## Monitoring

### Health Checks

```
GET /health        → Basic liveness
GET /health/ready  → Dependencies OK
```

### Uptime Monitoring

Set up external monitoring (free options):
- UptimeRobot
- Checkly
- Better Uptime

Configure to check `/health` every 5 minutes.

## Scaling

For MVP scale (50-100 volunteers), single instance is sufficient.

If needed:
1. Increase instance size before adding instances
2. Consider managed database if SQLite becomes bottleneck
3. See [Future: Production Hardening](../implementation-plan.md#future-production-hardening-post-validation)

## Rollback

If deployment fails:

**Railway:**
1. Deployments → Select previous successful deploy
2. Click "Redeploy"

**Render:**
1. Events → Find previous deploy
2. Click "Rollback"
